"""Package existing Room 7 PNG frames as a portable single-file HTML preview.

Usage: python -B -m tools.package_room7_preview "PATH_TO_EXISTING_OUTPUT_DIRECTORY"

No archive, ScummVM capture or rerender is required. The original frame PNGs,
manifest, and preview.html are left untouched. A new preview-standalone.html is
created exclusively; existing outputs are never overwritten.
"""
import argparse
import json
from pathlib import Path

from scummbucket.room23_export import PLAYER
from scummbucket.standalone_preview import render_standalone_preview


def package_existing(folder: Path) -> Path:
    folder = Path(folder)
    report = json.loads((folder / "manifest.json").read_text(encoding="utf-8"))
    rows = report.get("frames", [])
    if len(rows) != 87 or any(row.get("mismatches") != 0 for row in rows):
        raise ValueError("Expected 87 verified, zero-mismatch Room 7 frames")
    html = render_standalone_preview(folder, rows, PLAYER)
    output = folder / "preview-standalone.html"
    with output.open("x", encoding="utf-8") as stream:
        stream.write(html)
    return output


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("output_directory", type=Path, help="existing Room 7 output directory containing manifest.json and all frame-*.png")
    args = parser.parse_args()
    print(package_existing(args.output_directory))
