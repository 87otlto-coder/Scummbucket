"""Analyze saved Room 7 cycle phases with calibration/heldout separation.

Read-only capture input. Writes metadata report exclusively to a fresh file
under FIXTURE/REPORTS/Room7. Nonzero exit marks unconfirmed palette fidelity.
"""
import argparse
import json
from pathlib import Path

from scummbucket.room7_palette_phase import analyze_saved_palette_cycles
from tools.compare_room23_frames import engine, digest
from tools.verify_room7_saved_entry import validate


def analyze(capture, export, *, calibration_frames=24):
    capture, export = Path(capture).resolve(), Path(export).resolve()
    gate = validate(capture)
    manifest_raw = (export / "manifest.json").read_bytes()
    manifest = json.loads(manifest_raw)
    run = json.loads((capture / "run.json").read_bytes())
    if (manifest.get("room_id") != 7 or
            set(run["archives"].values()) !=
            {row["sha256"] for row in manifest["sources"]}):
        raise ValueError("Archive provenance or room does not match saved capture")
    first_palette, pairs = None, []
    for n in range(1, 88):
        meta, palettes, _, _, _ = engine(
            (capture / f"engine-{n:03}.bin").read_bytes(), n)
        if first_palette is None:
            first_palette = palettes[0]
        pairs.append({
            "timer_pair": meta["timer_pair"],
            "post_palette": palettes[1],
        })
    result = analyze_saved_palette_cycles(
        manifest["scene"]["palette_cycles"], first_palette, pairs,
        calibration_frames=calibration_frames)
    result.update({
        "capture": str(capture),
        "export": str(export),
        "export_manifest_sha256": digest(manifest_raw),
        "save_sha256": gate["summary"]["copied_save_sha256"],
        "trace_sha256": gate["summary"]["trace_sha256"],
        "frame_pairs_checked": gate["summary"]["frames_checked"],
        "trace_samples_total": gate["summary"]["trace_samples_total"],
        "trace_samples_paired": gate["summary"]["trace_samples_paired_to_frames"],
        "trace_samples_unpaired": gate["summary"]["trace_samples_unpaired"],
    })
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--capture", type=Path, required=True)
    parser.add_argument("--export", type=Path, required=True)
    parser.add_argument("--report", type=Path, required=True)
    parser.add_argument("--calibration-frames", type=int, default=24)
    args = parser.parse_args()
    capture, report = args.capture.resolve(), args.report.resolve()
    expected = capture.parents[2] / "REPORTS" / "Room7"
    if not report.is_relative_to(expected) or report.suffix.lower() != ".json":
        parser.error("Report must be JSON under FIXTURE/REPORTS/Room7")
    if report.exists():
        parser.error("Report already exists; refusing overwrite")
    result = analyze(args.capture, args.export,
                     calibration_frames=args.calibration_frames)
    with report.open("x", encoding="utf8") as handle:
        json.dump(result, handle, indent=2)
    print(json.dumps({
        "status": result["status"],
        "calibration_frames": result["calibration_frames"],
        "heldout_frames": result["heldout_frames"],
        "phase_uniquely_identified_count":
            result["phase_uniquely_identified_count"],
        "cycles_without_calibration_solution":
            result["cycles_without_calibration_solution"],
        "heldout_full_palette_matches":
            result["heldout_full_palette_matches"],
        "heldout_ambiguous_frames": len(result["heldout_ambiguous_frames"]),
        "heldout_full_palette_mismatch_frames":
            len(result["heldout_full_palette_mismatch_frames"]),
        "heldout_cycle_mismatch_total":
            result["heldout_cycle_mismatch_total"],
        "heldout_noncycle_changed_frames":
            len(result["heldout_noncycle_changed_frames"]),
        "report": str(report),
    }, indent=2))
    return 0 if result["status"] == "heldout_matched" else 2


if __name__ == "__main__":
    raise SystemExit(main())
