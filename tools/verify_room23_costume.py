"""Validate independently drawn Room 23 walk frames against the original evidence."""
import argparse
import json
from pathlib import Path

from scummbucket.classic_costume import ClassicCostume, apply_depth, compose
from scummbucket.inspector import inspect, XOR_KEY
from scummbucket.palette_probe import decode_room_background_indexed
from scummbucket.room23_export import INDEX_SHA
from tools.compare_room23_frames import digest, engine
from tools.compare_room23_walk import archive_masks
from tools.run_room23_frames import ARCHIVES


WALK_SHA = "ab34f9c0ccbac98561494e4014addc5fb7a84258eaa5d577556e2bae129f9550"


def differences(candidate, observed):
    if len(candidate) != len(observed):
        raise ValueError("room dimensions differ")
    first = None
    count = 0
    if candidate != observed:
        for i, (predicted, actual) in enumerate(zip(candidate, observed)):
            if actual != predicted:
                count += 1
                if first is None:
                    first = dict(x=i % 320, y=i // 320, predicted=predicted, observed=actual)
    return dict(mismatches=count, first=first, predicted_sha256=digest(candidate),
                observed_sha256=digest(observed))


def verify(fixture):
    game = fixture / "GAMES/MonkeyIsland2_DOS_VGA"
    raw = (fixture / "REPORTS/Room23/walk-20261110-a.json").read_bytes()
    if digest(raw) != WALK_SHA:
        raise ValueError("unexpected walk report")
    evidence = json.loads(raw)
    masks = archive_masks(game)
    inventory = inspect(game)
    resource = (game / "MONKEY2.001").read_bytes()
    if digest(resource) != ARCHIVES["MONKEY2.001"]:
        raise ValueError("unexpected resource")
    data = bytes(b ^ XOR_KEY for b in resource)
    link, = (a for a in inventory["directory_links"]["entries"] if
             a["directory"] == "DCOS" and a["id"] == 1 and a["status"] == "linked")
    off = link["source_offset"]
    chunk = data[off:off + link["byte_length"]]
    costume = ClassicCostume(chunk)
    room, = (r for r in inventory["resources"]["rooms"] if r["id"] == 23)
    bg = decode_room_background_indexed(data, room_offset=room["room_offset"],
                                        room_length=room["room_size"])["indexed_pixels"]
    if digest(bg) != INDEX_SHA:
        raise ValueError("unexpected background")
    rows = []
    for pose in evidence["frames"]:
        seq = pose["id"]
        plane = pose["plane"]
        if plane not in (0, 2):
            raise ValueError("unverified clipping plane")
        positions = pose["limbs"]
        if pose["moving"]:
            positions = costume.drawn_walk_positions(pose["frame"], pose["facing"], positions)
        actor, limbs = compose(costume, bg, 320, pose["x"], pose["y"], pose["facing"], positions)
        mask = masks[plane]
        clipped = apply_depth(actor, bg, mask)
        row = dict(id=seq, plane=plane, recorded_positions=pose["limbs"],
                   foot=[pose["x"], pose["y"]], facing=pose["facing"], limbs=limbs,
                   suppressed_indices=sum(a != b for a, b in zip(actor, clipped)))
        for mode, predicted in (("control", actor), ("normal", clipped)):
            folder = fixture / f"CAPTURES/Room23/walk-20261110-a-{mode}"
            capture = (folder / f"engine-{seq:03}.bin").read_bytes()
            if digest(capture) != pose[mode]["engine"]:
                raise ValueError(f"capture fingerprint mismatch at {mode}/{seq}")
            meta, _, back, front, _ = engine(capture, seq)
            if back != bg or meta["depth_sha256"] != [digest(m) for m in masks]:
                raise ValueError(f"background or mask mismatch at {mode}/{seq}")
            row[mode] = differences(predicted, front)
        rows.append(row)
    return dict(schema="room23-costume/1", archives=ARCHIVES, walk_sha256=WALK_SHA,
                evidence={"archive-decoded": ["COST cels, offsets, sequences and palette",
                                              "room background and depth masks"],
                          "engine-observed": ["actor state, indexed reference planes"],
                          "inferred": ["draw-phase cursor from one walk advance",
                                       "native scale, default palette and foot origin"],
                          "unsupported": ["ZP01 actor clipping", "other costumes and routes"]},
                cost_offset=off, cost_sha256=digest(chunk), mask_sha256=digest(masks[2]),
                background_sha256=INDEX_SHA, frames=rows,
                totals={mode: sum(r[mode]["mismatches"] for r in rows) for mode in ("control", "normal")})


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("fixture", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    result = verify(args.fixture)
    with args.output.open("x", encoding="utf8") as out:
        json.dump(result, out, indent=2)
    print(result["totals"])
    raise SystemExit(int(any(result["totals"].values())))
