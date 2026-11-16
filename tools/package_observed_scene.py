"""Create/verify private offline observed scene packages. Never publish game assets."""
import argparse
import json
from pathlib import Path

from scummbucket.observed_scene_package import export_replay_package, verify_replay_package
from tools.compare_cross_room_scene import costumes_from_archive
from tools.replay_observed_scene import compare


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest='command', required=True)
    export = commands.add_parser('export')
    export.add_argument('destination', type=Path)
    for name in ('game', 'capture', 'indexed-report'):
        export.add_argument('--'+name, type=Path, required=True)
    export.add_argument('--room', type=int, required=True)
    verify = commands.add_parser('verify')
    verify.add_argument('destination', type=Path)
    args = parser.parse_args()
    if args.command == 'verify':
        result = verify_replay_package(args.destination)
    else:
        if args.destination.exists() or args.destination.is_symlink():
            parser.error('Output destination already exists')
        comparison, sequence = compare(args.game, args.capture, args.indexed_report, args.room)
        needed = {d['row']['costume'] for p in sequence['frames']
                  for d in p['events'][1]['draw_order']}
        costumes = costumes_from_archive(args.game, needed,
                                         expected_sources=comparison['original_archives'])
        result = export_replay_package(args.game, args.destination, comparison, sequence, costumes)
    print(json.dumps(result, indent=2))
    # Integrity/reproducibility success does not promote historical fidelity.
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
