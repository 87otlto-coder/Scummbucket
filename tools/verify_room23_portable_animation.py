"""Read-only audit of an existing Room 23 self-contained native preview.

Revalidates every original indexed PNG and palette against the exact SBP4
trace, then checks the saved metadata and embedded HTML against the expected
reconstruction. Does not assert final SDL RGB or Guybrush composition.
"""
import argparse
import json
from pathlib import Path

from scummbucket.room23_portable_animation import (
    prepare, HTML_FILENAME, MANIFEST_FILENAME,
)


def verify(folder, raw_log, game=None):
    folder=Path(folder)
    expected,html=prepare(folder,raw_log,game=game)
    recorded=json.loads((folder/MANIFEST_FILENAME).read_text(encoding="utf-8"))
    if recorded!=expected:
        raise ValueError("Portable Room 23 animation manifest differs from verified source")
    if (folder/HTML_FILENAME).read_text(encoding="utf-8")!=html:
        raise ValueError("Portable Room 23 HTML differs from verified embedded frames/timing")
    return {
        "status":"room23_native_palette_package_verified",
        "room":23,
        "mode":"palette_background_only",
        "frame_count":recorded["frame_count"],
        "segment_count":len(recorded["segments"]),
        "clock_gaps":recorded["clock_gaps"],
        "raw_trace_sha256":recorded["raw_capture_sha256"],
        "capture_complete":recorded["capture_complete"],
        "evidence_boundary":"Index plane, modeled palette, trace bytes and callback timing only; not full-scene SDL rendering",
    }


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("export",type=Path)
    parser.add_argument("--raw-log",type=Path,required=True)
    parser.add_argument("--game",type=Path,help="Original DOS VGA game directory for source CLUT/CYCL verification")
    args=parser.parse_args()
    print(json.dumps(verify(args.export,args.raw_log,game=args.game),indent=2))


if __name__=="__main__":
    main()
