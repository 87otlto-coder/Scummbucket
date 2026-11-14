"""Verify the Room 23 walking experiment. Run as python -m tools.compare_room23_walk."""
import argparse
import json
from pathlib import Path

from scummbucket.inspector import XOR_KEY, chunks, inspect
from scummbucket.object_images import _decode_zplane
from scummbucket.room23_export import INDEX_SHA
from tools.compare_room23_frames import digest, engine, present
from tools.run_room23_frames import ARCHIVES


def archive_masks(game):
    if {name: digest((game / name).read_bytes()) for name in ARCHIVES} != ARCHIVES:
        raise ValueError("unexpected game edition")
    data = bytes(b ^ XOR_KEY for b in (game / "MONKEY2.001").read_bytes())
    room, = (r for r in inspect(game)["resources"]["rooms"] if r["id"] == 23)
    start = room["room_offset"]
    end = start + room["room_size"]
    for tag in ("RMIM", "IM00"):
        node, = (n for n in chunks(data, start + 8, end, "room") if n.tag == tag)
        start, end = node.offset, node.end
    planes = [bytes(5760)]
    for tag in ("ZP01", "ZP02"):
        node, = (n for n in chunks(data, start + 8, end, "IM00") if n.tag == tag)
        pixels = _decode_zplane(data, node, width=320, height=144)
        planes.append(bytes(sum((pixels[i + bit] != 0) << (7 - bit) for bit in range(8))
                            for i in range(0, len(pixels), 8)))
    return planes


def measure(back, normal, control, mask):
    if len(back) != len(normal) or len(back) != len(control) or len(back) != len(mask) * 8:
        raise ValueError("incompatible planes")
    visible = hidden = 0
    xs, ys = [], []
    for i, (bg, actual, candidate) in enumerate(zip(back, normal, control)):
        masked = mask[i // 8] & (128 >> (i % 8))
        if actual != (bg if masked else candidate):
            raise ValueError(f"clipping model mismatch at pixel {i}")
        visible += actual != bg
        if candidate != actual:
            hidden += 1
            xs.append(i % 320)
            ys.append(i // 320)
    return dict(visible=visible, hidden=hidden,
                hidden_bounds=[min(xs), min(ys), max(xs), max(ys)] if xs else None)


def read_frame(folder, seq, masks):
    raw = (folder / f"engine-{seq:03}.bin").read_bytes()
    meta, palettes, bg, front, screen = engine(raw, seq)
    display = (folder / f"present-{seq:03}.bin").read_bytes()
    ms, renderer, image = present(display, seq)
    top = meta["top"] * 320
    if (ms < meta["wall_ms"] or image.size != (320, 200) or
            meta["depth_sha256"] != [digest(m) for m in masks] or digest(bg) != INDEX_SHA or
            screen[top:top + len(front)] != front):
        raise ValueError(f"reference plane or presentation mismatch at {folder.name}/{seq}")
    walk, = (s for s in meta["state"] if s.startswith("walk "))
    plane, control, moving, facing, counter, *limbs = map(int, walk.split()[1:])
    state = [s for s in meta["state"] if s != walk]
    actor, = (s for s in state if s.startswith("actor "))
    actor_id, x, y, visible, costume, frame, box, force = map(int, actor.split()[1:])
    if (actor_id, visible, costume, force) != (1, 1, 1, 0) or plane not in range(3) or len(limbs) != 16:
        raise ValueError(f"unexpected costume state at {seq}")
    pose = dict(x=x, y=y, walkbox=box, frame=frame, plane=plane, moving=moving,
                facing=facing, anim_counter=counter, limbs=limbs, state=state, timer=meta["timer_pair"],
                palettes=[digest(p) for p in palettes])
    evidence = dict(engine=digest(raw), display=digest(display), wall_ms=meta["wall_ms"],
                    present_ms=ms, renderer=renderer)
    return pose, control, bg, front, evidence


def compare(normal, control, game):
    masks = archive_masks(game)
    runs = [json.loads((p / "run.json").read_text()) for p in (normal, control)]
    if ([r["walk"] for r in runs] != ["normal", "control"] or
            any(r["archives"] != ARCHIVES for r in runs) or not runs[0]["save_sha256"] or
            any(runs[0][k] != runs[1][k] for k in ("exe_sha256", "save_sha256", "version"))):
        raise ValueError("unmatched capture provenance")
    rows = []
    for seq in range(1, 88):
        pose, flag, bg, front, a = read_frame(normal, seq, masks)
        other, override, _, candidate, b = read_frame(control, seq, masks)
        if pose != other or flag or override != int(seq > 5):
            raise ValueError(f"unmatched walk at frame {seq}")
        counts = measure(bg, front, candidate, masks[pose["plane"]])
        rows.append(dict(id=seq, **pose, **counts, normal=a, control=b))
    if not (rows[4]["x"] < 200 and rows[-1]["x"] > 250 and rows[-1]["moving"] == 0 and
            any(200 <= r["x"] <= 245 and r["moving"] and r["hidden"] for r in rows)):
        raise ValueError("no completed foreground crossing")
    return dict(schema="room23-walk/1", runs=runs, mask_sha256=[digest(m) for m in masks], frames=rows)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("normal", "control", "game", "output"):
        parser.add_argument("--" + name, type=Path, required=True)
    args = parser.parse_args()
    result = compare(args.normal, args.control, args.game)
    with args.output.open("x", encoding="utf8") as out:
        json.dump(result, out, indent=2)
