"""Verify ordered-event reconstruction against original indexed engine captures.

Reads original archives/captures, emits JSON only. Existing reports and outputs
are never overwritten. Object visibility and missing actor draws are not inferred.
"""
import argparse
from copy import deepcopy
from hashlib import sha256
import json
from pathlib import Path

from scummbucket.observed_scene_replay import (
    observed_frame_packet, replay_observed_frame, compare_native_frame)
from scummbucket.scene_source import load_scene
from tools.compare_cross_room_scene import costumes_from_archive
from tools.compare_room23_frames import engine
from tools.verify_cross_room_capture import parse_draw_actor


def read_observed_packet(raw, row, scene):
    """Bind report identities back to the raw snapshot, including ordered draws."""
    if sha256(raw).hexdigest() != row["raw_sha256"]:
        raise ValueError("Original raw engine record changed")
    meta, palettes, background, front, backend = engine(raw, row["indexed_frame"])
    if (sha256(front).hexdigest() != row["front_sha256"] or
            sha256(background).hexdigest() != row["background_sha256"] or
            sha256(palettes[3]).hexdigest() != row["final_palette_sha256"]):
        raise ValueError("Original indexed evidence hash mismatch")
    states = meta["state"]
    identities = [s.split() for s in states if s.startswith("scene ")]
    if identities != [["scene", str(row["room"]), str(row["tick"])]]:
        raise ValueError("Raw scene/tick identity disagrees with report")
    cameras = [s.split() for s in states if s.startswith("camera ")]
    if len(cameras) != 1 or len(cameras[0]) != 9:
        raise ValueError("Missing/ambiguous observed camera")
    _, _, left, top, width, height, room_w, room_h = map(int, cameras[0][1:])
    if [room_w, room_h] != scene["manifest"]["dimensions"] or [width, height] != [320, 144]:
        raise ValueError("Recorded camera/source geometry mismatch")
    actors = [parse_draw_actor(s) for s in states if s.startswith("draw_actor ")]
    if actors != row["actors"]:
        raise ValueError("Raw ordered draw state disagrees with report")
    if backend[meta["top"]*320:(meta["top"]+144)*320] != front:
        raise ValueError("Indexed front/backend crop mismatch")
    packet = observed_frame_packet(frame_id=row["indexed_frame"], tick=row["tick"],
                                   room_id=row["room"], viewport=[left, top, width, height],
                                   actors=actors, palette=palettes[3], raw_sha256=row["raw_sha256"])
    return packet, background, front, palettes[3]


def compare(game, capture, indexed_report, room_id):
    capture, indexed_report = Path(capture), Path(indexed_report)
    report_bytes = indexed_report.read_bytes()
    evidence = json.loads(report_bytes)
    if evidence.get("schema") != "scummbucket-cross-room-indexed-evidence/1":
        raise ValueError("Unsupported indexed capture report")
    rows = [r for r in evidence["frames"] if r["room"] == room_id]
    if not rows or len(rows) > 1000:
        raise ValueError("Missing/excessive observed room frames")
    if any(a["indexed_frame"] >= b["indexed_frame"] or a["tick"] > b["tick"]
           for a, b in zip(rows, rows[1:])):
        raise ValueError("Observed frame/tick order regression")
    scene = load_scene(game, room_id)
    costumes = costumes_from_archive(game, {a["costume"] for r in rows for a in r["actors"]})
    findings, packets = [], []
    for row in rows:
        raw = (capture / f"engine-{row['indexed_frame']:03}.bin").read_bytes()
        packet, background, front, palette = read_observed_packet(raw, row, scene)
        result = replay_observed_frame(scene, costumes, packet)
        comparison = compare_native_frame(result, front, palette)
        unmasked = replay_observed_frame(scene, costumes, packet, mask_enabled=False)
        shifted = deepcopy(packet)
        for draw in shifted["events"][1]["draw_order"]:
            draw["row"]["screen_x"] += 1
        moved = replay_observed_frame(scene, costumes, shifted)
        left, top, width, height = packet["viewport"]
        sw = scene["manifest"]["dimensions"][0]
        source_crop = b"".join(scene["background"][(top+y)*sw+left:(top+y)*sw+left+width]
                               for y in range(height))
        findings.append(dict(indexed_frame=row["indexed_frame"], tick=row["tick"],
                             viewport=packet["viewport"], raw_sha256=row["raw_sha256"],
                             actor_order=[a["id"] for a in row["actors"]], **comparison,
                             source_background_errors=sum(a != b for a, b in zip(source_crop, background)),
                             mask_disabled_errors=compare_native_frame(unmasked, front, palette)["indexed_errors"],
                             actors_shifted_right_errors=compare_native_frame(moved, front, palette)["indexed_errors"]))
        packets.append(packet)
    errors = sum(r["indexed_errors"] for r in findings)
    background_errors = sum(r["source_background_errors"] for r in findings)
    palette_errors = sum(r["palette_byte_errors"] for r in findings)
    result = dict(schema="scummbucket-observed-event-replay-comparison/1",
                  status="observed_samples_exact" if errors == background_errors == palette_errors == 0 else "PARTIAL",
                  room_id=room_id, samples=len(findings),
                  exact_frames=sum(r["indexed_errors"] == 0 for r in findings),
                  indexed_pixel_observations=len(findings)*46080,
                  indexed_errors=errors, source_background_errors=background_errors,
                  palette_byte_errors=palette_errors,
                  palette_evidence="engine_observed_snapshot; not independently predicted cycling",
                  mask_disabled_errors=sum(r["mask_disabled_errors"] for r in findings),
                  actors_shifted_right_errors=sum(r["actors_shifted_right_errors"] for r in findings),
                  original_archives=scene["manifest"]["sources"],
                  room_sha256=scene["manifest"]["room_sha256"],
                  indexed_report_sha256=sha256(report_bytes).hexdigest(),
                  timing="sampled_engine_tick_identity_only; no interpolation or milliseconds inferred",
                  unsupported=["automatic script/object state execution", "unobserved object draw order",
                               "unrecorded actor persistence", "SDL display-phase validation"],
                  frames=findings)
    return result, dict(schema="scummbucket-observed-scene-sequence/1", room_id=room_id,
                        source_room_sha256=result["room_sha256"],
                        indexed_report_sha256=result["indexed_report_sha256"], frames=packets)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("game", "capture", "indexed-report", "output"):
        parser.add_argument("--" + name, type=Path, required=True)
    parser.add_argument("--room", type=int, required=True)
    parser.add_argument("--events-output", type=Path)
    args = parser.parse_args()
    for path in (args.output, args.events_output):
        if path is not None and (path.exists() or path.is_symlink()):
            parser.error(f"Refusing existing output: {path}")
    if args.events_output is not None and args.output.resolve() == args.events_output.resolve():
        parser.error("Comparison and events output must differ")
    result, sequence = compare(args.game, args.capture, args.indexed_report, args.room)
    with args.output.open("x", encoding="utf-8") as out:
        json.dump(result, out, indent=2)
    if args.events_output is not None:
        with args.events_output.open("x", encoding="utf-8") as out:
            json.dump(sequence, out, indent=2)
    print(json.dumps({k: v for k, v in result.items() if k not in ("frames", "original_archives")}, indent=2))
    return 0 if result["status"] == "observed_samples_exact" else 2


if __name__ == "__main__":
    raise SystemExit(main())
