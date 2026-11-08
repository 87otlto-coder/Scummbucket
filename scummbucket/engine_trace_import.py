"""Strict importer for private ScummVM P4 palette trace hook output.

The raw log is captured by an independently built, opt-in ScummVM executable.
This parser does not simulate palette cycles or authenticate engine binaries.
"""
from __future__ import annotations

from hashlib import sha256
import json
from pathlib import Path
import re

MAX_LOG_BYTES = 1_000_000
MAX_RESOURCE_BYTES = 150_000_000
MAX_TRACE_SAMPLES = 256
PALETTE_HEX = re.compile(r"^[0-9a-f]{1536}$")
HEX_SHA = re.compile(r"^[0-9a-f]{64}$")
ENGINE_COMMIT = re.compile(r"^[0-9a-f]{40}$")


class EngineTraceError(ValueError):
    def __init__(self, code: str, message: str):
        self.code = code
        super().__init__(message)


def _need(ok: bool, code: str, message: str) -> None:
    if not ok:
        raise EngineTraceError(code, message)


def _integer(token: str, *, label: str, maximum: int) -> int:
    _need(bool(re.fullmatch(r"(?:0|[1-9][0-9]*)", token)),
          "ENGINE_LOG_INTEGER_INVALID", f"{label}: expected unsigned decimal integer")
    value = int(token)
    _need(value <= maximum, "ENGINE_LOG_INTEGER_INVALID",
          f"{label}: value exceeds {maximum}")
    return value


def parse_scummvm_palette_log(data: bytes, *, engine_commit: str,
                                game_resource_sha256: str) -> dict:
    """Parse complete private log into existing verify-palette-trace schema 0.1.

    Requires a BEGIN, consecutive SAMPLE lines, and a matching END. Does not
    mislabel a truncated engine run as successful; count and wall-clock sanity
    checks protect the external provenance contract.
    """
    _need(type(data) is bytes and 1 <= len(data) <= MAX_LOG_BYTES,
          "ENGINE_LOG_SIZE_INVALID", "Raw hook log size must be 1..1,000,000 bytes")
    _need(isinstance(engine_commit, str) and bool(ENGINE_COMMIT.fullmatch(engine_commit)),
          "ENGINE_COMMIT_INVALID", "Supply ScummVM's full lowercase 40-character commit SHA")
    _need(isinstance(game_resource_sha256, str) and bool(HEX_SHA.fullmatch(game_resource_sha256)),
          "ENGINE_SOURCE_HASH_INVALID", "Resource checksum must be lowercase SHA-256")
    try:
        raw = data.decode("ascii")
    except UnicodeDecodeError as exc:
        raise EngineTraceError("ENGINE_LOG_ENCODING_INVALID", "Expected ASCII hook log") from exc
    _need(raw.endswith("\n"), "ENGINE_LOG_INCOMPLETE",
          "Raw hook log lacks its final newline (possible truncation)")
    lines = raw.splitlines()
    _need(len(lines) >= 3, "ENGINE_LOG_INCOMPLETE",
          "Expected BEGIN, one or more SAMPLE lines, and END")
    begin = lines[0].split("|")
    _need(len(begin) == 5 and begin[:2] == ["SBP4", "BEGIN"] and begin[2] == "23",
          "ENGINE_LOG_BEGIN_INVALID", "Expected Room 23 BEGIN record from source hook")
    begin_ms = _integer(begin[3], label="begin_ms", maximum=0xFFFFFFFF)
    _need(bool(PALETTE_HEX.fullmatch(begin[4])), "ENGINE_LOG_PALETTE_INVALID",
          "BEGIN palette must be 768 lowercase RGB hex bytes")
    _need(1 <= len(lines) - 2 <= MAX_TRACE_SAMPLES,
          "ENGINE_LOG_SAMPLES_INVALID", "Expected between 1 and 256 samples")
    samples = []
    prior_ms = begin_ms
    for line_index, line in enumerate(lines[1:-1], 1):
        parts = line.split("|")
        _need(len(parts) == 7 and parts[:2] == ["SBP4", "SAMPLE"],
              "ENGINE_LOG_SAMPLE_INVALID", f"Line {line_index + 1}: invalid SAMPLE record")
        seq = _integer(parts[2], label="sequence", maximum=MAX_TRACE_SAMPLES)
        _need(seq == line_index, "ENGINE_LOG_SEQUENCE_INVALID",
              f"Expected sample {line_index}, found {seq}")
        timer = _integer(parts[3], label="var_timer", maximum=65535)
        timer_next = _integer(parts[4], label="var_timer_next", maximum=65535)
        wall_ms = _integer(parts[5], label="sample_ms", maximum=0xFFFFFFFF)
        _need(wall_ms >= prior_ms and wall_ms - begin_ms <= 600_000,
              "ENGINE_LOG_CLOCK_INVALID",
              f"Sample {seq} has nonmonotonic clock or exceeds 10-minute budget")
        prior_ms = wall_ms
        _need(bool(PALETTE_HEX.fullmatch(parts[6])),
              "ENGINE_LOG_PALETTE_INVALID", f"Sample {seq} palette must be 768 hex RGB bytes")
        samples.append({
            "sequence": seq, "var_timer": timer,
            "var_timer_next": timer_next, "palette_rgb_hex": parts[6],
            "elapsed_ms": wall_ms - begin_ms,
        })
    ending = lines[-1].split("|")
    _need(len(ending) == 4 and ending[:2] == ["SBP4", "END"] and
          ending[3] in ("limit", "room_exit"),
          "ENGINE_LOG_END_INVALID", "Expected explicit END|count|limit or room_exit")
    end_count = _integer(ending[2], label="end_count", maximum=MAX_TRACE_SAMPLES)
    _need(end_count == len(samples) and
          (ending[3] != "limit" or end_count == MAX_TRACE_SAMPLES),
          "ENGINE_LOG_END_MISMATCH", "END count or stop reason disagrees with samples")
    return {
        "schema_version": "0.1",
        "room_id": 23,
        "game_resource_sha256": game_resource_sha256,
        "capture_point": "after_cyclePalette_before_palManipulate",
        "engine_commit": engine_commit,
        "capture_method": "ScummBucket P4 opt-in source hook in ScummVM v2026.4.0",
        "initial_palette_rgb_hex": begin[4],
        "samples": samples,
        "clock_observation": {
            "clock": "ScummVM OSystem::getMillis()",
            "start_millis": begin_ms,
            "last_millis": prior_ms,
            "elapsed_ms": prior_ms - begin_ms,
            "stop_reason": ending[3],
            "samples_recorded": len(samples),
            "is_monotonic_wallclock_not_engine_counter": True,
        },
        "limitations": {
            "runtime_trace_authenticated": False,
            "source_claim_authenticated": False,
            "timer_values_observed_at_cycle_call": True,
            "source_game_archive_reopened_by_scummbucket": False,
            "complete_room_lifetime_captured": ending[3] == "room_exit",
            "engine_commit_supplied_by_operator": True,
        },
    }


def import_scummvm_palette_log(raw_path: str | Path, resource_path: str | Path,
                                output_path: str | Path, *, engine_commit: str,
                                expected_source_sha256: str | None = None) -> dict:
    """Validate raw private hook log and source fingerprint; write once."""
    raw, resource, out = Path(raw_path), Path(resource_path), Path(output_path)
    result = {
        "schema_version": "0.1", "operation": "import_scummvm_palette_log",
        "status": "failed", "raw_log": str(raw), "resource_file": str(resource),
        "output": str(out), "diagnostics": [], "samples": 0,
        "raw_log_sha256": None, "resource_sha256": None,
        "trace_sha256": None, "clock_observation": {},
    }

    output_created = False

    def diag(code: str, message: str):
        result["diagnostics"].append({"severity": "error", "code": code,
                                      "message": message})

    try:
        _need(out.suffix.lower() == ".json", "ENGINE_TRACE_OUTPUT_INVALID",
              "Output must use .json extension")
        _need(not out.exists() and not out.is_symlink() and not out.parent.is_symlink(),
              "OUTPUT_COLLISION", "Output exists or destination is a symlink")
        _need(raw.is_file() and not raw.is_symlink(), "ENGINE_LOG_MISSING",
              "Raw log absent or symlinked")
        _need(resource.is_file() and not resource.is_symlink(),
              "ENGINE_RESOURCE_MISSING", "Original game resource file absent or symlinked")
        _need(1 <= raw.stat().st_size <= MAX_LOG_BYTES,
              "ENGINE_LOG_SIZE_INVALID", "Raw log outside 1..1,000,000-byte limit")
        _need(1 <= resource.stat().st_size <= MAX_RESOURCE_BYTES,
              "ENGINE_RESOURCE_SIZE_INVALID", "Game resource outside safe file-size bound")
        if expected_source_sha256 is not None:
            _need(bool(HEX_SHA.fullmatch(expected_source_sha256)),
                  "ENGINE_SOURCE_HASH_INVALID", "Expected resource SHA-256 is malformed")
        raw_bytes = raw.read_bytes()
        result["raw_log_sha256"] = sha256(raw_bytes).hexdigest()
        hasher = sha256()
        with resource.open("rb") as f:
            for chunk in iter(lambda: f.read(1024 * 1024), b""):
                hasher.update(chunk)
        source_sha = hasher.hexdigest()
        result["resource_sha256"] = source_sha
        if expected_source_sha256 is not None:
            _need(source_sha == expected_source_sha256,
                  "ENGINE_SOURCE_MISMATCH", "Resource hash differs from expected archive fingerprint")
        trace = parse_scummvm_palette_log(
            raw_bytes, engine_commit=engine_commit, game_resource_sha256=source_sha)
        trace["raw_hook_log_sha256"] = result["raw_log_sha256"]
        trace["resource_file_bytes"] = resource.stat().st_size
        encoded = (json.dumps(trace, indent=2) + "\n").encode("utf-8")
        _need(len(encoded) <= 1024 * 1024, "ENGINE_TRACE_SIZE_INVALID",
              "Produced trace exceeds existing verifier's 1 MB limit")
        out.parent.mkdir(parents=True, exist_ok=True)
        with out.open("xb") as f:
            output_created = True
            f.write(encoded)
        _need(out.read_bytes() == encoded, "ENGINE_TRACE_WRITE_MISMATCH",
              "Written trace bytes differ from constructed trace")
        result["trace_sha256"] = sha256(encoded).hexdigest()
        result["samples"] = len(trace["samples"])
        result["clock_observation"] = trace["clock_observation"]
        result["status"] = "success"
    except (EngineTraceError, OSError, ValueError, UnicodeError) as exc:
        diag(getattr(exc, "code", "ENGINE_TRACE_IMPORT_FAILED"),
             f"{type(exc).__name__}: {exc}")
        if output_created and result["trace_sha256"] is None:
            result["status"] = "partial"
    return result
