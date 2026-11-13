"""Phase-aware, held-out palette-cycle research for SCUMM v5 captures.

Archive-defined CYCL records and the first engine-observed pre-cycle palette
are used. Initial counter phases are fitted ONLY to the observed calibration
prefix; engine-observed timer pairs are inputs. The later frames are held out.
This does not reproduce full game state or infer actual saved counter bytes.
"""
from __future__ import annotations

from .palette_probe import advance_palette, prepare_cycles


class PhaseResearchError(ValueError):
    pass


def _require(condition, message):
    if not condition:
        raise PhaseResearchError(message)


def analyze_saved_palette_cycles(records, initial_palette, samples, *,
                                 calibration_frames=24):
    """Analyze samples: timer_pair=[a,b], post_palette=768-byte bytes."""
    _require(len(initial_palette) == 768, "Initial palette requires 768 bytes")
    _require(type(calibration_frames) is int and 1 <= calibration_frames < len(samples),
             "Calibration must leave at least one held-out frame")
    cycles, issues = prepare_cycles(records)
    _require(not issues and bool(cycles),
             f"Unsupported or absent palette cycle definitions: {issues}")
    occupied = set()
    for cycle in cycles:
        start, end = cycle["start_color"], cycle["end_color"]
        _require(end > start, f"Cycle {cycle['id']} does not rotate colors")
        colors = set(range(start, end + 1))
        _require(not occupied.intersection(colors),
                 "Overlapping cycles cannot be calibrated independently")
        occupied.update(colors)
    deltas, posts = [], []
    for index, sample in enumerate(samples, 1):
        pair = sample.get("timer_pair")
        palette = sample.get("post_palette")
        _require(isinstance(pair, (tuple, list)) and len(pair) == 2 and
                 all(type(t) is int and 0 <= t <= 65535 for t in pair),
                 f"Invalid timer pair in sample {index}")
        _require(isinstance(palette, bytes) and len(palette) == 768,
                 f"Invalid post-palette in sample {index}")
        deltas.append(max(pair))
        posts.append(palette)
    suffix = len(samples) - calibration_frames
    per_cycle, projections = [], []
    for cycle in cycles:
        delay = cycle["delay_counter_units"]
        _require(0 < delay <= 4096, f"Unsupported cycle delay {delay}")
        start, end = cycle["start_color"] * 3, (cycle["end_color"] + 1) * 3
        possibilities = []
        for phase in range(delay):
            candidate = dict(cycle, counter=phase, rotation_events=0)
            predicted = bytearray(initial_palette)
            predicted_suffix = []
            calibrates = True
            for index, delta in enumerate(deltas):
                advance_palette(predicted, [candidate], delta=delta)
                if index < calibration_frames:
                    if predicted[start:end] != posts[index][start:end]:
                        calibrates = False
                        break
                else:
                    predicted_suffix.append(bytes(predicted[start:end]))
            if calibrates:
                possibilities.append((phase, predicted_suffix))
        phases = [phase for phase, _ in possibilities]
        predicted_groups = []
        for offset in range(suffix):
            distinct = {seq[offset] for _, seq in possibilities}
            predicted_groups.append(next(iter(distinct)) if len(distinct) == 1 else None)
        projections.append((start, end, predicted_groups))
        mismatches = [calibration_frames + j + 1
                      for j, prediction in enumerate(predicted_groups)
                      if prediction is not None and
                      prediction != posts[calibration_frames+j][start:end]]
        per_cycle.append({
            "id": cycle["id"], "start_color": cycle["start_color"],
            "end_color": cycle["end_color"],
            "delay_counter_units": delay,
            "calibration_matching_phases": phases,
            "phase_uniquely_identified": len(phases) == 1,
            "heldout_determinate_frames": sum(p is not None for p in predicted_groups),
            "heldout_ambiguous_frames": sum(p is None for p in predicted_groups),
            "heldout_mismatching_frames": len(mismatches),
            "heldout_first_mismatch_frame": mismatches[0] if mismatches else None,
        })
    outside = [i for i in range(256) if i not in occupied]
    noncycle_changes, full_mismatches, ambiguous_frames = [], [], []
    full_matches = 0
    for offset in range(suffix):
        index = calibration_frames + offset
        observed = posts[index]
        untouched = [i for i in outside if
                     initial_palette[3*i:3*i+3] != observed[3*i:3*i+3]]
        if untouched:
            noncycle_changes.append({"frame": index+1, "palette_indices": untouched})
        estimated = bytearray(initial_palette)
        ambiguous = False
        for start, end, values in projections:
            value = values[offset]
            if value is None:
                ambiguous = True
            else:
                estimated[start:end] = value
        if ambiguous:
            ambiguous_frames.append(index+1)
        elif estimated == observed:
            full_matches += 1
        else:
            wrong = [i for i in range(256) if
                     estimated[3*i:3*i+3] != observed[3*i:3*i+3]]
            full_mismatches.append({"frame": index+1, "palette_indices": wrong})
    no_phases = [c["id"] for c in per_cycle
                 if not c["calibration_matching_phases"]]
    cycle_mismatches = sum(c["heldout_mismatching_frames"] for c in per_cycle)
    status = ("calibration_unresolved" if no_phases else
              "heldout_mismatch" if cycle_mismatches or full_mismatches else
              "forecast_ambiguous" if ambiguous_frames else
              "heldout_matched")
    return {
        "schema": "room7-palette-phase-research/1",
        "evidence": {
            "cycle_config": "archive_decoded",
            "initial_palette": "first_engine_observed_pre_cycle_palette",
            "timer_deltas": "engine_observed_per_frame",
            "counter_phases": "inferred_only_from_calibration_prefix",
            "heldout_palettes": "engine_observed_not_used_in_fitting",
        },
        "status": status,
        "calibration_frames": calibration_frames,
        "heldout_frames": suffix,
        "phase_uniquely_identified_count": sum(
            c["phase_uniquely_identified"] for c in per_cycle),
        "cycles_without_calibration_solution": no_phases,
        "per_cycle": per_cycle,
        "heldout_full_palette_matches": full_matches,
        "heldout_full_palette_mismatch_frames": full_mismatches,
        "heldout_noncycle_changed_frames": noncycle_changes,
        "heldout_ambiguous_frames": ambiguous_frames,
        "heldout_cycle_mismatch_total": cycle_mismatches,
    }
