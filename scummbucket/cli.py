"""Command-line tools for read-only inspection and selective raw chunk export."""
import argparse
import json
import sys

from .extraction import extract
from .descumm_verification import verify_descumm
from .inspector import inspect
from .object_images import export_object_images
from .palette_probe import palette_probe
from .palette_trace import verify_palette_trace
from .palette_coverage import export_cycle_coverage
from .palette_sequence import export_palette_sequence


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
    verifier = sub.add_parser("verify-descumm",
        help="Verify SCUMM v5 object-state candidate offsets with external descumm")
    verifier.add_argument("input", help="Original DOS MI2 ZIP, folder, or MONKEY2.000 file")
    verifier.add_argument("--room", type=int, required=True, help="Room ID (0..255)")
    verifier.add_argument("--script", type=int, required=True, help="Room-local LSCR script ID (0..255)")
    verifier.add_argument("--object", type=int, required=True, help="Object ID (0..65535)")
    verifier.add_argument("--descumm", help="Path to official ScummVM Tools descumm executable; defaults to PATH")
    verifier.add_argument("--json", action="store_true", help="Print machine-readable report")
    verifier.add_argument("--output", help="Write report to a new JSON file; never overwrite")
    pictures = sub.add_parser("images", help="Decode one DOS MI2 OBIM object's image states (P2 experimental)")
    pictures.add_argument("input", help="ZIP, game folder or MONKEY2.000 input")
    pictures.add_argument("--room", type=int, required=True, help="Room ID")
    pictures.add_argument("--object", type=int, required=True, help="Object ID")
    pictures.add_argument("--output-dir", required=True, help="Folder for RGBA PNG states and separate mask PNGs")
    pictures.add_argument("--no-masks", action="store_true", help="Skip separate Z-plane mask PNG exports")
    pictures.add_argument("--json", action="store_true", help="Print complete JSON report")
    palette = sub.add_parser(
        "palette-probe",
        help="Export hypothetical room palette-cycle snapshots, NOT observed animation")
    palette.add_argument("input", help="Original DOS MI2 ZIP or game folder")
    palette.add_argument("--room", type=int, required=True)
    palette.add_argument("--ticks", nargs="+", type=int, required=True,
                         help="Synthetic update indices, e.g. 0 35 71 107; NOT milliseconds")
    palette.add_argument("--counter-increment", type=int, default=1,
                         help="Simulated timer counter units added on each update (default 1, not a real runtime measurement)")
    palette.add_argument("--output-dir", required=True, help="New non-overwriting PNG output folder")
    palette.add_argument("--json", action="store_true", help="Print JSON report")
    trace = sub.add_parser("verify-palette-trace",
        help="Compare externally recorded SCUMM palette state to source-based cycle simulation")
    trace.add_argument("input", help="Authorized MI2 archive, folder or index file")
    trace.add_argument("--room", type=int, required=True, help="Room ID 0..255")
    trace.add_argument("--trace", required=True, help="JSON trace captured after engine cyclePalette")
    trace.add_argument("--output", help="Write a new JSON verification report; never overwrite")
    trace.add_argument("--json", action="store_true", help="Print complete JSON")
    coverage = sub.add_parser(
        "palette-map",
        help="Export native-coordinate PNG masks for room CYCL palette-index coverage")
    coverage.add_argument("input", help="Original DOS MI2 game archive or directory")
    coverage.add_argument("--room", type=int, required=True, help="Room ID (0..255)")
    coverage.add_argument("--output-dir", required=True,
                          help="New folder for combined overlay, per-cycle masks and manifest")
    coverage.add_argument("--json", action="store_true", help="Print full JSON report")
    sequence = sub.add_parser(
        "palette-sequence",
        help="Export native indexed PNG frames using modeled palette rotations (not engine-verified timing)")
    sequence.add_argument("input", help="Original MI2 archive, game directory or index file")
    sequence.add_argument("--room", type=int, required=True)
    sequence.add_argument("--output-dir", required=True,
                          help="New folder for indexed frames, original CLUT and manifest")
    sequence.add_argument("--fps", type=int, default=30, help="Output playback FPS (1..60; default 30)")
    sequence.add_argument("--duration-seconds", type=int, default=4,
                          help="Whole-second duration; maximum 240 frames total")
    sequence.add_argument("--counter-rate", type=int, default=60,
                          help="ASSUMED palette counter units/second (default 60, room23 video estimate)")
    sequence.add_argument("--json", action="store_true", help="Print complete JSON export report")
    args = parser.parse_args(argv)

    if args.command == "palette-sequence":
        report = export_palette_sequence(
            args.input, args.output_dir, room_id=args.room,
            fps=args.fps, duration_seconds=args.duration_seconds,
            counter_rate=args.counter_rate)
        if args.json:
            print(json.dumps(report, indent=2))
        else:
            print(f"Palette animation sequence: {report['status']} ({args.input})")
            summary = report["summary"]
            print(f"Room {args.room}: {summary['frames_written']}/"
                  f"{summary['frames_requested']} frames at {args.fps} fps, "
                  f"{summary['cycle_records']} cycles, "
                  f"{summary['unique_cycled_source_pixels']} source pixel positions")
            print(f"Timing: {report['timing']['model']}; "
                  f"assumed {args.counter_rate} counter units/second")
            print("Frames are lossless indexed PNGs with changing PLTE chunks. "
                  "The original indexed background and CLUT are exported separately.")
            print("Not engine-clock verified; actor/object overlays, scene masks "
                  "and script changes are not included.")
            for issue in report["diagnostics"]:
                print(f"{issue['severity'].upper()} {issue['code']}: "
                      f"{issue['message']}", file=sys.stderr)
        return 0 if report["status"] == "success" else 2

    if args.command == "palette-map":
        report = export_cycle_coverage(
            args.input, args.output_dir, room_id=args.room)
        if args.json:
            print(json.dumps(report, indent=2))
        else:
            print(f"Palette-cycle pixel map: {report['status']} ({args.input})")
            summary = report["summary"]
            print(f"Room {args.room}: {summary.get('cycle_records', 0)} cycle definitions, "
                  f"{summary.get('union_pixel_count', 0)} unique indexed-background "
                  "pixel positions covered")
            for cycle in summary.get("cycles", []):
                print(f"  Cycle {cycle['id']}: colors "
                      f"{cycle['start_color']}-{cycle['end_color']}, "
                      f"pixels={cycle['native_pixel_count']}, "
                      f"bounds={cycle['native_bounds_xyxy_inclusive']}")
            print("Coordinate coverage only; runtime behavior, timing and "
                  "other animation mechanisms remain unverified.")
            for issue in report["diagnostics"]:
                print(f"{issue['severity'].upper()} {issue['code']}: "
                      f"{issue['message']}", file=sys.stderr)
        return 0 if report["status"] == "success" else 2

    if args.command == "verify-palette-trace":
        report = verify_palette_trace(args.input, args.trace, room_id=args.room)
        if args.output:
            try:
                with open(args.output, "x", encoding="utf-8") as f:
                    json.dump(report, f, indent=2)
                    f.write("\n")
            except OSError as exc:
                print(f"ERROR OUTPUT_WRITE_FAILED: {type(exc).__name__}: {exc}",
                      file=sys.stderr)
                return 2
        if args.json:
            print(json.dumps(report, indent=2))
        else:
            summary = report.get("result") or {}
            print(f"External palette trace comparison: {report['status']} ({args.input})")
            print(f"Room {args.room}: {summary.get('samples_checked', 0)} samples, "
                  f"{summary.get('samples_matched', 0)} matches, "
                  f"{summary.get('samples_mismatched', 0)} mismatches")
            print("This checks user-supplied palette state, not screenshot pixels, "
                  "trace authenticity, or playback timing.")
            for issue in report["diagnostics"]:
                print(f"{issue['severity'].upper()} {issue['code']}: "
                      f"{issue['message']}", file=sys.stderr)
        return 0 if report["status"] == "success" else 2

    if args.command == "palette-probe":
        report = palette_probe(
            args.input, args.output_dir, room_id=args.room, ticks=args.ticks,
            counter_increment=args.counter_increment)
        if args.json:
            print(json.dumps(report, indent=2))
        else:
            print(f"Palette probe: {report['status']} ({args.input})")
            print(f"Room {args.room}, counter increment {args.counter_increment} per update: "
                  f"{report['summary']['snapshots']} hypothetical PNG snapshots, "
                  f"{report['summary']['cycle_records']} cycle records, "
                  f"{report['summary']['visible_cycle_pixels']} background pixel positions "
                  "using cycled palette indices")
            for snapshot in report["snapshots"]:
                print(f"  Synthetic update {snapshot['synthetic_update_index']} "
                      f"(cumulative counter units {snapshot['cumulative_counter_units']}): "
                      f"{snapshot['visible_changed_pixels_vs_initial']} visually changed "
                      f"pixel positions vs initial, {snapshot['cycle_rotation_events']} "
                      "cycle rotation events")
            print("These are synthetic palette updates; real gameplay execution "
                  "and timing remain unverified.")
            for issue in report["diagnostics"]:
                print(f"{issue['severity'].upper()} {issue['code']}: {issue['message']}",
                      file=sys.stderr)
        return 0 if report["status"] == "success" else 2

    if args.command == "images":
        report = export_object_images(
            args.input, args.output_dir, room_id=args.room,
            object_id=args.object, include_masks=not args.no_masks)
        if args.json:
            print(json.dumps(report, indent=2))
        else:
            print(f"Image-state export: {report['status']} ({args.input})")
            print("State outcomes: " + ", ".join(
                f"{k}={v}" for k, v in report["summary"].items()))
            print("Output: RGBA state images and separate Z-plane masks; "
                  "pixel fidelity vs ScummVM NOT verified")
            for diag in report["diagnostics"]:
                print(f"{diag['severity'].upper()} {diag['code']}: {diag['message']}",
                      file=sys.stderr)
        return 0 if report["status"] == "success" else 2

    if args.command == "verify-descumm":
        report = verify_descumm(args.input, room_id=args.room, script_id=args.script,
                                object_id=args.object, descumm=args.descumm)
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
            counts = report["summary"]
            print(f"External disassembly verification: {report['status']} ({args.input})")
            print(f"Room {args.room}, LSCR {args.script}, object {args.object}: "
                  f"patterns={counts['candidates']}, "
                  f"confirmed instruction starts={counts['confirmed_opcode_starts']}, "
                  f"not emitted={counts['not_emitted']}, conflicts={counts['opcode_conflicts']}")
            print("This verifies instruction boundaries only, not runtime execution or animation timing.")
            for item in report["candidates"]:
                print(f"  0x{item['source_offset']:08X} {item['operation_candidate']}: "
                      f"{item['disassembly_status']}")
            for d in report["diagnostics"]:
                print(f"{d['severity'].upper()} {d['code']}: {d['message']}", file=sys.stderr)
        return 0 if report["status"] == "success" else 2

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
