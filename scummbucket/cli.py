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

    by_id = sub.add_parser("extract-id", help="Export one verified resource by directory type and ID")
    by_id.add_argument("input", help="ZIP, folder or MONKEY2.000 input")
    by_id.add_argument("--directory", choices=("DROO", "DSCR", "DSOU", "DCOS", "DCHR"),
                       required=True, help="SCUMM v5 index directory")
    by_id.add_argument("--id", type=int, required=True, help="Resource ID within the chosen directory")
    by_id.add_argument("--output-dir", required=True, help="New output directory for chunk and manifest")
    by_id.add_argument("--representation", choices=("decoded", "stored"), default="decoded")
    by_id.add_argument("--json", action="store_true", help="Print full JSON result")
    scene = sub.add_parser("scenes", help="Inspect per-room animation resource candidates (not playback)")
    scene.add_argument("input", help="Original DOS Monkey Island 2 ZIP, folder, or index file")
    scene.add_argument("--room", type=int, help="Show one room ID; omit for all rooms")
    scene.add_argument("--json", action="store_true", help="Print complete scene relationship JSON")
    scene.add_argument("--output", help="Write JSON report to a new file, without overwriting")
    args = parser.parse_args(argv)

    if args.command in ("extract", "extract-id"):
        if args.command == "extract-id":
            report = extract(args.input, args.output_dir, directory=args.directory,
                             resource_id=args.id, representation=args.representation)
        else:
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

    if args.command == "scenes":
        report = inspect(args.input)
        if args.room is not None and not 0 <= args.room <= 255:
            report["diagnostics"].append(
                {"severity": "error", "code": "SCENE_ROOM_INVALID",
                 "message": "Room must be in 0..255", "source": str(args.input),
                 "offset": None, "tag": None, "resource_id": args.room})
            report["status"] = "failed"
        scenes = report.get("scene_inventory", {}).get("rooms", [])
        if args.room is not None and report["status"] != "failed":
            scenes = [r for r in scenes if r["room_id"] == args.room]
            if not scenes:
                report["diagnostics"].append(
                    {"severity": "error", "code": "SCENE_ROOM_NOT_FOUND",
                     "message": f"No scene inventory for room {args.room}",
                     "source": str(args.input), "offset": None, "tag": "ROOM",
                     "resource_id": args.room})
                report["status"] = "failed"
        result = {"schema_version": "0.1", "operation": "scene_candidates",
                  "status": report["status"], "input": report["input"],
                  "selection": {"room_id": args.room},
                  "summary": report.get("scene_inventory", {}).get("summary", {}),
                  "rooms": scenes, "diagnostics": report["diagnostics"],
                  "interpretation": "Resource relationships only; no script control or animation playback verified"}
        if args.output:
            try:
                with open(args.output, "x", encoding="utf-8") as f:
                    json.dump(result, f, indent=2)
                    f.write("\n")
            except OSError as exc:
                print(f"ERROR OUTPUT_WRITE_FAILED: {type(exc).__name__}: {exc}", file=sys.stderr)
                return 2
        if args.json:
            print(json.dumps(result, indent=2))
        else:
            print(f"Scene inventory: {result['status']} ({args.input})")
            for room in scenes:
                pairs = sum(o["status"] == "paired" for o in room["objects"])
                candidates = sum(o["background_animation_candidate"] for o in room["objects"])
                hit_count = len(room.get("script_state_candidates", []))
                print(f"Room {room['room_id']:03d}: objects={pairs} paired, "
                      f"multistate candidates={candidates}, "
                      f"palette cycle records={len(room['palette_cycles'])}, "
                      f"local script chunks={len(room['local_script_chunks'])}, "
                      f"state opcode byte-pattern candidates={hit_count}")
                if args.room is not None:
                    for obj in room["objects"]:
                        hits = [hit for hit in room.get("script_state_candidates", [])
                                if hit["object_id"] == obj["object_id"]]
                        if hits:
                            draws = sum(x["operation_candidate"] == "drawObject" for x in hits)
                            sets = sum(x["operation_candidate"] == "setState" for x in hits)
                            scripts = sorted({x["script_id"] for x in hits if x["script_id"] is not None})
                            print(f"  Object {obj['object_id']}: drawObject={draws}, "
                                  f"setState={sets}, local scripts={scripts} "
                                  f"(byte patterns only; instruction alignment unverified)")
            print("Note: candidates do not establish active animation or script control.")
            for d in report["diagnostics"]:
                print(f"{d['severity'].upper()} {d['code']}: {d['message']}", file=sys.stderr)
        return 0 if result["status"] == "success" else 2

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
