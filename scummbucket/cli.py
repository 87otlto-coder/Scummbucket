"""Minimal CLI: python -m scummbucket inspect ARCHIVE_OR_DIRECTORY [--json]."""
import argparse
import json
import sys
from .inspector import inspect


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(prog="scummbucket", description="Read-only SCUMM asset inventory (initial MI2 DOS scope)")
    sub = parser.add_subparsers(dest="command", required=True)
    command = sub.add_parser("inspect", help="Inspect a ZIP, game folder or MONKEY2.000 file")
    command.add_argument("input")
    command.add_argument("--json", action="store_true", help="Print complete JSON report")
    command.add_argument("--output", help="Write complete JSON report to a separate output path")
    args = parser.parse_args(argv)
    report = inspect(args.input)
    if args.output:
        try:
            with open(args.output, "x", encoding="utf-8") as f:
                json.dump(report, f, indent=2)
                f.write("\n")
        except OSError as exc:
            print(f"ERROR OUTPUT_WRITE_FAILED: {type(exc).__name__}: {exc}", file=sys.stderr)
            return 2
    if args.json:
        print(json.dumps(report, indent=2))
    else:
        print(f"Inspection: {report['status']} ({args.input})")
        if report["detected_game"]:
            r = report["resources"]
            print(f"Game: {report['detected_game']['id']}; rooms: {r['room_count']}; "
                  f"cycles: {r['cycle_count']} in {r['rooms_with_cycles']} rooms; "
                  f"multi-state OBIM: {r['multistate_object_images']}")
            print("Decoded/exported assets: 0 (inventory only)")
        for d in report["diagnostics"]:
            print(f"{d['severity'].upper()} {d['code']}: {d['message']}", file=sys.stderr)
    return 0 if report["status"] == "success" else 2
