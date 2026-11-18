"""Bounded source-derived preview of MI2 Room 35's waterfall component."""

import argparse
from hashlib import sha256
from pathlib import Path

from .extraction import _write_new_verified
from .inspector import XOR_KEY, _read_pair, chunks, inspect
from .object_images import decode_indexed_object_state
from .palette_probe import advance_palette, decode_room_background_indexed, prepare_cycles
from .palette_sequence import encode_indexed_png
from .scene_events import serialize_scene_events

ARCHIVE_SHA256 = "ad045372e0d49626503bb50fca29a687ec8e01ef75d9b8bca702a366d143819e"
CYCLE_RECORDS = {(176, 191, 3072, 4), (160, 175, 2688, 4)}
STATE_TAGS = tuple(f"IM{state:02X}" for state in range(1, 9))


def paint_indexed_layer(background, width, height, indices, opacity, layer_width,
                        layer_height, x, y):
    """Paint one indexed layer, clipped to the native canvas."""
    if (min(width, height, layer_width, layer_height) <= 0
            or len(background) != width * height
            or len(indices) != layer_width * layer_height
            or len(opacity) != len(indices)
            or any(alpha not in (0, 255) for alpha in opacity)):
        raise ValueError("Invalid indexed layer geometry or opacity")
    pixels = bytearray(background)
    for row in range(max(0, -y), min(layer_height, height - y)):
        for column in range(max(0, -x), min(layer_width, width - x)):
            offset = row * layer_width + column
            if opacity[offset]:
                pixels[(row + y) * width + column + x] = indices[offset]
    return bytes(pixels)


def _event(kind, evidence, *, script=None, **payload):
    event = dict(kind=kind, evidence=evidence, tick=None, payload=payload)
    if script is not None:
        event["script"] = script
    return event


def _script(kind, script_id, pc):
    return dict(kind=kind, storage_room=35, id=script_id, pc=pc)


def render_waterfall(background, states, records, *, x, y, effective_bit92, updates):
    """Render eight source-ordered samples under an explicitly selected branch.

    updates has eight sequences of synthetic cyclePalette deltas. Each delta is
    one update before its sample. Neither a sample nor a delta is wall time.
    """
    if effective_bit92 is not False:
        raise ValueError("Room 35 entry starts script 202 only with effective Bit92 clear")
    if len(states) != 8 or len(updates) != 8:
        raise ValueError("Expected eight authored states and eight update sequences")
    if len(records) != 2 or {(c["start_color"], c["end_color"], c["rate_raw"], c["flags"])
                            for c in records} != CYCLE_RECORDS:
        raise ValueError("Unexpected Room 35 CYCL definitions")
    cycles, diagnostics = prepare_cycles(records)
    palette = bytearray(background["initial_palette"])
    if len(palette) != 768:
        raise ValueError("Expected 256 palette entries")
    events = [
        _event("conditional_transition", "script_static_aligned",
               script=_script("ENCD", None, None), condition="effective Bit92 == 0", taken=True,
               input_evidence="synthetic"),
        _event("script_start", "script_static_aligned", script=_script("ENCD", None, 0x7F),
               script_id=202),
        _event("layer_order", "synthetic", layers=["RMIM", "object 364"]),
        _event("object_position", "synthetic", object_id=364, x=x, y=y),
    ]
    for cycle in cycles:
        events.append(_event("palette_cycle", "archive_decoded", cycle_id=cycle["id"],
                             first=cycle["start_color"], last=cycle["end_color"],
                             flags=cycle["flags_raw"], raw_rate=cycle["rate_raw"],
                             delay=cycle["delay_counter_units"], offset=cycle["source_offset"]))
        diagnostics.append(dict(code="ROOM35_CYCL_FLAG_UNRESOLVED", severity="warning",
                                cycle_id=cycle["id"], flags=cycle["flags_raw"]))
    frames = []
    for number, ((meta, indices, opacity, masks), deltas) in enumerate(zip(states, updates), 1):
        if meta["object_id"] != 364 or meta["state_tag"] != STATE_TAGS[number - 1]:
            raise ValueError(f"Expected authored Room 35 waterfall state {number}")
        for delta in deltas:
            advance_palette(palette, cycles, delta=delta)
        composed = paint_indexed_layer(background["indexed_pixels"], background["width"],
                                       background["height"], indices, opacity, meta["width"],
                                       meta["height"], x, y)
        frames.append((composed, bytes(palette)))
        events.append(_event("object_draw", "script_static_aligned",
                             script=_script("LSCR", 202, 5), object_id=364, state=number,
                             source_offset=meta["source_offset"]))
        for cycle in cycles:
            events.append(_event("palette_phase", "synthetic", sample=number,
                                 cycle_id=cycle["id"], counter=cycle["counter"],
                                 rotations=cycle["rotation_events"]))
        events.append(_event("script_yield", "script_static_aligned",
                             script=_script("LSCR", 202, 0xB)))
    events.append(_event("unknown", "unsupported",
                         reason="Native runtime timing, placement, redraw and Z-plane interactions"))
    return frames, events, diagnostics


def export_room35(source, output, *, x, y, effective_bit92, updates):
    """Write a fresh diagnostic preview and provenance manifest from the pinned archive."""
    inventory = inspect(source)
    if inventory["status"] != "success":
        raise ValueError(f"Archive inspection failed: {inventory['diagnostics']}")
    index, resource, _, _ = _read_pair(Path(source))
    hashes = [sha256(member).hexdigest() for member in (index, resource)]
    if hashes != [entry["sha256"] for entry in inventory["sources"]] or hashes[1] != ARCHIVE_SHA256:
        raise ValueError("Archive fingerprint mismatch for Room 35 DOS VGA")
    scene, = (room for room in inventory["scene_inventory"]["rooms"] if room["room_id"] == 35)
    obj, = (obj for obj in scene["objects"] if obj["object_id"] == 364)
    if obj["status"] != "paired" or set(obj["image"]["image_state_tags"]) != set(STATE_TAGS):
        raise ValueError("Room 35 object 364 does not have the expected eight paired states")
    data = bytes(value ^ XOR_KEY for value in resource)
    start, size = scene["room_offset"], scene["room_size"]
    background = decode_room_background_indexed(data, room_offset=start, room_length=size)
    trns, = (node for node in chunks(data, start + 8, start + size, "ROOM") if node.tag == "TRNS")
    if trns.length < 9:
        raise ValueError("Missing Room 35 transparency index")
    transparent = data[trns.offset + 8]
    states = [decode_indexed_object_state(data, obim_offset=obj["image"]["source_offset"],
                                         state_tag=tag, transparent_color=transparent)
              for tag in STATE_TAGS]
    frames, events, diagnostics = render_waterfall(
        background, states, scene["palette_cycles"], x=x, y=y,
        effective_bit92=effective_bit92, updates=updates)
    events.insert(0, _event("transparency", "archive_decoded", index=transparent,
                            source_offset=trns.offset))
    width, height = background["width"], background["height"]
    payloads = {}
    for number, ((raster, palette), (meta, indices, opacity, masks)) in enumerate(zip(frames, states), 1):
        stem = f"state-{number:02}"
        payloads[stem + ".png"] = encode_indexed_png(width, height, raster, palette)
        payloads[stem + ".indices"] = raster
        payloads[stem + ".rgb"] = palette
        payloads[stem + ".object.indices"] = indices
        payloads[stem + ".object.opacity"] = opacity
        for plane, mask in masks.items():
            payloads[f"{stem}.object.{plane}.mask"] = mask
    manifest = dict(schema="p4-scene-events/1", clock=None, events=events,
                    source=dict(game_edition="MI2 original DOS VGA", archive_sha256=hashes[1],
                                index_sha256=hashes[0], logical_room=35, physical_room=35),
                    fidelity="source_derived_with_synthetic_inputs", width=width, height=height,
                    updates=updates, background=background["source"],
                    background_zplane_tags=background["background_zplanes"],
                    states=[state[0] for state in states],
                    diagnostics=background["diagnostics"] + diagnostics,
                    files={name: sha256(data).hexdigest() for name, data in payloads.items()})
    manifest_bytes = serialize_scene_events(manifest)
    destination = Path(output)
    destination.mkdir(parents=True, exist_ok=False)
    for name, contents in payloads.items():
        _write_new_verified(destination / name, contents)
    _write_new_verified(destination / "manifest.json", manifest_bytes)
    return manifest


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--x", type=int, required=True, help="Assumed object X")
    parser.add_argument("--y", type=int, required=True, help="Assumed object Y")
    parser.add_argument("--effective-bit92-clear", action="store_true", required=True)
    parser.add_argument("--synthetic-delta", type=int, required=True,
                        help="Assumed increment for one palette update before each sample")
    args = parser.parse_args()
    export_room35(args.source, args.output, x=args.x, y=args.y,
                  effective_bit92=False, updates=[[args.synthetic_delta] for _ in STATE_TAGS])


if __name__ == "__main__":
    main()
