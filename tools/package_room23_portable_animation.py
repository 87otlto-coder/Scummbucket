"""Package an existing Room 23 native palette export for offline playback.

Never re-captures gameplay, changes old manifest/play.html, or exports game
resources into Git. Both new files use exclusive creation under FIXTURE.
"""
import argparse
from pathlib import Path

from scummbucket.room23_portable_animation import package


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("export",type=Path,help="Existing Room 23 native export directory")
    parser.add_argument("--raw-log",type=Path,required=True,help="Original SBP4 capture matching the export")
    args=parser.parse_args()
    result=package(args.export,args.raw_log)
    print(f"Verified {result['frame_count']} source-indexed Room 23 backgrounds")
    print(f"Continuous trace segments: {len(result['segments'])}")
    print(f"Capture complete: {result['capture_complete']}")
    print(f"Portable preview: {args.export / 'play-standalone.html'}")
    print(f"Metadata: {args.export / 'animation.json'}")


if __name__=="__main__":
    main()
