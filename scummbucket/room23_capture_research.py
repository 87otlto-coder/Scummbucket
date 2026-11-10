"""Forensic, phase-aware comparison of Room 23 source CYCL versus engine palettes.

This does NOT replace the fail-closed raw-log importer or strict CLUT-baseline
verifier. An unfinished log can be studied, but is never treated as complete.
Only palette states at the post-cyclePalette hook are compared; not screen frames.
"""
from __future__ import annotations

import hashlib
from collections import Counter
from pathlib import Path
import re
from statistics import median

from .inspector import XOR_KEY, _read_pair, inspect
from .palette_probe import (advance_palette, decode_room_background_indexed,
                            prepare_cycles)

MAX_LOG_BYTES = 1_000_000
MAX_SAMPLES = 256
PALETTE_RE = re.compile(r"[0-9a-f]{1536}\Z")
NAT_RE = re.compile(r"(?:0|[1-9][0-9]*)\Z")
KNOWN_DOS_VGA_MI2_SHA256 = "ad045372e0d49626503bb50fca29a687ec8e01ef75d9b8bca702a366d143819e"


class ResearchInvalid(Exception):
    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code


def _check(condition: bool, code: str, message: str) -> None:
    if not condition:
        raise ResearchInvalid(code, message)


def _number(text: str, *, label: str, bound: int) -> int:
    _check(bool(NAT_RE.fullmatch(text)), "RESEARCH_INTEGER_INVALID", f"{label}: invalid unsigned decimal integer")
    value = int(text)
    _check(value <= bound, "RESEARCH_INTEGER_INVALID", f"{label}: exceeds {bound}")
    return value


def _palette(text: str, *, label: str) -> bytes:
    _check(bool(PALETTE_RE.fullmatch(text)), "RESEARCH_PALETTE_INVALID",
           f"{label}: require exactly 768 bytes of lowercase RGB hex")
    return bytes.fromhex(text)


def _entries_differ(left: bytes, right: bytes, indices: tuple[int, ...]) -> list[int]:
    return [index for index in indices if left[index * 3:index * 3 + 3] != right[index * 3:index * 3 + 3]]


def parse_room23_hook_log(raw: bytes) -> dict:
    """Strictly validate records but keep completion as a separate property."""
    _check(type(raw) is bytes and 1 <= len(raw) <= MAX_LOG_BYTES,
           "RESEARCH_LOG_SIZE_INVALID", "Log must be a nonempty byte string under 1,000,000 bytes")
    try:
        text = raw.decode("ascii")
    except UnicodeDecodeError as exc:
        raise ResearchInvalid("RESEARCH_LOG_ENCODING_INVALID", "Log must be ASCII") from exc
    _check(text.endswith("\n"), "RESEARCH_LOG_TRUNCATED_LINE",
           "Log ends without a newline; final record may be truncated")
    lines = text.splitlines()
    _check(len(lines) >= 2, "RESEARCH_LOG_INCOMPLETE", "Need BEGIN and at least one SAMPLE")
    header = lines[0].split("|")
    _check(len(header) == 5 and header[:3] == ["SBP4", "BEGIN", "23"],
           "RESEARCH_BEGIN_INVALID", "Expected Room 23 SBP4 BEGIN")
    start_ms = _number(header[3], label="begin_millis", bound=0xFFFFFFFF)
    initial = _palette(header[4], label="BEGIN")
    has_end = lines[-1].startswith("SBP4|END|")
    if has_end:
        end = lines.pop().split("|")
        _check(len(end) == 4 and end[:2] == ["SBP4", "END"] and
               end[3] in ("limit", "room_exit"), "RESEARCH_END_INVALID", "Malformed END record")
        declared = _number(end[2], label="end_count", bound=MAX_SAMPLES)
        _check(declared == len(lines) - 1 and
               (end[3] != "limit" or declared == MAX_SAMPLES),
               "RESEARCH_END_MISMATCH", "END record does not agree with sample count")
        stop_reason = end[3]
    else:
        stop_reason = "missing_end"
    _check(1 <= len(lines) - 1 <= MAX_SAMPLES, "RESEARCH_SAMPLE_COUNT_INVALID",
           "Need 1..256 SAMPLE records")
    samples = []
    previous_ms = start_ms
    for position, line in enumerate(lines[1:], 1):
        fields = line.split("|")
        _check(len(fields) == 7 and fields[:2] == ["SBP4", "SAMPLE"],
               "RESEARCH_SAMPLE_INVALID", f"SAMPLE {position}: malformed fields")
        seq = _number(fields[2], label="sequence", bound=MAX_SAMPLES)
        _check(seq == position, "RESEARCH_SEQUENCE_INVALID", f"Expected sequence {position}, got {seq}")
        timer = _number(fields[3], label="VAR_TIMER", bound=65535)
        next_timer = _number(fields[4], label="VAR_TIMER_NEXT", bound=65535)
        stamp = _number(fields[5], label="sample_millis", bound=0xFFFFFFFF)
        _check(previous_ms <= stamp <= start_ms + 600_000,
               "RESEARCH_CLOCK_INVALID", f"SAMPLE {position}: nonmonotonic or >10-minute clock")
        previous_ms = stamp
        samples.append({"sequence": position, "var_timer": timer,
                        "var_timer_next": next_timer, "millis": stamp,
                        "palette": _palette(fields[6], label=f"SAMPLE {position}")})
    return {"complete": has_end, "stop_reason": stop_reason,
            "begin_millis": start_ms, "initial_palette": initial,
            "samples": samples, "raw_sha256": hashlib.sha256(raw).hexdigest()}


def _split_on_clock_discontinuities(samples: list[dict]) -> tuple[list[list[dict]], list[dict], int]:
    intervals = [b["millis"] - a["millis"] for a, b in zip(samples, samples[1:])]
    nominal = int(median(intervals)) if intervals else 0
    threshold = max(1000, nominal * 5)
    segments = [[]]
    breaks = []
    for index, sample in enumerate(samples):
        if index and sample["millis"] - samples[index - 1]["millis"] > threshold:
            breaks.append({"after_sequence": samples[index - 1]["sequence"],
                           "before_sequence": sample["sequence"],
                           "gap_ms": sample["millis"] - samples[index - 1]["millis"],
                           "interpretation": "clock_discontinuity_only; restart not proven"})
            segments.append([])
        segments[-1].append(sample)
    return segments, breaks, nominal


def _candidate_phases(source: bytes, records: list[dict], segment: list[dict],
                      cycled: tuple[int, ...], search_limit: int,
                      max_prefix: int) -> dict[int, list[int]]:
    """Find model positions using prefix ONLY; never fit to held-out samples."""
    cycles, issues = prepare_cycles(records)
    _check(bool(cycles) and not any(p["severity"] == "error" for p in issues),
           "RESEARCH_CYCLES_UNSUPPORTED", "Missing or invalid source cycle records")
    first_delta = max(segment[0]["var_timer"], segment[0]["var_timer_next"])
    _check(first_delta > 0, "RESEARCH_ZERO_DELTA", "Cannot phase-search with a zero initial delta")
    current = bytearray(source)
    results = {k: [] for k in range(1, max_prefix + 1)}
    for pos in range(1, search_limit + 1):
        advance_palette(current, cycles, delta=first_delta)
        trial = bytearray(current)
        trial_cycles = [cycle.copy() for cycle in cycles]
        for k in range(1, max_prefix + 1):
            if k > 1:
                value = segment[k - 1]
                advance_palette(trial, trial_cycles,
                                delta=max(value["var_timer"], value["var_timer_next"]))
            if _entries_differ(trial, segment[k - 1]["palette"], cycled):
                break
            results[k].append(pos)
    return results


def iter_continuous_palettes(source, cycles, capture, phase):
    """Yield immutable post-callback palettes, preserving counters across clock gaps."""
    rows = capture["samples"]
    palette = bytearray(capture["initial_palette"])
    cycles = [cycle.copy() for cycle in cycles]
    for cycle in cycles:
        span = slice(3 * cycle["start_color"], 3 * (cycle["end_color"] + 1))
        palette[span] = source[span]
    first_delta = max(rows[0]["var_timer"], rows[0]["var_timer_next"])
    for _ in range(phase - 1):
        advance_palette(palette, cycles, delta=first_delta)

    for row in rows:
        delta = max(row["var_timer"], row["var_timer_next"])
        events = advance_palette(palette, cycles, delta=delta)
        yield bytes(palette), events


def _continuous_replay(source: bytes, cycles: list[dict], capture: dict,
                       first_segment: dict, fixed: tuple[int, ...]) -> dict:
    """Freeze the first segment's prefix phase and advance once per recorded call."""
    phase = first_segment.get("first_sample_equivalent_model_update")
    if phase is None:
        return {"status": "phase_unresolved", "heldout_samples": 0}

    rows = capture["samples"]
    prefix = first_segment["calibration_samples"]
    groups = []
    for cycle in cycles:
        groups.append({key: cycle[key] for key in (
            "id", "start_color", "end_color", "rate_raw", "delay_counter_units",
            "direction_from_flag_bit_1")})
    for group in groups:
        group.update(heldout_matches=0, first_mismatch=None)
    predictions = []
    previous = capture["initial_palette"]
    states = iter_continuous_palettes(source, cycles, capture, phase)
    for row, (palette, events) in zip(rows, states):
        if row["sequence"] > prefix:
            observed = row["palette"]
            changed = []
            mismatches = []
            for group in groups:
                span = slice(3 * group["start_color"], 3 * (group["end_color"] + 1))
                if observed[span] != previous[span]:
                    changed.append(group["id"])
                if palette[span] == observed[span]:
                    group["heldout_matches"] += 1
                else:
                    mismatches.append(group["id"])
                    if group["first_mismatch"] is None:
                        group["first_mismatch"] = row["sequence"]
            fixed_diff = _entries_differ(capture["initial_palette"], observed, fixed)
            predictions.append({
                "sequence": row["sequence"], "timer_pair": [row["var_timer"], row["var_timer_next"]],
                "predicted_rotation_ids": [event["cycle_id"] for event in events],
                "observed_changed_ids": changed, "mismatched_cycle_ids": mismatches,
                "noncycling_mismatch_indices": fixed_diff,
            })
        previous = row["palette"]
    matches = sum(not (p["mismatched_cycle_ids"] or p["noncycling_mismatch_indices"])
                  for p in predictions)
    return {
        "method": "First clock segment prefix selects one equivalent phase. Carry counters through clock gaps, one max(timer, timer_next) update per SAMPLE. Noncycling colors use BEGIN.",
        "first_sample_equivalent_model_update": phase, "calibration_samples": prefix,
        "heldout_samples": len(predictions), "heldout_matches": matches,
        "status": ("no_holdout" if not predictions else
                   "matched" if matches == len(predictions) else "mismatch"),
        "cycles": groups, "predictions": predictions,
    }


def compare_room23_palette_capture(source_palette: bytes, records: list[dict],
                                   capture: dict, *, phase_search_limit: int = 500,
                                   min_calibration: int = 3,
                                   max_calibration: int = 24) -> dict:
    """Report phase-selected cycling matches, not complete room fidelity.

    Up to 24 prefix samples may be needed to disambiguate the 60-unit
    stress regime, where cycle parity patterns repeat more frequently.
    Held-out samples are never used to select the equivalent phase.
    """
    _check(len(source_palette) == 768, "RESEARCH_CLUT_INVALID", "Source CLUT must be 768 bytes")
    _check(1 <= phase_search_limit <= 2000, "RESEARCH_PHASE_LIMIT_INVALID", "Phase search must be 1..2000")
    _check(2 <= min_calibration <= max_calibration <= 24,
           "RESEARCH_CALIBRATION_INVALID", "Calibration samples must be 2..24")
    cycles, issues = prepare_cycles(records)
    _check(bool(cycles) and not any(i["severity"] == "error" for i in issues),
           "RESEARCH_CYCLES_UNSUPPORTED", "Invalid cycle definitions")
    cycled = tuple(sorted({i for c in cycles for i in range(c["start_color"], c["end_color"] + 1)}))
    _check(cycled and len(cycled) <= 64, "RESEARCH_CYCLES_UNSUPPORTED", "Cannot analyze empty or >64 cycled entries")
    _check(sum(c["end_color"] - c["start_color"] + 1 for c in cycles) == len(cycled),
           "RESEARCH_CYCLE_OVERLAP", "Overlapping cycles require additional modelling")
    fixed = tuple(i for i in range(256) if i not in set(cycled))
    samples = capture["samples"]
    segments, discontinuities, nominal = _split_on_clock_discontinuities(samples)
    all_out = []
    full_matched = cycle_matched = heldout_matched = 0
    all_calibrated = True
    stable_initial = capture["initial_palette"]
    for chunk in segments:
        cap = min(max_calibration, len(chunk))
        if cap < min_calibration:
            all_calibrated = False
            all_out.append({"from": chunk[0]["sequence"], "to": chunk[-1]["sequence"],
                            "status": "too_short", "sample_count": len(chunk),
                            "matched_cycling": 0, "matched_full_palette": 0,
                            "heldout_matches": 0})
            continue
        possible = _candidate_phases(source_palette, records, chunk, cycled,
                                     phase_search_limit, cap)
        selected_k = next((k for k in range(min_calibration, cap + 1)
                           if len(possible[k]) == 1), None)
        if selected_k is None:
            all_calibrated = False
            all_out.append({"from": chunk[0]["sequence"], "to": chunk[-1]["sequence"],
                            "status": "phase_unresolved",
                            "candidate_count_after_max_calibration": len(possible[cap]),
                            "sample_count": len(chunk), "matched_cycling": 0,
                            "matched_full_palette": 0, "heldout_matches": 0})
            continue
        first_pos = possible[selected_k][0]
        palette = bytearray(source_palette)
        model_cycles, _ = prepare_cycles(records)
        first_delta = max(chunk[0]["var_timer"], chunk[0]["var_timer_next"])
        for _ in range(first_pos):
            advance_palette(palette, model_cycles, delta=first_delta)
        cycled_matches = full_matches = heldout = 0
        first_mismatch = None
        for row_index, item in enumerate(chunk):
            if row_index:
                advance_palette(palette, model_cycles,
                                delta=max(item["var_timer"], item["var_timer_next"]))
            cycling_difference = _entries_differ(palette, item["palette"], cycled)
            stable_difference = _entries_differ(stable_initial, item["palette"], fixed)
            if not cycling_difference:
                cycled_matches += 1
            if not cycling_difference and not stable_difference:
                full_matches += 1
                if row_index >= selected_k:
                    heldout += 1
            if first_mismatch is None and (cycling_difference or stable_difference):
                first_mismatch = {"sequence": item["sequence"],
                                  "cycling_indices": cycling_difference[:16],
                                  "noncycling_indices": stable_difference[:16]}
        cycle_matched += cycled_matches
        full_matched += full_matches
        heldout_matched += heldout
        all_out.append({"from": chunk[0]["sequence"], "to": chunk[-1]["sequence"],
                        "status": "match" if full_matches == len(chunk) else "mismatch",
                        "sample_count": len(chunk), "first_sample_equivalent_model_update": first_pos,
                        "calibration_samples": selected_k,
                        "holdout_samples": len(chunk) - selected_k,
                        "heldout_matches": heldout,
                        "matched_cycling": cycled_matches,
                        "matched_full_palette": full_matches,
                        "first_mismatch": first_mismatch})
    src_begin_diff = _entries_differ(source_palette, stable_initial, tuple(range(256)))
    noncycle_overrides = sorted(set(src_begin_diff) - set(cycled))
    report_status = ("matched" if all_calibrated and full_matched == len(samples)
                     else "mismatch_or_unresolved")
    for pos, boundary in enumerate(discontinuities, 1):
        current_first = segments[pos][0]["palette"]
        previous_last = segments[pos - 1][-1]["palette"]
        boundary["source_cycle_colors_reinitialized_at_first_post_gap_sample"] = (
            not _entries_differ(source_palette, current_first, cycled))
        boundary["changed_cycling_indices_across_gap"] = len(
            _entries_differ(previous_last, current_first, cycled))
    timer_counts = Counter((row["var_timer"], row["var_timer_next"]) for row in samples)
    timer_pairs = [{
        "var_timer": timer, "var_timer_next": timer_next,
        "count": count,
        "first_sequence": next(row["sequence"] for row in samples
                               if (row["var_timer"], row["var_timer_next"]) == (timer, timer_next)),
        "last_sequence": next(row["sequence"] for row in reversed(samples)
                              if (row["var_timer"], row["var_timer_next"]) == (timer, timer_next)),
    } for (timer, timer_next), count in sorted(timer_counts.items())]
    return {
        "continuous_scheduler": _continuous_replay(source_palette, cycles, capture, all_out[0], fixed),
        "timer_pair_distribution": timer_pairs,
        "model_comparison_status": report_status,
        "capture_complete": bool(capture["complete"]),
        "stop_reason": capture["stop_reason"],
        "sample_count": len(samples),
        "samples_matching_cycling": cycle_matched,
        "samples_matching_full_palette_with_observed_noncycle_baseline": full_matched,
        "heldout_samples_matching": heldout_matched,
        "palette_cycle_indices": list(cycled),
        "runtime_noncycle_overrides_vs_source_clut": noncycle_overrides,
        "begin_source_palette_different_indices": src_begin_diff,
        "typical_interval_ms": nominal,
        "clock_discontinuities": discontinuities,
        "segments": all_out,
        "method": "Phase selected only from early calibration samples in each clock-separated segment; subsequent samples held out. Phase denotes source-model equivalence, not observed room-entry callback count.",
        "limitations": [
            "Raw trace has no built-in proof of executing binary identity.",
            "Full-palette comparisons retain noncycled entries from the observed BEGIN state; this does not explain those overrides.",
            "Clock gaps only suggest interruption; a reinitialization trigger is not measured.",
            "Potential scripts and other palette effects are not simulated; comparison is restricted to source-defined palette cycling.",
            "The capture is after cyclePalette, before palManipulate, not a final composited frame.",
        ],
    }


def analyze_room23_capture(input_path: str | Path, raw_path: str | Path, *,
                           phase_search_limit: int = 500) -> dict:
    """Run forensic analysis; never synthesize END or write into source files."""
    source, capture_path = Path(input_path), Path(raw_path)
    report = {"schema_version": "research-room23-phase/0.1",
              "operation": "analyze_room23_capture", "status": "failed",
              "input": str(source), "raw_log": str(capture_path),
              "source_sha256": None, "raw_log_sha256": None,
              "evidence": None, "diagnostics": []}
    try:
        _check(capture_path.is_file() and not capture_path.is_symlink(),
               "RESEARCH_LOG_MISSING", "Raw log not found or is a symlink")
        _check(1 <= capture_path.stat().st_size <= MAX_LOG_BYTES,
               "RESEARCH_LOG_SIZE_INVALID", "Raw log is empty or exceeds 1 MB")
        raw = capture_path.read_bytes()
        parsed = parse_room23_hook_log(raw)
        report["raw_log_sha256"] = parsed["raw_sha256"]
        inventory = inspect(source)
        _check(inventory["status"] == "success", "RESEARCH_ARCHIVE_INVALID",
               "The original game failed inspection")
        matching = [r for r in inventory["resources"]["rooms"] if r["id"] == 23]
        _check(len(matching) == 1, "RESEARCH_ROOM_NOT_FOUND", "Room 23 not uniquely indexed")
        _, stored, _, _ = _read_pair(source)
        resource_sha = hashlib.sha256(stored).hexdigest()
        report["source_sha256"] = resource_sha
        _check(resource_sha == KNOWN_DOS_VGA_MI2_SHA256,
               "RESEARCH_UNVERIFIED_EDITION", "Research comparator is validated only against the pinned original DOS VGA MI2 resource")
        room = matching[0]
        decoded = bytes(v ^ XOR_KEY for v in stored)
        background = decode_room_background_indexed(
            decoded, room_offset=room["room_offset"], room_length=room["room_size"])
        comparison = compare_room23_palette_capture(
            background["initial_palette"], room["palette_cycles"], parsed,
            phase_search_limit=phase_search_limit)
        report["evidence"] = comparison
        report["source_clut_sha256"] = background["initial_palette_sha256"]
        report["runtime_trace_authenticated"] = False
        report["complete_scene_animation_verified"] = False
        report["status"] = (
            "incomplete" if not parsed["complete"]
            else "success" if comparison["model_comparison_status"] == "matched"
            else "failed")
        if not parsed["complete"]:
            report["diagnostics"].append({"severity": "warning", "code": "RESEARCH_MISSING_END",
                                          "message": "All available records were analyzed; raw capture lacks END and remains formally incomplete"})
        if comparison["clock_discontinuities"]:
            report["diagnostics"].append({"severity": "warning", "code": "RESEARCH_CLOCK_DISCONTINUITY",
                                          "message": "Clock gaps segmented for phase analysis; actual reset cause unobserved"})
        if comparison["model_comparison_status"] != "matched":
            report["diagnostics"].append({"severity": "error", "code": "RESEARCH_MODEL_MISMATCH",
                                          "message": "Clock-segment phase search did not resolve or match every observed palette"})
    except Exception as exc:
        # Research input mistakes and unsupported source variants must remain
        # visible as structured diagnostics rather than vanishing silently.
        report["diagnostics"].append({"severity": "error", "code": getattr(exc, "code", "RESEARCH_ANALYSIS_FAILED"),
                                      "message": f"{type(exc).__name__}: {exc}"})
    return report
