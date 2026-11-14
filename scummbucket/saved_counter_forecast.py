"""Unfitted palette-cycle forecast from directly serialized ScummVM counters.

Uses only an archive-derived CYCL configuration, actual saved counters,
the first engine-observed pre-cycle palette and captured per-frame timers.
Never calibrates phase against post-cycle palettes or resets after a mismatch.
"""
import hashlib

from .palette_probe import advance_palette, prepare_cycles


class SavedCounterForecastError(ValueError):
    pass


def forecast_from_saved_counters(archive_records, saved_cycle_rows,
                                 initial_palette, samples):
    if not isinstance(initial_palette, bytes) or len(initial_palette) != 768:
        raise SavedCounterForecastError("Invalid initial pre-cycle palette")
    cycles, issues = prepare_cycles(archive_records)
    if issues or not cycles:
        raise SavedCounterForecastError(f"Unsupported archive cycles: {issues}")
    known = {row["id"]: row for row in saved_cycle_rows}
    if len(known) != len(saved_cycle_rows) or set(known) != {c["id"] for c in cycles}:
        raise SavedCounterForecastError("Saved cycle IDs differ from archive cycles")
    for cycle in cycles:
        source = known[cycle["id"]]
        if (cycle["delay_counter_units"] != source["delay_counter_units"] or
                cycle["start_color"] != source["start_color"] or
                cycle["end_color"] != source["end_color"] or
                cycle["flags_raw"] != source["flags_raw"]):
            raise SavedCounterForecastError(
                f"Saved cycle {cycle['id']} configuration differs from archive"
            )
        value = source["saved_counter"]
        if type(value) is not int or not 0 <= value <= 65535:
            raise SavedCounterForecastError(f"Invalid saved counter for cycle {cycle['id']}")
        cycle["counter"] = value
    occupied = set()
    for cycle in cycles:
        affected = set(range(cycle["start_color"], cycle["end_color"] + 1))
        if occupied & affected:
            raise SavedCounterForecastError("Overlapping active cycles unsupported")
        occupied.update(affected)
    palette = bytearray(initial_palette)
    rows = []
    cycle_totals = {cycle["id"]: 0 for cycle in cycles}
    noncycle_frames = []
    for n, sample in enumerate(samples, 1):
        pair = sample.get("timer_pair")
        post = sample.get("post_palette")
        if (not isinstance(pair, (list, tuple)) or len(pair) != 2 or
                any(type(x) is not int or not 0 <= x <= 65535 for x in pair)):
            raise SavedCounterForecastError(f"Invalid timer pair at frame {n}")
        if not isinstance(post, bytes) or len(post) != 768:
            raise SavedCounterForecastError(f"Invalid observed post palette at frame {n}")
        events = advance_palette(palette, cycles, delta=max(pair))
        wrong = [index for index in range(256)
                 if palette[index*3:index*3+3] != post[index*3:index*3+3]]
        wrong_set = set(wrong)
        wrong_cycles = [cycle["id"] for cycle in cycles
                        if wrong_set.intersection(range(
                            cycle["start_color"], cycle["end_color"] + 1))]
        for cid in wrong_cycles:
            cycle_totals[cid] += 1
        wrong_outside = sorted(wrong_set - occupied)
        if wrong_outside:
            noncycle_frames.append(n)
        rows.append({
            "frame": n,
            "matches": not wrong,
            "mismatching_color_indices": wrong,
            "mismatching_cycle_ids": wrong_cycles,
            "mismatching_noncycle_color_indices": wrong_outside,
            "predicted_palette_sha256": hashlib.sha256(palette).hexdigest(),
            "observed_palette_sha256": hashlib.sha256(post).hexdigest(),
            "predicted_rotation_events": [event["cycle_id"] for event in events],
        })
    mismatch_frames = [row["frame"] for row in rows if not row["matches"]]
    return {
        "schema": "room7-saved-counter-forecast/1",
        "status": "direct_saved_counter_forecast_matched" if not mismatch_frames
                  else "direct_saved_counter_forecast_mismatch",
        "evidence": {
            "saved_counters": "direct_decoding_of_original_scummvm_save",
            "cycle_definitions": "archive_decoded",
            "initial_palette": "first_engine_observed_pre_cycle_palette",
            "timer_deltas": "engine_observed_per_frame",
            "post_cycle_palettes": "held_out_of_counter_selection",
            "phase_fitting_used": False,
        },
        "frames_checked": len(rows),
        "exact_frame_count": len(rows) - len(mismatch_frames),
        "mismatch_frame_count": len(mismatch_frames),
        "mismatch_frames": mismatch_frames,
        "first_mismatch_frame": mismatch_frames[0] if mismatch_frames else None,
        "noncycle_mismatch_frames": noncycle_frames,
        "mismatch_frames_per_cycle": cycle_totals,
        "saved_cycle_counters": {
            str(row["id"]): row["saved_counter"] for row in saved_cycle_rows
        },
        "frames": rows,
    }
