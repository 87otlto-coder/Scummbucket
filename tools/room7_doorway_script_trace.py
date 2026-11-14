"""Launch a private Room 7 -> 12 -> 7 run with SCUMM opcode tracing.

Uses the pinned, already-built ScummVM-P4-Doorway-20261114-b executable.
Original game files are read-only; every capture/report gets a fresh UUID.
Private script dumps remain only inside FIXTURE.
"""
import argparse
import json
from pathlib import Path

from tools.capture_room7_navigation import capture
from tools.instrument_room7_doorway import BUILD


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, required=True)
    args = parser.parse_args()
    report = capture(args.root.resolve(), BUILD, doorway=True, script_trace=True)
    result = json.loads((report / "script_trace.json").read_text(encoding="utf-8"))
    if result["status"] != "opcode_trace_observed":
        print("Incomplete opcode evidence: preserve capture and report for analysis")
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
