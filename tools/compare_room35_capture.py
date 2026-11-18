"""Compare captured Room 35 frames against archive-derived waterfall samples."""
import argparse
from hashlib import sha256
import json
from pathlib import Path

from scummbucket.classic_costume import ClassicCostume, apply_depth
from scummbucket.classic_scale import paint_scaled
from scummbucket.inspector import XOR_KEY, _read_pair, chunks, inspect
from scummbucket.object_images import decode_indexed_object_state
from scummbucket.room35_waterfall import paint_indexed_layer
from scummbucket.native_frame_compare import compare_native_frame
from scummbucket.palette_probe import advance_palette, decode_room_background_indexed, prepare_cycles
from tools.compare_room23_frames import engine


def retain_unchanged_front(previous, background, actors):
    """Carry the previously reconstructed pose across an idle redraw omission."""
    if not any(actor[0] == "actor" and actor[4] == "1" for actor in actors):
        return background
    if previous is None or previous[:2] != (background, actors):
        raise ValueError("Visible actor has no draw record or unchanged prior pose")
    return previous[2]


def compare(game, export, capture):
    manifest = json.loads((export / "manifest.json").read_bytes())
    run = json.loads((capture / "run.json").read_bytes())
    if run["entry"] != "debugger_equivalent_room_entry":
        raise ValueError("Expected debugger-equivalent capture")
    index, resource, _, _ = _read_pair(game)
    for name, blob in (("MONKEY2.000", index), ("MONKEY2.001", resource)):
        if sha256(blob).hexdigest() != run["archives"][name]:
            raise ValueError("Capture and source archive fingerprints differ")
    inventory = inspect(game)
    room, = (row for row in inventory["scene_inventory"]["rooms"] if row["room_id"] == 35)
    decoded = bytes(v ^ XOR_KEY for v in resource)
    bg = decode_room_background_indexed(decoded,
                                        room_offset=room["room_offset"], room_length=room["room_size"])
    cycles, _ = prepare_cycles(room["palette_cycles"])
    rasters = {n: (export / f"state-{n:02}.indices").read_bytes() for n in range(1, 9)}
    for number, raster in rasters.items():
        if sha256(raster).hexdigest() != manifest["files"][f"state-{number:02}.indices"]:
            raise ValueError("Export raster hash differs")
    width, height = bg["width"], bg["height"]
    source_bg = bg["indexed_pixels"]
    palette = bytearray(bg["initial_palette"])
    seeded_palette = None
    seeded_cycles, _ = prepare_cycles(room["palette_cycles"])
    placement, = (e["payload"] for e in manifest["events"] if e["kind"] == "object_position")
    x, y = placement["x"], placement["y"]
    obj_width, obj_height = manifest["states"][0]["width"], manifest["states"][0]["height"]
    region = [row * width + col for row in range(y, min(y + obj_height, height))
              for col in range(x, min(x + obj_width, width))]
    member, = (r for r in inventory["directory_links"]["entries"]
               if r["directory"] == "DCOS" and r["id"] == 1 and r["status"] == "linked")
    start = member["source_offset"]
    guy = ClassicCostume(decoded[start:start + member["byte_length"]])
    trns, = (n for n in chunks(decoded, room["room_offset"] + 8,
                              room["room_offset"] + room["room_size"], "ROOM") if n.tag == "TRNS")
    objects = {obj["object_id"]: obj for obj in room["objects"]}
    object_layers = {}
    rows = []
    previous = None
    for frame in range(1, 33):
        packet = (capture / f"engine-{frame:03}.bin").read_bytes()
        meta, phases, back, front, backend = engine(packet, frame)
        lines = [line.split() for line in meta["state"]]
        entry, = (list(map(int, line[1:])) for line in lines if line[0] == "room35")
        effective = int(bool(run["injected_bit92"] or run["injected_bit567"]))
        if entry != [35, 35, effective, run["injected_bit567"]]:
            raise ValueError(f"Frame {frame} has unexpected room or effective bits: {entry}")
        camera, = (list(map(int, line[1:])) for line in lines if line[0] == "camera")
        if camera[2:] != [0, 0, width, height, width, height]:
            raise ValueError(f"Frame {frame} differs from the authored viewport")
        state, = (int(line[2]) for line in lines if line[:2] == ["object", "364"])
        pos, = (list(map(int, line[2:])) for line in lines if line[:2] == ["position", "364"])
        if pos != [x, y]:
            raise ValueError(f"Frame {frame} object position differs from archive: {pos}")
        observed_cycles = [list(map(int, line[1:])) for line in lines if line[0] == "cycle"]
        if [r[:2] + r[3:] for r in observed_cycles] != [
                [c["id"], c["delay_counter_units"], c["flags_raw"], c["start_color"], c["end_color"]]
                for c in cycles]:
            raise ValueError(f"Frame {frame} differs from authored cycle definitions")
        before = bytes(palette)
        delta = max(meta["timer_pair"])
        advance_palette(palette, cycles, delta=delta)
        if seeded_palette is None:
            seeded_palette = bytearray(phases[0])
        advance_palette(seeded_palette, seeded_cycles, delta=delta)
        prediction = source_bg if state == 0 else rasters[state]
        front_result = compare_native_frame(prediction, palette, front, phases[3],
                                            width=width, height=height)
        back_result = compare_native_frame(prediction, palette, back, phases[1],
                                           width=width, height=height)
        # Existing v5 room-object renderer traverses local object slots in reverse.
        sets = [(int(line[1]), int(line[2])) for line in lines if line[0] == "object"]
        positions = {int(line[1]): tuple(map(int, line[2:])) for line in lines if line[0] == "position"}
        extended = prediction
        if state == 0:
            for key in reversed(sets):
                number, selected = key
                if not selected:
                    continue
                if key not in object_layers:
                    info, idx, alpha, _ = decode_indexed_object_state(
                        decoded, obim_offset=objects[number]["image"]["source_offset"],
                        state_tag=f"IM{selected:02X}", transparent_color=decoded[trns.offset + 8])
                    object_layers[key] = idx, alpha, info["width"], info["height"]
                extended = paint_indexed_layer(extended, width, height, *object_layers[key],
                                               *positions[number])
        extended_back = compare_native_frame(extended, seeded_palette, back, phases[1],
                                             width=width, height=height)
        draw = [list(map(int, line[1:])) for line in lines if line[0] == "draw"]
        actors = tuple(tuple(line) for line in lines if line[0] in ("actor", "scale"))
        # Only actor rows carry the visibility field. Scale is also part of the
        # stable-pose check below.
        if draw:
            extended_front = bytearray(extended)
            (ax, ay, plane, sx, sy, facing, costume, *limbs), = draw
            if len(limbs) != 16 or sx != sy or costume != 1:
                raise ValueError("Unexpected ego draw state")
            paint_scaled(guy, extended_front, width, ax, ay, facing, limbs, sx)
            if plane:
                offset = packet.index(b"\nDATA\n") + 6 + 95232 + plane * 5760
                packed = packet[offset:offset + 5760]
                if not 0 < plane < meta["mask_count"]:
                    raise ValueError("Actor depth plane is out of range")
                extended_front = apply_depth(extended_front, extended, packed)
        else:
            extended_front = retain_unchanged_front(previous, extended, actors)
        previous = extended, actors, bytes(extended_front)
        extended_front_result = compare_native_frame(extended_front, seeded_palette, front, phases[3],
                                                     width=width, height=height)
        rows.append(dict(extended_back=extended_back, extended_front=extended_front_result,
                         archive_palette_difference_indices=[i // 3 for i in range(0, 768, 3)
                                                             if before[i:i+3] != phases[0][i:i+3]], frame=frame, sha256=sha256(packet).hexdigest(),
                         state=state, bits=entry[2:], timer=meta["timer_pair"],
                         depth_sha256=meta["depth_sha256"], engine_cycles=observed_cycles,
                         predicted_counters=[c["counter"] for c in cycles],
                         script202=[line[1:] for line in lines if line[:1] == ["script"] and line[2] == "202"],
                         objects=[line[1:] for line in lines if line[0] == "object"],
                         pre_palette_entries=sum(before[i:i+3] != phases[0][i:i+3] for i in range(0, 768, 3)),
                         seeded_post_palette_entries=sum(seeded_palette[i:i+3] != phases[1][i:i+3]
                                                        for i in range(0, 768, 3)),
                         back=back_result, front=front_result,
                         waterfall_back=sum(prediction[i] != back[i] for i in region),
                         waterfall_front=sum(prediction[i] != front[i] for i in region),
                         actual_front_backend=sum(a != b for a, b in
                                                  zip(front, backend[meta["top"]*width:(meta["top"]+height)*width]))))
    return dict(entry=run["entry"], exe_sha256=run["exe_sha256"], save_sha256=run["save_sha256"],
                archive_background_sha256=sha256(source_bg).hexdigest(), room=35, selected_frames=len(rows),
                object_region=[x, y, obj_width, obj_height], rows=rows)


if __name__ == "__main__":
    arg = argparse.ArgumentParser(description=__doc__)
    for name in ("game", "export", "capture", "report"):
        arg.add_argument(name, type=Path)
    args = arg.parse_args()
    result = compare(args.game, args.export, args.capture)
    with args.report.open("x", encoding="utf8") as out:
        json.dump(result, out, indent=2)
    frames = result["rows"]
    print("Frames:", len(frames), "states:", [f["state"] for f in frames])
    print("script202 frames:", sum(bool(f["script202"]) for f in frames))
    for target in ("back", "front", "extended_back", "extended_front"):
        print(target, {key: sum(f[target][key]["mismatches"] for f in frames)
                       for key in ("indices", "palette")})
    for key in ("waterfall_back", "waterfall_front", "pre_palette_entries", "seeded_post_palette_entries",
                "actual_front_backend"):
        print(key, sum(f[key] for f in frames))
    print("counter mismatch frames:", sum(f["predicted_counters"] != [c[2] for c in f["engine_cycles"]]
                                           for f in frames))
