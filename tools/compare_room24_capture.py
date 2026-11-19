"""Validate 64 consecutive Room 24 capture frames against decoded assets."""
import argparse
from hashlib import sha256
import json
from pathlib import Path

from scummbucket.classic_costume import ClassicCostume, apply_depth
from scummbucket.classic_scale import paint_scaled
from scummbucket.extraction import _write_new_verified
from scummbucket.native_frame_compare import compare_native_frame
from scummbucket.palette_probe import advance_palette, prepare_cycles
from scummbucket.room24_water import DOS_HASHES, authored_position, decode_layer, load_room24
from scummbucket.room35_waterfall import paint_indexed_layer
from scummbucket.scene_events import serialize_scene_events
from tools.compare_room23_frames import engine, present


def compare(game, capture):
    run = json.loads((capture / "run.json").read_bytes())
    if (run["entry"], run["equivalent_command"]) != ("debugger_equivalent_room_entry", "room 24"):
        raise ValueError("Expected debugger-equivalent Room 24 capture")
    if tuple(run["archives"][f"MONKEY2.00{i}"] for i in range(2)) != DOS_HASHES:
        raise ValueError("Capture archive hashes differ")
    inventory, room, decoded, bg, objects, transparent = load_room24(game)
    water = objects[246]
    x, y, _ = authored_position(decoded, water, 24)
    width, height = bg["width"], bg["height"]
    authored = {}
    for state in (1, 2, 3):
        meta, pixels, opacity, _ = decode_layer(decoded, water, state, transparent)
        authored[state] = paint_indexed_layer(bg["indexed_pixels"], width, height, pixels,
                                              opacity, meta["width"], meta["height"], x, y)
    costume, = (c for c in inventory["directory_links"]["entries"]
                if c["directory"] == "DCOS" and c["id"] == 1 and c["status"] == "linked")
    offset = costume["source_offset"]
    guy = ClassicCostume(decoded[offset:offset + costume["byte_length"]])
    cycles, _ = prepare_cycles(room["palette_cycles"])
    archive_cycles, _ = prepare_cycles(room["palette_cycles"])
    archive_palette = bytearray(bg["initial_palette"])
    palette = None
    previous = None
    frames = []
    events = []
    for frame in range(1, 65):
        packet = (capture / f"engine-{frame:03}.bin").read_bytes()
        display = (capture / f"present-{frame:03}.bin").read_bytes()
        present(display, frame)
        meta, phases, back, front, backend = engine(packet, frame)
        rows = [s.split() for s in meta["state"]]
        context, = (list(map(int, r[1:])) for r in rows if r[0] == "room24")
        view, = (list(map(int, r[1:])) for r in rows if r[0] == "camera")
        if context[:2] != [24, 24] or view[2:] != [0, 0, width, height, width, height]:
            raise ValueError(f"Unexpected room or viewport at frame {frame}")
        script, = (list(map(int, r[1:])) for r in rows if r[0] == "script" and r[2] == "200")
        pos, = (list(map(int, r[2:])) for r in rows if r[:2] == ["position", "246"])
        if pos != [x, y]:
            raise ValueError(f"Room 24 placement differs at frame {frame}")
        states = {int(r[1]): int(r[2]) for r in rows if r[0] == "object"}
        state = states.pop(246)
        if any(states.values()) or state not in authored or state == previous:
            raise ValueError(f"Unexpected object transition at frame {frame}")
        previous = state
        if palette is None:
            palette = bytearray(phases[0])
            seed_sha = sha256(palette).hexdigest()
        archive_changes = [i // 3 for i in range(0, 768, 3)
                           if archive_palette[i:i + 3] != phases[0][i:i + 3]]
        pre_rgb = sum(palette[i:i + 3] != phases[0][i:i + 3] for i in range(0, 768, 3))
        delta = max(meta["timer_pair"])
        advance_palette(palette, cycles, delta=delta)
        advance_palette(archive_palette, archive_cycles, delta=delta)
        actual_cycles = [list(map(int, r[1:])) for r in rows if r[0] == "cycle"]
        expected = [[c["id"], c["delay_counter_units"], c["counter"], c["flags_raw"],
                     c["start_color"], c["end_color"]] for c in cycles]
        prediction = authored[state]
        actors = [r for r in rows if r[0] == "actor" and r[4] == "1"]
        if [a[1] for a in actors] != ["1"]:
            raise ValueError("Unsupported visible actor configuration")
        (ax, ay, depth, sx, sy, facing, costume_id, *limbs), = [
            list(map(int, r[1:])) for r in rows if r[0] == "draw"]
        if sx != sy or costume_id != 1 or len(limbs) != 16 or not 0 <= depth < meta["mask_count"]:
            raise ValueError("Unsupported actor draw state")
        composed = bytearray(prediction)
        paint_scaled(guy, composed, width, ax, ay, facing, limbs, sx)
        if depth:
            start = packet.index(b"\nDATA\n") + 6 + 95232 + depth * 5760
            composed = apply_depth(composed, prediction, packet[start:start + 5760])
        events.append(dict(kind="object_state", evidence="runtime_observed", tick=frame,
                           script=dict(kind="LSCR", storage_room=24, id=200, pc=25),
                           payload=dict(object_id=246, state=state)))
        frames.append(dict(frame=frame, packet_sha256=sha256(packet).hexdigest(),
                           present_sha256=sha256(display).hexdigest(), state=state, script=script,
                           object_position=pos, inherited_bits=context[2:], actor_draw=rows[[r[0] for r in rows].index("draw")][1:],
                           timer=meta["timer_pair"], cycles=actual_cycles, expected_cycles=expected,
                           archive_pre_palette_difference_indices=archive_changes,
                           pre_palette_mismatches=pre_rgb,
                           depth_sha256=meta["depth_sha256"],
                           back=compare_native_frame(prediction, palette, back, phases[1],
                                                     width=width, height=height),
                           front=compare_native_frame(composed, palette, front, phases[3],
                                                      width=width, height=height),
                           archive_palette_mismatches=sum(archive_palette[i:i+3] != phases[3][i:i+3]
                                                          for i in range(0, 768, 3)),
                           backend_index_mismatches=sum(a != b for a, b in zip(
                               front, backend[meta["top"] * width:(meta["top"] + height) * width]))))
    return dict(schema="p4-scene-events/1", clock="engine_frame", source=dict(
                    game_edition="MI2 original DOS VGA", archive_sha256=DOS_HASHES[1],
                    index_sha256=DOS_HASHES[0], logical_room=24, physical_room=24),
                entry=run["entry"], save_sha256=run["save_sha256"], exe_sha256=run["exe_sha256"],
                engine_version=run["version"], raw_rng_calls="unobserved",
                palette_seed_sha256=seed_sha, events=events, frames=frames)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("game", "capture", "report"):
        parser.add_argument(name, type=Path)
    args = parser.parse_args()
    result = compare(args.game, args.capture)
    _write_new_verified(args.report, serialize_scene_events(result))
    frames = result["frames"]
    print("States:", "".join(str(row["state"]) for row in frames))
    for surface in ("back", "front"):
        print(surface, {field: sum(row[surface][field]["mismatches"] for row in frames)
                        for field in ("indices", "palette")})
    for field in ("pre_palette_mismatches", "archive_palette_mismatches", "backend_index_mismatches"):
        print(field, sum(row[field] for row in frames))
    print("Archive initial differences:", frames[0]["archive_pre_palette_difference_indices"])
    print("Cycle mismatches:", sum(sum(a != b for a, b in zip(row["cycles"], row["expected_cycles"]))
                                   for row in frames))


if __name__ == "__main__":
    main()
