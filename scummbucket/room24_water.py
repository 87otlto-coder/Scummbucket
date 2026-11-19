"""Archive-backed Room 24 water samples driven by explicit scene events."""

import argparse
from hashlib import sha256
import json
from pathlib import Path

from .extraction import _write_new_verified
from .inspector import XOR_KEY, _read_pair, chunks, inspect
from .object_images import decode_indexed_object_state
from .palette_probe import advance_palette, decode_room_background_indexed, prepare_cycles
from .palette_sequence import encode_indexed_png
from .room35_waterfall import paint_indexed_layer
from .scene_events import serialize_scene_events

DOS_HASHES = (
    "cde7aa8980317e3a750fbb3b49884cdddaf1ff3d4231a0c840b22cceed9033f1",
    "ad045372e0d49626503bb50fca29a687ec8e01ef75d9b8bca702a366d143819e",
)


def choose_nonrepeating(candidates, allowed, *, previous=None):
    """Yield every candidate and its acceptance, including rejected repeats."""
    for candidate in candidates:
        if type(candidate) is not int or candidate not in allowed:
            raise ValueError(f"Random result outside supported states: {candidate!r}")
        accepted = candidate != previous
        yield candidate, accepted
        if accepted:
            previous = candidate


def authored_position(decoded, obj, room):
    info = obj["code"]
    offset = info["source_offset"]
    header, = (c for c in chunks(decoded, offset + 8, offset + info["byte_length"],
                                 f"Room {room} OBCD") if c.tag == "CDHD")
    data = decoded[header.offset + 8:header.end]
    if len(data) < 4 or int.from_bytes(data[:2], "little") != obj["object_id"]:
        raise ValueError("Invalid authored CDHD position")
    return data[2] * 8, data[3] * 8, header.offset


def load_room24(game):
    index, resource, _, _ = _read_pair(Path(game))
    if tuple(sha256(v).hexdigest() for v in (index, resource)) != DOS_HASHES:
        raise ValueError("Room 24 requires the pinned DOS VGA archives")
    inventory = inspect(game)
    if inventory["status"] != "success":
        raise ValueError(f"Archive inspection failed: {inventory['diagnostics']}")
    room, = (r for r in inventory["scene_inventory"]["rooms"] if r["room_id"] == 24)
    decoded = bytes(v ^ XOR_KEY for v in resource)
    start = room["room_offset"]
    children = chunks(decoded, start + 8, start + room["room_size"], "Room 24")
    trns, = (c for c in children if c.tag == "TRNS" and c.length >= 9)
    encd, = (c for c in children if c.tag == "ENCD")
    script, = (c for c in children if c.tag == "LSCR" and decoded[c.offset + 8] == 200)
    if (encd.offset, encd.length, script.offset, script.length) != (1972720, 12, 1972742, 45):
        raise ValueError("Unexpected Room 24 ENCD or LSCR source boundaries")
    if len(room["palette_cycles"]) != 8:
        raise ValueError("Expected eight Room 24 palette cycles")
    bg = decode_room_background_indexed(decoded, room_offset=start, room_length=room["room_size"])
    objects = {obj["object_id"]: obj for obj in room["objects"]}
    water = objects[246]
    if water["status"] != "paired" or set(water["image"]["image_state_tags"]) != {
            "IM01", "IM02", "IM03"}:
        raise ValueError("Unexpected authored states for object 246")
    return inventory, room, decoded, bg, objects, decoded[trns.offset + 8]


def decode_layer(decoded, obj, state, transparent):
    if obj["status"] != "paired":
        raise ValueError(f"Object {obj['object_id']} is missing its image or code partner")
    return decode_indexed_object_state(decoded, obim_offset=obj["image"]["source_offset"],
                                       state_tag=f"IM{state:02X}", transparent_color=transparent)


def export_room24(game, destination, candidates, deltas):
    """Write one sample per accepted synthetic RNG result and explicit cycle delta."""
    decisions = list(choose_nonrepeating(candidates, (1, 2, 3)))
    if not decisions or sum(accepted for _, accepted in decisions) != len(deltas):
        raise ValueError("Supply one palette delta per accepted random result")
    _, room, decoded, bg, objects, transparent = load_room24(game)
    x, y, position_offset = authored_position(decoded, objects[246], 24)
    indexed, palette = bg["indexed_pixels"], bytearray(bg["initial_palette"])
    width, height = bg["width"], bg["height"]
    cycles, issues = prepare_cycles(room["palette_cycles"])
    source = dict(game_edition="MI2 original DOS VGA", archive_sha256=DOS_HASHES[1],
                  index_sha256=DOS_HASHES[0], logical_room=24, physical_room=24)
    events = [dict(kind="object_position", evidence="archive_decoded", tick=None,
                   payload=dict(object_id=246, x=x, y=y, source_offset=position_offset))]
    files = {}
    states = {}
    sample = 0
    for value, accepted in decisions:
        events.append(dict(kind="random_choice", evidence="synthetic", tick=None,
                           script=dict(kind="LSCR", storage_room=24, id=200, pc=0),
                           payload=dict(result=value, accepted=accepted)))
        if not accepted:
            continue
        if value not in states:
            states[value] = decode_layer(decoded, objects[246], value, transparent)
        meta, pixels, opacity, masks = states[value]
        delta = deltas[sample]
        advance_palette(palette, cycles, delta=delta)
        sample += 1
        for kind, pc, payload in (
            ("object_draw", 25, dict(object_id=246, state=value, sample=sample)),
            ("script_yield", 31, dict(sample=sample)),
        ):
            events.append(dict(kind=kind, evidence="synthetic", tick=None, payload=payload,
                               script=dict(kind="LSCR", storage_room=24, id=200, pc=pc)))
        for cycle in cycles:
            events.append(dict(kind="palette_phase", evidence="synthetic", tick=None,
                               payload=dict(sample=sample, cycle_id=cycle["id"],
                                            rotations=cycle["rotation_events"], counter=cycle["counter"])))
        raster = paint_indexed_layer(indexed, width, height, pixels, opacity,
                                     meta["width"], meta["height"], x, y)
        filename = f"sample-{sample:04}"
        files[filename + ".indices"] = bytes(raster)
        files[filename + ".rgb"] = bytes(palette)
        files[filename + ".png"] = encode_indexed_png(width, height, raster, palette)
        for tag, mask in masks.items():
            files[filename + f".object.{tag}.mask"] = mask
    manifest = dict(schema="p4-scene-events/1", source=source, clock=None, events=events,
                    width=width, height=height, cycles=room["palette_cycles"], diagnostics=issues,
                    fidelity="archive_water_component_with_synthetic_inputs",
                    placement=dict(x=x, y=y, source_offset=position_offset), palette_deltas=list(deltas),
                    background=bg["source"],
                    object_states=[states[state][0] for state in sorted(states)],
                    files={name: sha256(data).hexdigest() for name, data in files.items()})
    encoded = serialize_scene_events(manifest)
    destination.mkdir(parents=True, exist_ok=False)
    for name, data in files.items():
        _write_new_verified(destination / name, data)
    _write_new_verified(destination / "manifest.json", encoded)
    return manifest


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("game", type=Path)
    parser.add_argument("destination", type=Path)
    parser.add_argument("events", type=Path, help="JSON object containing candidates and deltas arrays")
    args = parser.parse_args()
    data = json.loads(args.events.read_bytes())
    export_room24(args.game, args.destination, data["candidates"], data["deltas"])


if __name__ == "__main__":
    main()
