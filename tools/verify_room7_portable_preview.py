"""Read-only portable 87-frame saved Room 7 palette preview verification.

Checks the original DOS VGA MONKEY2.001, ScummVM saved game and play.zip.
Outputs a new metadata-only report under FIXTURE/REPORTS/Room7.
This is NOT a replacement for direct engine-*.bin capture verification.

Example:
  python -B -m tools.verify_room7_portable_preview
      --archive-001 F:/Dev/SCUMMBUCKET/FIXTURE/GAMES/MonkeyIsland2_DOS_VGA/MONKEY2.001
      --save F:/Dev/SCUMMBUCKET/FIXTURE/GAMES/MonkeyIsland2_DOS_VGA/monkey2-1.s01
      --preview-zip PATH/TO/play.zip
      --report F:/Dev/SCUMMBUCKET/FIXTURE/REPORTS/Room7/unique-portable.json
"""
import argparse
import json
from pathlib import Path

from scummbucket.room7_portable_preview import verify_saved_preview


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--archive-001", type=Path, required=True)
    parser.add_argument("--save", type=Path, required=True)
    parser.add_argument("--preview-zip", type=Path, required=True)
    parser.add_argument("--report", type=Path, required=True)
    args = parser.parse_args()
    archive = args.archive_001.resolve()
    output = args.report.resolve()
    game = archive.parent
    fixture = archive.parents[2]
    if (archive.name.upper() != "MONKEY2.001" or
            game.name.upper() != "MONKEYISLAND2_DOS_VGA" or
            game.parent.name.upper() != "GAMES" or
            fixture.name.upper() != "FIXTURE"):
        parser.error("Expected original MONKEY2.001 in canonical FIXTURE/GAMES")
    if (not output.is_relative_to(fixture / "REPORTS" / "Room7") or
            output.suffix.lower() != ".json"):
        parser.error("Report must be JSON under FIXTURE/REPORTS/Room7")
    if output.exists():
        parser.error("Report already exists; refusing overwrite")
    if not output.parent.is_dir():
        parser.error("Report directory does not exist")
    result = verify_saved_preview(
        args.preview_zip, args.save, archive.read_bytes())
    with output.open("x", encoding="utf-8") as stream:
        json.dump(result, stream, indent=2)
    print(json.dumps({
        "status": result["status"],
        "frame_count": result["frame_count"],
        "exact_palette_count": result["exact_palette_count"],
        "mismatching_palette_count": result["mismatching_palette_count"],
        "first_mismatch_frame": result["first_mismatch_frame"],
        "distinct_index_planes": result["distinct_index_planes"],
        "saved_cycle_counters": result["saved_cycle_counters"],
        "raw_engine_buffers_reexamined":
            result["evidence_boundary"]["actual_raw_engine_buffers_reexamined"],
        "report": str(output),
    }, indent=2))
    return 0 if result["status"] == "portable_palettes_matched" else 2


if __name__ == "__main__":
    raise SystemExit(main())
