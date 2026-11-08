"""Compare user-supplied ScummVM palette *state traces* to modeled SCUMM v5 cycles.

The independently captured trace must sample the palette immediately after
cyclePalette() and before palManipulate(), from within the SCUMM engine.
ScummBucket never instruments a live game or authenticates external traces.

This is NOT a screenshot comparator, gameplay recording, emulator, script
interpreter, or proof that the supplied trace came from ScummVM.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import re

from .inspector import XOR_KEY, _read_pair, inspect, InspectionError
from .palette_probe import (
    PaletteProbeError, _require, decode_room_background_indexed,
    prepare_cycles, advance_palette,
)

MAX_TRACE_SIZE = 1024 * 1024
MAX_TRACE_SAMPLES = 256
_SHA_PATTERN = re.compile(r"^[0-9a-f]{64}$")


class TraceInvalid(Exception):
    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code


def _valid(condition: bool, code: str, message: str):
    if not condition:
        raise TraceInvalid(code, message)


def _rgb_hex(value: object, label: str) -> bytes:
    _valid(isinstance(value, str) and len(value) == 1536
           and bool(re.fullmatch(r"[0-9a-fA-F]{1536}", value)),
           "TRACE_PALETTE_INVALID", f"{label} must contain 768 RGB bytes as hex")
    return bytes.fromhex(value)


def _validate_trace(trace: object, *, room_id: int, source_sha: str) -> tuple[bytes, list[dict]]:
    _valid(isinstance(trace, dict), "TRACE_FORMAT_INVALID", "Trace must be a JSON object")
    _valid(trace.get("schema_version") == "0.1", "TRACE_VERSION_UNSUPPORTED",
           "Expected palette trace schema_version 0.1")
    _valid(type(trace.get("room_id")) is int and trace["room_id"] == room_id,
           "TRACE_ROOM_MISMATCH", "Trace room ID differs from requested room")
    _valid(trace.get("game_resource_sha256") == source_sha,
           "TRACE_SOURCE_MISMATCH", "Trace resource SHA-256 does not match archive")
    _valid(trace.get("capture_point") == "after_cyclePalette_before_palManipulate",
           "TRACE_CAPTURE_POINT_INVALID",
           "Expected palette captured immediately after cyclePalette, before palManipulate")
    _valid(isinstance(trace.get("engine_commit"), str)
           and 7 <= len(trace["engine_commit"]) <= 100,
           "TRACE_PROVENANCE_MISSING",
           "Record the ScummVM commit/version that produced the trace")
    _valid(isinstance(trace.get("capture_method"), str)
           and bool(trace["capture_method"].strip()),
           "TRACE_PROVENANCE_MISSING",
           "Trace must identify its capture method")
    initial = _rgb_hex(trace.get("initial_palette_rgb_hex"), "Initial palette")
    events = trace.get("samples")
    _valid(isinstance(events, list) and 1 <= len(events) <= MAX_TRACE_SAMPLES,
           "TRACE_SAMPLES_INVALID",
           f"Expected 1..{MAX_TRACE_SAMPLES} ordered trace samples")
    samples = []
    for i, item in enumerate(events, 1):
        _valid(isinstance(item, dict), "TRACE_SAMPLE_INVALID",
               f"Sample {i} must be a JSON object")
        _valid(type(item.get("sequence")) is int and item["sequence"] == i,
               "TRACE_SEQUENCE_INVALID",
               f"Sample sequence must be consecutive starting at 1 (expected {i})")
        for key in ("var_timer", "var_timer_next"):
            _valid(type(item.get(key)) is int and 0 <= item[key] <= 65535,
                   "TRACE_TIMER_INVALID",
                   f"Sample {i}: {key} must be integer 0..65535")
        observation = _rgb_hex(item.get("palette_rgb_hex"), f"Sample {i} palette")
        samples.append({"sequence": i, "var_timer": item["var_timer"],
                        "var_timer_next": item["var_timer_next"],
                        "observed_palette": observation})
    return initial, samples


def compare_palette_samples(initial: bytes, records: list[dict],
                            trace: object, *, room_id: int,
                            source_sha: str) -> dict:
    """Pure comparison with explicit provenance; doesn't read or change files."""
    observed_initial, samples = _validate_trace(
        trace, room_id=room_id, source_sha=source_sha)
    _valid(len(initial) == 768, "INITIAL_PALETTE_INVALID",
           "Original room CLUT must contain 768 RGB bytes")
    if initial != observed_initial:
        indices = [i for i in range(256)
                   if initial[3 * i:3 * i + 3] != observed_initial[3 * i:3 * i + 3]]
        raise TraceInvalid(
            "TRACE_INITIAL_PALETTE_MISMATCH",
            f"Initial captured palette differs from static room CLUT in "
            f"{len(indices)} entries (first: {indices[:8]}). "
            "A room-start script, fade or palette manipulation may have changed it; "
            "cannot reproduce this trace from the static baseline.")
    cycles, issues = prepare_cycles(records)
    blocking = [p for p in issues if p["severity"] == "error"]
    _valid(not blocking, "TRACE_UNSUPPORTED_CYCLES",
           f"Room contains unsupported cycle data: {[p['code'] for p in blocking]}")
    modeled = bytearray(initial)
    result = {"status": "success", "samples_checked": 0,
              "samples_matched": 0, "samples_mismatched": 0,
              "first_mismatch_sequence": None, "samples": [],
              "cycle_diagnostics": issues,
              "trace_authenticated": False,
              "gameplay_execution_verified": False,
              "comparison": "ScummVM-style palette values at engine capture point only"}
    for entry in samples:
        delta = max(entry["var_timer"], entry["var_timer_next"])
        events = advance_palette(modeled, cycles, delta=delta)
        expected = bytes(modeled)
        actual = entry["observed_palette"]
        changed = [index for index in range(256)
                   if expected[3 * index:3 * index + 3] != actual[3 * index:3 * index + 3]]
        matched = not changed
        row = {
            "sequence": entry["sequence"],
            "timer": entry["var_timer"],
            "timer_next": entry["var_timer_next"],
            "counter_delta": delta,
            "rotation_events": events,
            "modeled_palette_sha256": hashlib.sha256(expected).hexdigest(),
            "observed_palette_sha256": hashlib.sha256(actual).hexdigest(),
            "palette_matches": matched,
            "differing_palette_entries": len(changed),
            "first_differing_palette_indices": changed[:12],
        }
        result["samples"].append(row)
        result["samples_checked"] += 1
        if matched:
            result["samples_matched"] += 1
        else:
            result["samples_mismatched"] += 1
            if result["first_mismatch_sequence"] is None:
                result["first_mismatch_sequence"] = entry["sequence"]
    if result["samples_mismatched"]:
        result["status"] = "failed"
    return result


def verify_palette_trace(input_path: str | Path, trace_path: str | Path,
                         *, room_id: int) -> dict:
    src, capture = Path(input_path), Path(trace_path)
    report = {
        "schema_version": "0.1", "operation": "verify_palette_trace",
        "status": "failed", "archive": str(src), "trace_file": str(capture),
        "room_id": room_id, "source": {}, "trace_sha256": None,
        "result": None, "diagnostics": [],
        "limitations": [
            "The trace is supplied by the user and cannot be authenticated here.",
            "This compares engine RGB palette data, not final composited screen pixels.",
            "Matching samples do not establish visual playback timing in milliseconds.",
            "Global scripts, palette fades and cycle rate changes are not modeled.",
        ],
    }
    def diag(code: str, message: str, *, severity="error"):
        report["diagnostics"].append({"severity": severity, "code": code,
                                      "message": message})
    if type(room_id) is not int or not 0 <= room_id <= 255:
        diag("ROOM_ID_INVALID", "Room ID must be integer 0..255")
        return report
    try:
        size = capture.stat().st_size
        _valid(1 <= size <= MAX_TRACE_SIZE, "TRACE_SIZE_INVALID",
               f"Trace must be 1..{MAX_TRACE_SIZE} bytes")
        trace_bytes = capture.read_bytes()
        report["trace_sha256"] = hashlib.sha256(trace_bytes).hexdigest()
        trace = json.loads(trace_bytes.decode("utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError, TraceInvalid) as exc:
        diag(getattr(exc, "code", "TRACE_INPUT_ERROR"),
             f"{type(exc).__name__}: {exc}")
        return report

    inv = inspect(src)
    report["diagnostics"].extend(inv["diagnostics"])
    if inv["status"] != "success":
        diag("TRACE_ARCHIVE_INSPECTION_FAILED",
             "Original resource inspection must complete before comparison")
        return report
    target = [room for room in inv["resources"]["rooms"] if room["id"] == room_id]
    if len(target) != 1:
        diag("TRACE_ROOM_NOT_FOUND", f"Expected one room {room_id}, found {len(target)}")
        return report
    try:
        _, raw, _, label = _read_pair(src)
        original_sha = hashlib.sha256(raw).hexdigest()
        _valid(original_sha == inv["sources"][1]["sha256"], "TRACE_ARCHIVE_CHANGED",
               "Archive changed during verification")
        decoded = bytes(byte ^ XOR_KEY for byte in raw)
        room = target[0]
        bg = decode_room_background_indexed(
            decoded, room_offset=room["room_offset"], room_length=room["room_size"])
        report["source"] = {
            "resource_label": label, "resource_sha256": original_sha,
            "room_offset": room["room_offset"], "clut_sha256": bg["initial_palette_sha256"],
            "indexed_background_sha256": bg["pixel_indices_sha256"],
        }
        for issue in bg["diagnostics"]:
            diag(issue["code"], issue["message"], severity=issue["severity"])
        comparison = compare_palette_samples(
            bg["initial_palette"], room["palette_cycles"], trace,
            room_id=room_id, source_sha=original_sha)
        report["result"] = comparison
        report["status"] = comparison["status"]
        if comparison["samples_mismatched"]:
            diag("RUNTIME_PALETTE_MISMATCH",
                 f"{comparison['samples_mismatched']} of "
                 f"{comparison['samples_checked']} palette samples disagree; "
                 f"first mismatch at sequence {comparison['first_mismatch_sequence']}. "
                 "Inspect timing, cycle state, palette manipulation and script interference.")
    except (TraceInvalid, InspectionError, PaletteProbeError,
            OSError, ValueError) as exc:
        diag(getattr(exc, "code", "TRACE_COMPARISON_ERROR"),
             f"{type(exc).__name__}: {exc}")
    return report
