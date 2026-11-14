"""Bounded metadata audit of SCUMM script/opcode logs from a private doorway run.

The engine's DEBUG_OPCODES channel reports the opcode just fetched, with
offset measured *after* the opcode byte. The log does not carry the tick or
opcode operands. It must not be used to invent per-tick script attribution,
the destination room operand, or the origin of actor placement.
"""
from collections import Counter
from hashlib import sha256
import json
from pathlib import Path
import re

from tools.room7_doorway import read_ticks

MAX_LOG_BYTES = 64 * 1024 * 1024
OPCODE = re.compile(
    r"\bScript (?P<script>\d+), offset 0x(?P<offset>[0-9a-fA-F]+): "
    r"\[(?P<opcode>[0-9a-fA-F]{1,2})\] (?P<name>[A-Za-z_]\w*)\(\)"
)
SCRIPT = re.compile(r"\brun(?:Object)?Script\([^)]*\)(?:\s+from\s+[^\r\n]+)?")
RELEVANT = (
    "loadroom", "putactor", "actorops", "roomops", "walkactor",
    "setbox", "setcamera",
)


def _read_log(path):
    size = path.stat().st_size
    if size > MAX_LOG_BYTES:
        raise ValueError(f"Script trace log exceeds {MAX_LOG_BYTES} bytes: {path}")
    return path.read_text(encoding="utf-8", errors="replace").splitlines()


def summarize(lines):
    """Report executed opcode sites, but do not assign them to engine ticks."""
    counts = Counter()
    sites = {}
    transitions = []
    starts = []
    for line_number, line in enumerate(lines, 1):
        opcode = OPCODE.search(line)
        if opcode:
            name = opcode["name"]
            script = int(opcode["script"])
            offset_after_opcode = int(opcode["offset"], 16)
            raw_opcode = int(opcode["opcode"], 16)
            counts[name] += 1
            key = (script, offset_after_opcode, raw_opcode, name)
            if key not in sites:
                sites[key] = {
                    "script_number": script,
                    "offset_after_opcode": offset_after_opcode,
                    "probable_opcode_start": offset_after_opcode - 1,
                    "opcode": f"0x{raw_opcode:02X}",
                    "handler": name,
                    "first_log_line": line_number,
                    "executions": 0,
                }
            sites[key]["executions"] += 1
            if any(term in name.lower() for term in RELEVANT):
                transitions.append({
                    "line": line_number, "script_number": script,
                    "offset_after_opcode": offset_after_opcode,
                    "opcode": f"0x{raw_opcode:02X}", "handler": name,
                    "context_before": lines[max(0, line_number - 4):line_number - 1],
                    "context_after": lines[line_number:min(len(lines), line_number + 3)],
                })
        else:
            match = SCRIPT.search(line)
            if match:
                starts.append({"line": line_number, "message": match.group(0)})
    return {
        "opcode_observations": sum(counts.values()),
        "opcode_counts": dict(sorted(counts.items())),
        "opcode_sites": sorted(sites.values(),
                              key=lambda r: (r["script_number"], r["offset_after_opcode"])),
        "potential_transition_opcode_events": transitions,
        "script_start_messages": starts[:2000],
        "script_start_messages_truncated": len(starts) > 2000,
    }


def analyze(capture, report):
    """Write a new metadata-only report; never export script bytes into SOURCE."""
    capture, report = Path(capture), Path(report)
    run = json.loads((capture / "run.json").read_text(encoding="utf-8"))
    if run.get("capture_mode") != "doorway" or not run.get("script_trace"):
        raise ValueError("Not a script-tracing doorway capture")
    ticks = read_ticks((capture / "ticks.tsv").read_text(encoding="utf-8").splitlines())
    changes = []
    previous_room = None
    for tick, row in ticks.items():
        if previous_room is not None and previous_room != row["room"]:
            before = ticks[tick - 1]
            changes.append({
                "tick_before": tick - 1,
                "tick_after": tick,
                "room_before": previous_room,
                "room_after": row["room"],
                "world_before": before["world"],
                "world_after": row["world"],
                "box_before": before["walkbox"],
                "box_after": row["walkbox"],
                "scale_before": before["scale"],
                "scale_after": row["scale"],
                "plane_before": before["draw_plane"],
                "plane_after": row["draw_plane"],
            })
        previous_room = row["room"]
    if [(c["room_before"], c["room_after"]) for c in changes] != [(7, 12), (12, 7)]:
        raise ValueError("Expected exactly two transitions: 7 to 12, then 12 to 7")

    candidates = []
    for name in ("console.log", "runtime.log"):
        path = capture / name
        if path.exists():
            raw = path.read_bytes()
            if len(raw) > MAX_LOG_BYTES:
                raise ValueError(f"Excessive script log size: {name}")
            details = summarize(raw.decode("utf-8", errors="replace").splitlines())
            candidates.append((details["opcode_observations"], name,
                               sha256(raw).hexdigest(), details))
    if not candidates:
        raise ValueError("Neither console.log nor runtime.log is available")
    _, log_name, log_hash, trace = max(candidates, key=lambda r: r[0])

    dump_dir = capture / "dumps"
    dumps = []
    if dump_dir.is_dir():
        for path in sorted(dump_dir.rglob("*")):
            if path.is_file():
                data = path.read_bytes()
                dumps.append({
                    "file": str(path.relative_to(capture)),
                    "size": len(data),
                    "sha256": sha256(data).hexdigest(),
                })

    result = {
        "schema": "room7-script-trace/1",
        "status": "opcode_trace_observed" if trace["opcode_observations"]
                  else "script_opcode_debug_channel_missing",
        "evidence": {
            "room_changes": "engine_observed_on_consecutive_ticks",
            "script_opcode_sites": "engine_debug_channel_observed",
            "script_dump_files": "engine_dumped_private_resource_bytes_hash_only",
            "opcode_operands": "not_captured_by_debug_channel",
            "direct_opcode_to_tick_synchronization": False,
            "script_source_alignment": "not_yet_independently_disassembled",
        },
        "capture": str(capture),
        "engine_exe_sha256": run["exe_sha256"],
        "tick_count": len(ticks),
        "room_changes": changes,
        "selected_log": log_name,
        "selected_log_sha256": log_hash,
        "log_candidates": [{"file": item[1], "opcode_observations": item[0],
                            "sha256": item[2]} for item in candidates],
        "private_script_dumps": dumps,
        "limitations": [
            "Opcode debug log does not include decoded operands or tick IDs",
            "A source-level script assignment requires matching the recorded script and offset to archive bytes",
            "Room entry/exit scripts can run nested inside a room-change opcode",
            "No claim of independent indexed-pixel reconstruction for Room 12",
        ],
        **trace,
    }
    output = report / "script_trace.json"
    with output.open("x", encoding="utf-8") as stream:
        json.dump(result, stream, indent=2)
    print(f"Script opcode sites: {len(trace['opcode_sites'])}; "
          f"transition-related events: {len(trace['potential_transition_opcode_events'])}; "
          f"status: {result['status']}; report: {output}")
    return result


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("capture", type=Path)
    parser.add_argument("report", type=Path)
    args = parser.parse_args()
    result = analyze(args.capture, args.report)
    raise SystemExit(0 if result["status"] == "opcode_trace_observed" else 2)
