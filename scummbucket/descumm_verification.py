"""Verify SCRIPT byte-pattern candidates against external ScummVM Tools descumm.

Only external disassembly output can establish an emitted instruction boundary.
A boundary match does not establish that a branch is reachable or executed.
No ScummVM/descumm code is bundled or redistributed.
"""
from __future__ import annotations

from collections import Counter
import hashlib
from pathlib import Path
import re
import shutil
import subprocess
import tempfile

from .inspector import XOR_KEY, _read_pair, inspect, InspectionError


_OPCODE_LINE = re.compile(r"^\[([0-9A-Fa-f]{1,8})\]\s+\(([0-9A-Fa-f]{2})\)(?:\s|$)", re.MULTILINE)
_MAX_SCRIPT_SIZE = 200 * 1024  # descumm-tool.cpp read buffer limit


def _error(code: str, message: str, *, source: str | None = None,
           offset: int | None = None) -> dict:
    return {"severity": "error", "code": code, "message": message,
            "source": source, "offset": offset}


def _parse_instruction_starts(output: str) -> tuple[dict[int, int], list[dict]]:
    """Read only emitted [relative-offset] (opcode) lines, not arbitrary text."""
    starts: dict[int, int] = {}
    issues: list[dict] = []
    for found in _OPCODE_LINE.finditer(output):
        at, opcode = int(found[1], 16), int(found[2], 16)
        if at in starts:
            issues.append(_error("DESCUMM_OFFSET_DUPLICATE",
                                 f"Disassembler emitted multiple instructions at relative offset 0x{at:X}"))
        else:
            starts[at] = opcode
    return starts, issues


def verify_descumm(input_path: str | Path, *, room_id: int, script_id: int,
                   object_id: int, descumm: str | None = None) -> dict:
    """Verify a single local-script/object's existing candidates using descumm -5.

    Never parses output as execution traces. The only positive assertion is:
    'descumm emitted an opcode at this exact script body relative offset'.
    """
    src = Path(input_path)
    report = {"schema_version": "0.1", "operation": "verify_descumm",
              "status": "failed", "input": str(src),
              "selection": {"room_id": room_id, "script_id": script_id,
                            "object_id": object_id},
              "disassembler": {"tool": "ScummVM Tools descumm", "flags": ["-5", "-o", "-h"],
                               "independent": True, "output_sha256": None,
                               "instruction_starts_emitted": 0},
              "summary": {"candidates": 0, "confirmed_opcode_starts": 0,
                          "not_emitted": 0, "opcode_conflicts": 0},
              "candidates": [], "diagnostics": [],
              "interpretation": ("Verified opcode starts are evidence of correct instruction alignment, "
                                 "NOT evidence of runtime execution or animated scene timing")}
    problems = report["diagnostics"]
    if type(room_id) is not int or not 0 <= room_id <= 255:
        problems.append(_error("ROOM_ID_INVALID", "Room ID must be between 0 and 255"))
        return report
    if type(script_id) is not int or not 0 <= script_id <= 255:
        problems.append(_error("SCRIPT_ID_INVALID", "Local script ID must be between 0 and 255"))
        return report
    if type(object_id) is not int or not 0 <= object_id <= 65535:
        problems.append(_error("OBJECT_ID_INVALID", "Object ID must be between 0 and 65535"))
        return report

    original = inspect(src)
    problems.extend(original["diagnostics"])
    if original["status"] != "success":
        problems.append(_error("VERIFICATION_INSPECTION_FAILED",
                               "Source inspection must succeed before external verification"))
        return report

    scenes = [r for r in original["scene_inventory"]["rooms"] if r["room_id"] == room_id]
    if len(scenes) != 1:
        problems.append(_error("VERIFY_ROOM_NOT_FOUND", f"Room {room_id} is not in the inventory"))
        return report
    scene = scenes[0]
    if not any(o["object_id"] == object_id for o in scene["objects"]):
        problems.append(_error("VERIFY_OBJECT_NOT_FOUND",
                               f"Object {object_id} is not present in room {room_id}"))
        return report
    report["candidates"] = [
        {**c, "disassembly_status": "not_checked"}
        for c in scene.get("script_state_candidates", [])
        if c["script_tag"] == "LSCR" and c["script_id"] == script_id and c["object_id"] == object_id
    ]
    report["summary"]["candidates"] = len(report["candidates"])

    try:
        _, stored, _, label = _read_pair(src)
    except (InspectionError, OSError, ValueError) as exc:
        problems.append(_error("VERIFICATION_SOURCE_READ_FAILED",
                               f"Failed to reopen original game archive: {exc}", source=str(src)))
        return report
    if hashlib.sha256(stored).hexdigest() != original["sources"][1]["sha256"]:
        problems.append(_error("VERIFICATION_SOURCE_CHANGED",
                               "Original resource hash changed since inventory; refusing verification", source=label))
        return report
    decoded = bytes(byte ^ XOR_KEY for byte in stored)
    matches = []
    for item in scene["local_script_chunks"]:
        if item["tag"] != "LSCR":
            continue
        begin, length = item["source_offset"], item["byte_length"]
        if begin < 0 or length < 9 or begin + length > len(decoded):
            problems.append(_error("VERIFY_SCRIPT_RANGE_INVALID",
                                   "Invalid LSCR offset or length", source=label, offset=begin))
            return report
        if decoded[begin:begin + 4] != b"LSCR":
            problems.append(_error("VERIFY_SCRIPT_TAG_INVALID", "Expected LSCR tag",
                                   source=label, offset=begin))
            return report
        if decoded[begin + 8] == script_id:
            matches.append((begin, length))
    if len(matches) != 1:
        problems.append(_error("VERIFY_SCRIPT_MISSING" if not matches else "VERIFY_SCRIPT_AMBIGUOUS",
                               f"Expected exactly one LSCR with script ID {script_id}, found {len(matches)}"))
        return report
    begin, size = matches[0]
    if size > _MAX_SCRIPT_SIZE:
        problems.append(_error("DESCUMM_SCRIPT_TOO_LARGE",
                               f"Script length {size} exceeds descumm's 200 KiB buffer",
                               source=label, offset=begin))
        return report
    chunk = decoded[begin:begin + size]
    report["source"] = {
        "name": label, "sha256": original["sources"][1]["sha256"],
        "script_chunk_offset": begin, "script_length": size,
        "script_chunk_sha256": hashlib.sha256(chunk).hexdigest(),
        "script_body_offset": begin + 9,
    }

    exe = descumm if descumm is not None else shutil.which("descumm")
    if not exe:
        problems.append(_error("DESCUMM_NOT_FOUND",
                               "Install official ScummVM Tools descumm or provide --descumm <executable>"))
        return report
    # A user-supplied command path may be absolute or resolve on PATH.
    if shutil.which(str(exe)) is None and not Path(exe).is_file():
        problems.append(_error("DESCUMM_NOT_FOUND", f"Disassembler does not exist: {exe}",
                               source=str(exe)))
        return report
    report["disassembler"]["executable"] = str(exe)

    try:
        with tempfile.TemporaryDirectory(prefix="scummbucket-descumm-") as directory:
            script_path = Path(directory) / f"room-{room_id:03d}-script-{script_id:03d}.lscr"
            script_path.write_bytes(chunk)
            completed = subprocess.run(
                [str(exe), "-5", "-o", "-h", str(script_path)],
                capture_output=True, text=True, encoding="utf-8", errors="replace",
                timeout=25, check=False,
            )
    except subprocess.TimeoutExpired:
        problems.append(_error("DESCUMM_TIMEOUT", "External disassembler exceeded 25 seconds"))
        return report
    except (OSError, ValueError) as exc:
        problems.append(_error("DESCUMM_EXEC_FAILED",
                               f"Could not run external disassembler: {type(exc).__name__}: {exc}"))
        return report

    # The tool emits a terminal END marker when its disassembly loop completes.
    if completed.returncode != 0:
        problems.append(_error("DESCUMM_NONZERO_EXIT",
                               f"descumm returned exit code {completed.returncode}; "
                               f"stderr excerpt: {completed.stderr[:250]}"))
        return report
    output = completed.stdout
    if len(output) > 4 * 1024 * 1024:
        problems.append(_error("DESCUMM_OUTPUT_EXCESSIVE", "Disassembly output exceeds 4 MiB"))
        return report
    if not output.strip().endswith("END"):
        problems.append(_error("DESCUMM_OUTPUT_INCOMPLETE", "Disassembly has no expected END marker"))
        return report
    if re.search(r"(?im)^\s*(?:error:|unknown opcode|invalid opcode)", output):
        problems.append(_error("DESCUMM_OUTPUT_ERROR",
                               "Disassembler output contains an error or unknown opcode report"))
        return report

    starts, anomalies = _parse_instruction_starts(output)
    problems.extend(anomalies)
    report["disassembler"]["output_sha256"] = hashlib.sha256(output.encode("utf-8")).hexdigest()
    report["disassembler"]["instruction_starts_emitted"] = len(starts)
    if not starts:
        problems.append(_error("DESCUMM_NO_INSTRUCTIONS",
                               "No opcode start lines could be parsed from the output"))
        return report
    if anomalies:
        return report

    tally = Counter()
    for candidate in report["candidates"]:
        relative = candidate["script_body_offset"]
        emitted_opcode = starts.get(relative)
        if emitted_opcode is None:
            candidate["disassembly_status"] = "not_emitted"
            tally["not_emitted"] += 1
        elif emitted_opcode != int(candidate["opcode_hex"], 16):
            candidate["disassembly_status"] = "opcode_conflict"
            candidate["emitted_opcode_hex"] = f"0x{emitted_opcode:02X}"
            tally["opcode_conflicts"] += 1
            problems.append(_error("DESCUMM_OPCODE_CONFLICT",
                                   f"At body offset 0x{relative:X}, expected "
                                   f"{candidate['opcode_hex']}, tool emitted "
                                   f"0x{emitted_opcode:02X}",
                                   source=label, offset=candidate["source_offset"]))
        else:
            candidate["disassembly_status"] = "confirmed_opcode_start"
            candidate["instruction_alignment_verified"] = True
            tally["confirmed_opcode_starts"] += 1
    report["summary"].update({name: tally[name] for name in (
        "confirmed_opcode_starts", "not_emitted", "opcode_conflicts")})
    report["status"] = (
        "failed" if tally["opcode_conflicts"]
        else "partial" if tally["not_emitted"] else "success"
    )
    return report
