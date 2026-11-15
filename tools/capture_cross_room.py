"""Capture a fresh Room 7 -> Room 12 -> Room 7 indexed evidence run.

Requires a separately linked, fingerprinted ScummVM-P4-CrossRoom-* build
created by tools.build_cross_room_recorder. Uses original Room 7 save and
ordinary game controls; no debugger jump, artificial walk or game overwrite.
All private binaries, actor states and script dumps remain under FIXTURE.
"""
import argparse
import json
from pathlib import Path

from tools.capture_room7_navigation import capture


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root",type=Path,required=True)
    parser.add_argument("--build",required=True,
        help="Name of a fresh ScummVM-P4-CrossRoom-* folder under TOOLS")
    args=parser.parse_args()
    if ("/" in args.build or "\\" in args.build or
        not args.build.startswith("ScummVM-P4-CrossRoom-")):
        raise ValueError("Pass only a separate fingerprinted cross-room TOOLS build folder name")
    report=capture(args.root.resolve(),args.build,doorway=True,
                   script_trace=True,cross_room=True)
    summary=json.loads((report/"cross-room-indexed.json").read_text(encoding="utf-8"))
    print(json.dumps({
        "status":summary["status"],
        "indexed_frames":summary["indexed_frame_count"],
        "room_frame_counts":summary["rooms"],
        "room12_actors":summary["room12_actor_draw_counts"],
        "presentation_association":summary["association"],
        "scene_fidelity":summary["scene_fidelity"],
        "report":str(report/"cross-room-indexed.json"),
    },indent=2))
    return 0 if summary["status"]=="indexed_capture_with_actor7_8_observed" else 2


if __name__=="__main__":
    raise SystemExit(main())
