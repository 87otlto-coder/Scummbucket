"""Read-only inspection of ScummVM v124 saved games (gzip or raw).

Usage:
    python -B -m tools.inspect_scummvm_save PATH_TO_SAVE --require-room 7

Prints only non-image metadata and a hash. Does not write or load a save,
does not claim natural gameplay provenance, and supports only format v124.
"""
import argparse
import hashlib
import json
from pathlib import Path
import sys

from scummbucket.scummvm_save import inspect_scummvm_save, SaveFormatError


def inspect(path, *, require_room=None):
    path = Path(path)
    state = inspect_scummvm_save(path)
    result = {
        "schema": "scummvm-save-inspection/1",
        "file_sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
        "size_bytes": path.stat().st_size,
        "state": state,
        "status": "save_metadata_verified",
        "gameplay_entry_verified": False,
    }
    if require_room is not None:
        result["required_room"] = require_room
        if state["current_room"] != require_room or state["room_resource"] != require_room:
            raise SaveFormatError(
                f"Saved room {state['current_room']} / resource "
                f"{state['room_resource']} is not required Room {require_room}"
            )
    return result


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("save", type=Path, help="Original private .s01; no copy or mutation")
    parser.add_argument("--require-room", type=int, choices=range(256), metavar="0..255")
    args = parser.parse_args(argv)
    try:
        result = inspect(args.save, require_room=args.require_room)
    except (OSError, ValueError) as exc:
        parser.exit(2, f"ERROR SAVE_INSPECTION_FAILED: {exc}\n")
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
