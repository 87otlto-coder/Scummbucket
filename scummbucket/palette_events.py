"""Experimental renderer-independent palette-event bundle.

This does NOT decode or claim real engine update timing. The default assumes
one SCUMM-like palette update per counter unit, independent of output FPS.
Events retain ordered cycle rotations, RGB palette patches and exact rational
model times. A separate indexed PNG and raw CLUT make the bundle portable.
"""
from __future__ import annotations

from collections import Counter
from hashlib import sha256
import json
from pathlib import Path

from .extraction import _write_new_verified
from .inspector import XOR_KEY, _read_pair, inspect, InspectionError
from .object_images import ImageDecodeError, MAX_PIXELS
from .palette_probe import (
    PaletteProbeError, advance_palette, decode_room_background_indexed, prepare_cycles,
)
from .palette_sequence import (
    SequenceError, REFERENCE_RESOURCE_SHA256, encode_indexed_png,
)

MAX_COUNTER_RATE = 600
MAX_DURATION_SECONDS = 20
MAX_COUNTER_STEPS = 12000


def _require(ok: bool, code: str, message: str):
    if not ok:
        raise SequenceError(code, message)


def build_counter_event_timeline(
    indices: bytes, initial_palette: bytes, records: list[dict], *,
    width: int, height: int, counter_rate: int = 60,
    duration_seconds: int = 4,
) -> dict:
    """Record *all modeled* rotations at unit-counter boundaries.

    A rotation may cause zero RGB differences (identical colors) or affect
    no source pixels; it is still a legitimate event in this hypothetical
    model and must not be filtered as a non-animation.
    """
    _require(type(width) is int and type(height) is int
             and width > 0 and height > 0 and width * height <= MAX_PIXELS
             and len(indices) == width * height,
             "EVENT_IMAGE_DIMENSIONS_INVALID",
             "Source indexed image does not match the native dimensions")
    _require(len(initial_palette) == 768,
             "EVENT_PALETTE_INVALID", "Expected 768 RGB palette bytes")
    _require(type(counter_rate) is int and 1 <= counter_rate <= MAX_COUNTER_RATE,
             "EVENT_COUNTER_RATE_INVALID", "Counter rate must be integer 1..600")
    _require(type(duration_seconds) is int
             and 1 <= duration_seconds <= MAX_DURATION_SECONDS,
             "EVENT_DURATION_INVALID", "Duration must be integer 1..20 seconds")
    end_tick = duration_seconds * counter_rate
    _require(end_tick <= MAX_COUNTER_STEPS,
             "EVENT_STEPS_LIMIT", "Too many hypothetical engine-like update calls")

    cycles, issues = prepare_cycles(records)
    _require(cycles, "EVENT_NO_CYCLES", "Room has no palette-cycle definitions")
    _require(not any(d["severity"] == "error" for d in issues),
             "EVENT_CYCLES_UNSUPPORTED", "Source cycle records contain blocking errors")

    history = []
    palette = bytearray(initial_palette)
    count = Counter(indices)
    unique_used_indices = set(indices)
    unique_states = {sha256(bytes(palette)).hexdigest()}
    modeled_rotations = 0
    changed_visible_count = 0
    # The modeled time domain is [0, duration_seconds).
    # An event occurring *at* the final boundary is deliberately excluded.
    for tick in range(1, end_tick):
        before = bytes(palette)
        rotations = advance_palette(palette, cycles, delta=1)
        if not rotations:
            continue
        after = bytes(palette)
        patches = [
            {
                "index": i,
                "before_rgb_hex": before[3*i:3*i+3].hex(),
                "after_rgb_hex": after[3*i:3*i+3].hex(),
            }
            for i in range(256)
            if before[3*i:3*i+3] != after[3*i:3*i+3]
        ]
        visible_changed = sum(count[x["index"]] for x in patches)
        previous_digest = sha256(before).hexdigest()
        after_digest = sha256(after).hexdigest()
        history.append({
            "counter_tick": tick,
            "modeled_seconds": {
                "numerator": tick, "denominator": counter_rate,
            },
            "counter_delta": 1,
            "rotations": rotations,
            "palette_before_sha256": previous_digest,
            "palette_after_sha256": after_digest,
            "palette_patches": patches,
            "changed_palette_entries": len(patches),
            "visible_source_pixel_positions_changed": visible_changed,
            "engine_event_observed": False,
        })
        modeled_rotations += len(rotations)
        if visible_changed:
            changed_visible_count += 1
        unique_states.add(after_digest)

    distinct_cycled = {i for c in cycles
                       for i in range(c["start_color"], c["end_color"] + 1)}
    return {
        "schema_version": "0.1",
        "model": "synthetic_one_cycle_update_per_counter_unit",
        "duration_seconds": duration_seconds,
        "counter_rate_assumed": counter_rate,
        "end_counter_tick_exclusive": end_tick,
        "modeled_palette_updates": end_tick - 1,
        "events": history,
        "summary": {
            "event_ticks": len(history),
            "modeled_cycle_rotations": modeled_rotations,
            "event_ticks_with_visible_rgb_changes": changed_visible_count,
            "unique_full_palette_states_at_events": len(unique_states),
            "cycle_definitions": len(cycles),
            "background_pixels_in_cycled_index_ranges": sum(
                count[i] for i in distinct_cycled),
            "background_palette_indices_used": len(unique_used_indices),
        },
        "cycle_definitions": [
            {k: v for k, v in c.items() if k not in ("counter", "rotation_events")}
            for c in cycles
        ],
        "diagnostics": issues,
        "initial_palette_sha256": sha256(initial_palette).hexdigest(),
        "initial_indexed_pixels_sha256": sha256(indices).hexdigest(),
        "engine_timer_values_observed": False,
        "source_fps_dependency": False,
        "seamless_loop_verified": False,
    }


def replay_event_palettes(initial_palette: bytes, events: list[dict], *,
                          counter_rate: int, duration_seconds: int, fps: int) -> list[dict]:
    """Sample event patches at any output rate; verify every state transition.

    Replays the JSON data, without invoking the palette-cycle engine a
    second time. This is a consistency check and future renderer primitive.
    """
    _require(len(initial_palette) == 768, "EVENT_PALETTE_INVALID",
             "Initial palette must contain 768 RGB bytes")
    _require(type(fps) is int and 1 <= fps <= 120,
             "EVENT_SAMPLE_FPS_INVALID", "Replay FPS must be 1..120")
    _require(type(counter_rate) is int and 1 <= counter_rate <= MAX_COUNTER_RATE
             and type(duration_seconds) is int
             and 1 <= duration_seconds <= MAX_DURATION_SECONDS,
             "EVENT_REPLAY_TIMING_INVALID", "Invalid counter rate or duration")
    _require(isinstance(events, list) and len(events) <= MAX_COUNTER_STEPS,
             "EVENT_REPLAY_INVALID", "Event list is not bounded")

    last_tick = 0
    for ev in events:
        tick = ev.get("counter_tick")
        _require(type(tick) is int and last_tick < tick < duration_seconds * counter_rate,
                 "EVENT_SEQUENCE_INVALID", "Event ticks must be strictly increasing in range")
        last_tick = tick

    output = []
    palette = bytearray(initial_palette)
    cursor = 0
    for frame in range(fps * duration_seconds):
        tick = frame * counter_rate // fps
        while cursor < len(events) and events[cursor]["counter_tick"] <= tick:
            event = events[cursor]
            _require(sha256(palette).hexdigest() == event["palette_before_sha256"],
                     "EVENT_BEFORE_HASH_MISMATCH", "Event baseline differs before replay")
            used = set()
            for entry in event["palette_patches"]:
                i = entry["index"]
                _require(type(i) is int and 0 <= i <= 255 and i not in used,
                         "EVENT_PATCH_INDEX_INVALID",
                         "Palette patch index invalid or repeated")
                used.add(i)
                before = palette[3*i:3*i+3]
                try:
                    old = bytes.fromhex(entry["before_rgb_hex"])
                    new = bytes.fromhex(entry["after_rgb_hex"])
                except (ValueError, TypeError) as exc:
                    raise SequenceError("EVENT_PATCH_COLOR_INVALID",
                                        "RGB patch must be 6 hex digits") from exc
                _require(len(old) == 3 and len(new) == 3,
                         "EVENT_PATCH_COLOR_INVALID",
                         "RGB patch must contain exactly 3 bytes")
                _require(before == old, "EVENT_PATCH_BEFORE_MISMATCH",
                         f"Palette color {i} differs from event's prior value")
                palette[3*i:3*i+3] = new
            _require(sha256(palette).hexdigest() == event["palette_after_sha256"],
                     "EVENT_AFTER_HASH_MISMATCH",
                     f"Event at counter {event['counter_tick']} produced incorrect RGB palette")
            cursor += 1
        output.append({
            "frame_index": frame,
            "timestamp_numerator": frame,
            "timestamp_denominator": fps,
            "modeled_counter_tick": tick,
            "palette_sha256": sha256(palette).hexdigest(),
        })
    return output


def export_palette_events(input_path: str | Path, output_dir: str | Path, *,
                          room_id: int, counter_rate: int = 60,
                          duration_seconds: int = 4) -> dict:
    """Export indexed source image, original CLUT and portable event manifest."""
    src, dest = Path(input_path), Path(output_dir)
    result = {
        "schema_version": "0.1", "operation": "palette_counter_events",
        "status": "failed", "input": str(src), "output_dir": str(dest),
        "selection": {
            "room_id": room_id, "counter_rate_assumed": counter_rate,
            "duration_seconds": duration_seconds,
        },
        "files": [], "source": {}, "timeline": None,
        "diagnostics": [], "timing": {
            "model": "one_synthetic_cycle_update_per_counter_unit",
            "counter_units_per_second_assumed": counter_rate,
            "actual_engine_schedule_observed": False,
            "engine_timer_values_observed": False,
            "rendering_fps_independent": True,
            "seamless_loop_verified": False,
        },
        "fidelity": {
            "source_indexed_pixels_preserved": False,
            "initial_source_CLUT_preserved": False,
            "object_costume_mask_compositing_supported": False,
            "script_interference_modelled": False,
        },
    }

    def problem(code, message, *, severity="error"):
        result["diagnostics"].append({
            "code": code, "message": message, "severity": severity,
            "room_id": room_id, "source": str(src),
        })

    if type(room_id) is not int or not 0 <= room_id <= 255:
        problem("ROOM_ID_INVALID", "Room ID must be integer 0..255")
        return result
    if type(counter_rate) is not int or not 1 <= counter_rate <= MAX_COUNTER_RATE:
        problem("EVENT_COUNTER_RATE_INVALID", "Rate must be integer 1..600")
        return result
    if type(duration_seconds) is not int or not 1 <= duration_seconds <= MAX_DURATION_SECONDS:
        problem("EVENT_DURATION_INVALID", "Duration must be integer 1..20 seconds")
        return result
    names = [f"room-{room_id:03d}_indexed.png",
             f"room-{room_id:03d}_initial-clut.rgb", "timeline.json"]
    if dest.is_symlink() or any(
            (dest / n).exists() or (dest / n).is_symlink() for n in names):
        problem("OUTPUT_COLLISION", "Output exists or is symlinked; no overwrite permitted")
        return result

    try:
        inventory = inspect(src)
        result["diagnostics"].extend(inventory["diagnostics"])
        if inventory["status"] != "success":
            raise SequenceError("EVENT_INSPECTION_FAILED", "Source archive inspection failed")
        matches = [r for r in inventory["resources"]["rooms"] if r["id"] == room_id]
        if len(matches) != 1:
            raise SequenceError("EVENT_ROOM_NOT_FOUND",
                                f"Expected one room {room_id}; found {len(matches)}")
        _, stored, _, label = _read_pair(src)
        original_sha = sha256(stored).hexdigest()
        if original_sha != inventory["sources"][1]["sha256"]:
            raise SequenceError("EVENT_SOURCE_CHANGED",
                                "Source archive changed after inspection")
        decoded = bytes(value ^ XOR_KEY for value in stored)
        room = matches[0]
        bg = decode_room_background_indexed(
            decoded, room_offset=room["room_offset"], room_length=room["room_size"])
        timeline = build_counter_event_timeline(
            bg["indexed_pixels"], bg["initial_palette"], room["palette_cycles"],
            width=bg["width"], height=bg["height"],
            counter_rate=counter_rate, duration_seconds=duration_seconds)
        for issue in bg["diagnostics"] + timeline["diagnostics"]:
            problem(issue["code"], issue["message"], severity=issue["severity"])
        if not timeline["events"]:
            problem("EVENT_NO_ROTATIONS",
                    "No modeled palette-cycle rotations within this duration",
                    severity="warning")
        if not timeline["summary"]["event_ticks_with_visible_rgb_changes"]:
            problem("EVENT_NO_VISIBLE_CHANGES",
                    "All modeled changes are invisible on the source indexed bitmap",
                    severity="warning")
        if (original_sha == REFERENCE_RESOURCE_SHA256 and
                room_id == 23 and counter_rate == 60):
            result["timing"]["model"] = (
                "video_calibrated_rate_plus_synthetic_unit_update_schedule")
            result["timing"]["evidence_reference"] = (
                "docs/research/P4_ROOM23_VGA_SPATIAL_VALIDATION.md")
        else:
            result["timing"]["model"] = "user_selected_synthetic_counter_rate_and_schedule"
        result["source"] = {
            "resource_name": label, "resource_sha256": original_sha,
            "room_offset": room["room_offset"],
            "native_size": [bg["width"], bg["height"]],
            "source_offsets": bg["source"],
            "indexed_pixels_sha256": bg["pixel_indices_sha256"],
            "initial_palette_sha256": bg["initial_palette_sha256"],
            "background_zplanes_not_composited": bg["background_zplanes"],
        }
        result["timeline"] = timeline
        # Replay consistency at multiple frame rates is a model check only.
        for fps in (15, 30, 60):
            states = replay_event_palettes(
                bg["initial_palette"], timeline["events"],
                counter_rate=counter_rate, duration_seconds=duration_seconds,
                fps=fps)
            result.setdefault("replay_checks", []).append({
                "sample_fps": fps, "samples": len(states),
                "end_sample_palette_sha256": states[-1]["palette_sha256"],
                "state_patch_hashes_verified": True,
            })
        dest.mkdir(parents=True, exist_ok=True)
        png_bytes = encode_indexed_png(
            bg["width"], bg["height"], bg["indexed_pixels"],
            bg["initial_palette"])
        for name, binary, kind in (
            (names[0], png_bytes, "original_indexed_background"),
            (names[1], bg["initial_palette"], "original_rgb_clut"),
        ):
            checksum = _write_new_verified(dest / name, binary)
            result["files"].append({
                "filename": name, "kind": kind, "sha256": checksum,
                "bytes": len(binary),
            })
            if kind == "original_indexed_background":
                result["fidelity"]["source_indexed_pixels_preserved"] = True
            if kind == "original_rgb_clut":
                result["fidelity"]["initial_source_CLUT_preserved"] = True
        result["status"] = "success"
    except (OSError, ValueError, InspectionError, ImageDecodeError,
            PaletteProbeError, SequenceError) as exc:
        problem(getattr(exc, "code", "EVENT_EXPORT_ERROR"),
                f"{type(exc).__name__}: {exc}")
        result["status"] = "partial" if result["files"] else "failed"
    if result["files"]:
        try:
            _write_new_verified(
                dest / "timeline.json", (json.dumps(result, indent=2) + "\n").encode("utf-8"))
        except (OSError, ValueError) as exc:
            problem("EVENT_MANIFEST_WRITE_FAILED", str(exc))
            result["status"] = "partial"
    return result
