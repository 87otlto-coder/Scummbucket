"""Command-line tools for read-only inspection and selective raw chunk export."""
import argparse
import json
import sys

from .extraction import extract
from .inspector import inspect


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(prog="scummbucket", description="SCUMM resource investigation (initial MI2 DOS scope)")
    sub = parser.add_subparsers(dest="command", required=True)
    command = sub.add_parser("inspect", help="Inspect a ZIP, game folder or MONKEY2.000 file")
    command.add_argument("input")
    command.add_argument("--json", action="store_true", help="Print complete JSON report")
    command.add_argument("--output", help="Write complete JSON report to a new file")
    export = sub.add_parser("extract", help="Export *uninterpreted* SCUMM chunks from a single room")
    export.add_argument("input", help="ZIP, folder or MONKEY2.000 input")
    export.add_argument("--room", type=int, required=True, help="Room ID (0..255)")
    export.add_argument("--tag", help="Optional four-character SCUMM chunk tag, e.g. CYCL")
    export.add_argument("--output-dir", required=True, help="Destination for new chunk files and manifest.json")
    export.add_argument("--representation", choices=("decoded", "stored"), default="decoded",
                        help="decoded removes XOR 0x69; stored preserves exact archive bytes")
    export.add_argument("--json", action="store_true", help="Print full JSON result")
    args = parser.parse_args(argv)

    if args.command == "extract":
        report = extract(args.input, args.output_dir, room_id=args.room,
                         tag=args.tag, representation=args.representation)
        if args.json:
            print(json.dumps(report, indent=2))
        else:
            print(f"Extraction: {report['status']} ({args.input})")
            print("Chunk outcomes: " + ", ".join(f"{k}={v}" for k, v in report["summary"].items()))
            print("Decoded images / animations / audio: 0 (raw chunk export only)")
            for d in report["diagnostics"]:
                print(f"{d['severity'].upper()} {d['code']}: {d['message']}", file=sys.stderr)
        return 0 if report["status"] == "success" else 2

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
            links = report.get("directory_links", {}).get("summary")
            if links:
                print("Directory references: " + ", ".join(f"{k}={v}" for k, v in links.items()))
            print("Decoded/exported assets: 0 (inventory only)")
        for d in report["diagnostics"]:
            print(f"{d['severity'].upper()} {d['code']}: {d['message']}", file=sys.stderr)
    return 0 if report["status"] == "success" else 2
