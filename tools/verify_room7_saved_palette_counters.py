"""Read-only 87-frame forecast from direct ScummVM saved ColorCycle counters.

No counter fitting, no engine execution, no overwrite, no private game bytes
written to SOURCE. A nonzero outcome preserves a full metadata diagnostic.
"""
import argparse
import json
from pathlib import Path

from scummbucket.scummvm_color_cycles import inspect_scummvm_color_cycles
from scummbucket.saved_counter_forecast import forecast_from_saved_counters
from tools.compare_room23_frames import engine, digest
from tools.verify_room7_saved_entry import validate


def analyze(capture, export):
    capture, export = Path(capture).resolve(), Path(export).resolve()
    gate = validate(capture)
    manifest_raw = (export / "manifest.json").read_bytes()
    manifest = json.loads(manifest_raw)
    run = json.loads((capture / "run.json").read_bytes())
    if (manifest.get("room_id") != 7 or
            set(run["archives"].values()) !=
            {row["sha256"] for row in manifest["sources"]}):
        raise ValueError("Archive provenance or room does not match saved capture")
    archive_cycles = manifest["scene"]["palette_cycles"]
    saved = inspect_scummvm_color_cycles(
        capture / "saves/monkey2.s01", archive_cycles
    )
    if saved["saved_room"] != 7 or saved["saved_room_resource"] != 7:
        raise ValueError("Direct decoded saved game is not Room 7")
    first_palette = None
    pairs = []
    for n in range(1, 88):
        meta, palettes, _, _, _ = engine(
            (capture / f"engine-{n:03}.bin").read_bytes(), n)
        if first_palette is None:
            first_palette = palettes[0]
        pairs.append({
            "timer_pair": meta["timer_pair"],
            "post_palette": palettes[1],
        })
    result = forecast_from_saved_counters(
        archive_cycles, saved["cycles"], first_palette, pairs)
    result.update({
        "capture": str(capture),
        "export": str(export),
        "export_manifest_sha256": digest(manifest_raw),
        "save_sha256": gate["summary"]["copied_save_sha256"],
        "trace_sha256": gate["summary"]["trace_sha256"],
        "frame_pairs_verified": gate["summary"]["frames_checked"],
        "serialized_color_cycle_block_offset": saved["decompressed_block_offset"],
        "serialized_color_cycle_block_sha256": saved["block_sha256"],
        "scummvm_color_cycle_save_schema": saved["schema"],
        "saved_counters_normalized": all(
            c["counter_in_normalized_range"] for c in saved["cycles"]
        ),
    })
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--capture", type=Path, required=True)
    parser.add_argument("--export", type=Path, required=True)
    parser.add_argument("--report", type=Path, required=True)
    args = parser.parse_args()
    capture, report = args.capture.resolve(), args.report.resolve()
    destination = capture.parents[2] / "REPORTS" / "Room7"
    if not report.is_relative_to(destination) or report.suffix.lower() != ".json":
        parser.error("Report must be JSON under FIXTURE/REPORTS/Room7")
    if report.exists():
        parser.error("Report already exists; refusing overwrite")
    result = analyze(args.capture, args.export)
    with report.open("x", encoding="utf8") as handle:
        json.dump(result, handle, indent=2)
    print(json.dumps({
        "status": result["status"],
        "frames_checked": result["frames_checked"],
        "exact_frame_count": result["exact_frame_count"],
        "mismatch_frame_count": result["mismatch_frame_count"],
        "first_mismatch_frame": result["first_mismatch_frame"],
        "mismatch_frames_per_cycle": result["mismatch_frames_per_cycle"],
        "noncycle_mismatch_frames": result["noncycle_mismatch_frames"],
        "saved_cycle_counters": result["saved_cycle_counters"],
        "saved_counter_block_sha256": result["serialized_color_cycle_block_sha256"],
        "report": str(report),
    }, indent=2))
    return 0 if result["status"] == "direct_saved_counter_forecast_matched" else 2


if __name__ == "__main__":
    raise SystemExit(main())
