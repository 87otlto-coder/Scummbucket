"""P4 experimental palette-driven background PNG sequence exporter.

Preserves the native indexed room bitmap as immutable pixel indices and
changes only PNG PLTE RGB entries. First timing model uses an explicit
counter-units-per-second hypothesis; for the fingerprinted MI2 room 23,
the 60-unit default is calibrated against video, NOT an engine trace.

No proprietary game data or GPL source is embedded in this code.
"""
from __future__ import annotations

from collections import Counter
from hashlib import sha256
import json
from pathlib import Path
import struct
import zlib

from .extraction import _write_new_verified
from .inspector import XOR_KEY, _read_pair, inspect, InspectionError
from .object_images import ImageDecodeError, MAX_PIXELS, _png_chunk
from .palette_probe import (
    PaletteProbeError, advance_palette, decode_room_background_indexed,
    prepare_cycles,
)

MAX_SEQUENCE_FRAMES = 240
MIN_OUTPUT_FPS, MAX_OUTPUT_FPS = 1, 60
MAX_COUNTER_RATE = 600
REFERENCE_RESOURCE_SHA256 = (
    "ad045372e0d49626503bb50fca29a687ec8e01ef75d9b8bca702a366d143819e"
)


class SequenceError(Exception):
    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code


def _require(condition: bool, code: str, message: str):
    if not condition:
        raise SequenceError(code, message)


def encode_indexed_png(width: int, height: int, indices: bytes,
                       palette: bytes) -> bytes:
    """Deterministic lossless PNG color type 3: same indices, variable PLTE.

    The PNG has no tRNS chunk: room backgrounds are treated as opaque here.
    Alpha masks and scene composites must be reconstructed separately.
    """
    _require(type(width) is int and type(height) is int and
             0 < width * height <= MAX_PIXELS,
             "SEQUENCE_DIMENSIONS_INVALID", "Invalid native image dimensions")
    _require(len(indices) == width * height,
             "SEQUENCE_INDEX_COUNT_INVALID",
             "Indexed background length does not match dimensions")
    _require(len(palette) == 256 * 3,
             "SEQUENCE_PALETTE_INVALID",
             "Expected exactly 256 entries of 8-bit RGB")
    scanlines = b"".join(
        b"\x00" + indices[y * width:(y + 1) * width]
        for y in range(height))
    return (
        b"\x89PNG\r\n\x1a\n"
        + _png_chunk(b"IHDR", struct.pack(">IIBBBBB", width, height, 8, 3, 0, 0, 0))
        + _png_chunk(b"PLTE", palette)
        + _png_chunk(b"IDAT", zlib.compress(scanlines, level=9))
        + _png_chunk(b"IEND", b"")
    )


def simulate_frame_palettes(initial_palette: bytes, records: list[dict], *,
                            fps: int, frames: int, counter_rate: int):
    """Yield one state per *exported* frame; one model call per output frame.

    Each frame is sampled at i/fps seconds with a cumulative synthetic counter
    floor(i*counter_rate/fps). The per-frame increment is the difference in
    consecutive cumulative counters. This does not model intermediate engine
    callbacks or pauses; export FPS is not asserted to be game update FPS.

    Generator keeps only the current palette and cycle counters in memory.
    """
    _require(type(fps) is int and MIN_OUTPUT_FPS <= fps <= MAX_OUTPUT_FPS,
             "SEQUENCE_FPS_INVALID", f"FPS must be {MIN_OUTPUT_FPS}..{MAX_OUTPUT_FPS}")
    _require(type(frames) is int and 1 <= frames <= MAX_SEQUENCE_FRAMES,
             "SEQUENCE_FRAME_COUNT_INVALID",
             f"Frame count must be 1..{MAX_SEQUENCE_FRAMES}")
    _require(type(counter_rate) is int and 1 <= counter_rate <= MAX_COUNTER_RATE,
             "SEQUENCE_COUNTER_RATE_INVALID",
             f"Counter rate must be 1..{MAX_COUNTER_RATE}")
    _require(len(initial_palette) == 768, "SEQUENCE_PALETTE_INVALID",
             "Expected the initial 256-color RGB palette")
    cycles, warnings = prepare_cycles(records)
    _require(bool(cycles), "SEQUENCE_NO_CYCLES",
             "Selected room has no CYCL palette definitions")
    _require(not any(issue["severity"] == "error" for issue in warnings),
             "SEQUENCE_CYCLE_INVALID",
             "Source contains a palette cycle that cannot be modeled")
    palette = bytearray(initial_palette)
    previous = 0
    for frame_no in range(frames):
        counter_total = frame_no * counter_rate // fps
        increment = counter_total - previous
        _require(0 <= increment <= 65535, "SEQUENCE_DELTA_INVALID",
                 "Calculated palette counter delta out of range")
        # Update exactly once for each output frame after the initial frame.
        events = (advance_palette(palette, cycles, delta=increment)
                  if frame_no else [])
        previous = counter_total
        yield {
            "frame": frame_no, "counter_total": counter_total,
            "counter_delta": increment,
            "timestamp_numerator": frame_no, "timestamp_denominator": fps,
            "palette": bytes(palette),
            "palette_sha256": sha256(palette).hexdigest(),
            "rotation_events": events,
            "rotation_events_total": sum(c["rotation_events"] for c in cycles),
        }


def export_palette_sequence(input_path: str | Path, output_dir: str | Path, *,
                            room_id: int, fps: int = 30,
                            duration_seconds: int = 4,
                            counter_rate: int = 60) -> dict:
    """Export native indexed PNG sequence + original palette, manifest and warnings.

    No files are overwritten. An operation may be partial if a write fails
    midway; all such failures are visible in the result and CLI exit code.
    """
    src, dest = Path(input_path), Path(output_dir)
    result = {
        "schema_version": "0.1",
        "operation": "palette_animation_sequence",
        "status": "failed",
        "input": str(src), "output_dir": str(dest),
        "selection": {
            "room_id": room_id, "fps": fps,
            "duration_seconds": duration_seconds,
            "counter_units_per_second": counter_rate,
        },
        "summary": {"frames_requested": 0, "frames_written": 0,
                    "cycle_records": 0, "unique_cycled_source_pixels": 0},
        "files": [], "frames": [], "cycles": [],
        "diagnostics": [],
        "provenance": {},
        "timing": {
            "model": "video_calibrated_hypothesis_for_original_MI2_room23_only",
            "assumed_counter_units_per_second": counter_rate,
            "output_fps": fps,
            "engine_timer_values_observed": False,
            "actual_runtime_update_calls_observed": False,
            "model_calls": "one cyclePalette-like call per output frame after frame zero",
            "frame_timestamps": "exact frame_index / output_fps (seconds)",
            "seamless_loop_verified": False,
        },
        "fidelity": {
            "original_palette_indices_preserved": True,
            "dynamic_PLTE_per_frame": True,
            "room_objects_and_actors_included": False,
            "depth_mask_compositing_implemented": False,
            "script_palette_modifications_modelled": False,
            "reference_render_pixel_verified": False,
            "comprehensive_background_animation": False,
        },
    }

    def diagnostic(code, message, *, severity="error", offset=None):
        result["diagnostics"].append({
            "code": code, "severity": severity,
            "message": message, "source": str(src), "offset": offset,
            "resource_id": room_id,
        })

    if type(room_id) is not int or not 0 <= room_id <= 255:
        diagnostic("ROOM_ID_INVALID", "Room ID must be 0..255")
        return result
    if (type(fps) is not int or not MIN_OUTPUT_FPS <= fps <= MAX_OUTPUT_FPS):
        diagnostic("SEQUENCE_FPS_INVALID", "Output FPS must be an integer 1..60")
        return result
    if type(duration_seconds) is not int or not 1 <= duration_seconds <= 20:
        diagnostic("SEQUENCE_DURATION_INVALID",
                   "Duration must be an integer 1..20 seconds")
        return result
    if type(counter_rate) is not int or not 1 <= counter_rate <= MAX_COUNTER_RATE:
        diagnostic("SEQUENCE_COUNTER_RATE_INVALID",
                   f"Counter units per second must be 1..{MAX_COUNTER_RATE}")
        return result
    num_frames = fps * duration_seconds
    if num_frames > MAX_SEQUENCE_FRAMES:
        diagnostic("SEQUENCE_FRAME_LIMIT",
                   f"Requested {num_frames} PNGs exceeds {MAX_SEQUENCE_FRAMES}; "
                   "reduce duration or FPS")
        return result
    result["summary"]["frames_requested"] = num_frames
    if dest.is_symlink() or (dest / "manifest.json").exists() or (
            dest / "manifest.json").is_symlink():
        diagnostic("OUTPUT_COLLISION",
                   "Output directory is a symlink or a manifest already exists")
        return result

    try:
        inventory = inspect(src)
        result["diagnostics"].extend(inventory["diagnostics"])
        if inventory["status"] != "success":
            diagnostic("SEQUENCE_INSPECTION_FAILED",
                       "Original game archive failed inspection")
            return result
        target = [room for room in inventory["resources"]["rooms"]
                  if room["id"] == room_id]
        if len(target) != 1:
            diagnostic("SEQUENCE_ROOM_NOT_FOUND",
                       f"Expected one room {room_id}, found {len(target)}")
            return result
        index_raw, raw, _, label = _read_pair(src)
        if sha256(index_raw).hexdigest() != inventory["sources"][0]["sha256"]:
            raise SequenceError("SEQUENCE_SOURCE_CHANGED",
                                "Original index SHA-256 changed since inspection")
        raw_sha = sha256(raw).hexdigest()
        if raw_sha != inventory["sources"][1]["sha256"]:
            raise SequenceError("SEQUENCE_SOURCE_CHANGED",
                                "Original resource SHA-256 changed since inspection")
        decoded = bytes(byte ^ XOR_KEY for byte in raw)
        room = target[0]
        bg = decode_room_background_indexed(
            decoded, room_offset=room["room_offset"], room_length=room["room_size"])
        cycles, issues = prepare_cycles(room["palette_cycles"])
        for item in bg["diagnostics"] + issues:
            diagnostic(item["code"], item["message"],
                       severity=item["severity"], offset=item.get("offset"))
        if not cycles:
            raise SequenceError("SEQUENCE_NO_CYCLES",
                                "Room has no palette cycles; no animation sequence exported")
        if any(item["severity"] == "error" for item in issues):
            raise SequenceError("SEQUENCE_CYCLE_INVALID",
                                "One or more source cycles could not be interpreted")
        index_hist = Counter(bg["indexed_pixels"])
        unique_indices = {
            idx for c in cycles
            for idx in range(c["start_color"], c["end_color"] + 1)
        }
        affected = sum(index_hist[i] for i in unique_indices)
        result["summary"]["cycle_records"] = len(cycles)
        result["summary"]["unique_cycled_source_pixels"] = affected
        if affected == 0:
            diagnostic("SEQUENCE_NO_VISIBLE_CYCLE_PIXELS",
                       "Original room background does not contain palette indices "
                       "addressed by room CYCL definitions; a static-looking "
                       "sequence may result", severity="warning")
        if len(unique_indices) != sum(
                c["end_color"] - c["start_color"] + 1 for c in cycles):
            diagnostic("SEQUENCE_OVERLAPPING_CYCLE_RANGES",
                       "Multiple cycles address the same color indices; update order "
                       "could affect their interaction", severity="warning")
        original_fingerprint = raw_sha == REFERENCE_RESOURCE_SHA256
        if original_fingerprint and room_id == 23 and counter_rate == 60:
            timing_label = "video_calibrated_60_units_per_second_hypothesis"
        else:
            timing_label = "user_selected_or_cross_room_counter_rate_hypothesis"
        result["timing"]["model"] = timing_label
        result["provenance"] = {
            "resource_name": label,
            "resource_sha256": raw_sha,
            "native_size": [bg["width"], bg["height"]],
            "room_offset": room["room_offset"],
            "source_offsets": bg["source"],
            "indexed_pixels_sha256": bg["pixel_indices_sha256"],
            "initial_palette_sha256": bg["initial_palette_sha256"],
            "reference_2026_11_08_room23_video_study": (
                "docs/research/P4_ROOM23_VGA_SPATIAL_VALIDATION.md"
                if original_fingerprint and room_id == 23 else None
            ),
            "background_zplanes_present_but_not_composited":
                bg["background_zplanes"],
        }
        # Definitions/provenance should not be mistaken for live engine state.
        result["cycles"] = [{
            key: value for key, value in cycle.items()
            if key not in ("counter", "rotation_events")
        } for cycle in cycles]
        # Preflight all planned names to avoid preventable partial outputs.
        original_name = f"room-{room_id:03d}_source-indexed.png"
        palette_name = f"room-{room_id:03d}_initial-clut.rgb"
        names = [original_name, palette_name, "manifest.json"]
        names.extend(f"room-{room_id:03d}_frame-{i:04d}.png"
                     for i in range(num_frames))
        colliding = [name for name in names
                     if (dest / name).exists() or (dest / name).is_symlink()]
        if colliding:
            raise SequenceError("OUTPUT_COLLISION",
                                f"Refusing to overwrite existing outputs: {colliding[:4]}")
        dest.mkdir(parents=True, exist_ok=True)
        source_png = encode_indexed_png(
            bg["width"], bg["height"],
            bg["indexed_pixels"], bg["initial_palette"])
        for filename, payload, kind in (
            (original_name, source_png, "original_indexed_background"),
            (palette_name, bg["initial_palette"], "original_rgb_clut"),
        ):
            checksum = _write_new_verified(dest / filename, payload)
            result["files"].append({
                "name": filename, "kind": kind, "sha256": checksum,
                "byte_count": len(payload),
            })
        for frame in simulate_frame_palettes(
                bg["initial_palette"], room["palette_cycles"],
                fps=fps, frames=num_frames, counter_rate=counter_rate):
            filename = f"room-{room_id:03d}_frame-{frame['frame']:04d}.png"
            png = encode_indexed_png(
                bg["width"], bg["height"],
                bg["indexed_pixels"], frame["palette"])
            checksum = _write_new_verified(dest / filename, png)
            result["files"].append({
                "name": filename, "kind": "indexed_palette_frame",
                "sha256": checksum, "byte_count": len(png),
            })
            result["frames"].append({
                "frame_index": frame["frame"],
                "filename": filename,
                "timestamp_numerator": frame["timestamp_numerator"],
                "timestamp_denominator": frame["timestamp_denominator"],
                "cumulative_counter_units": frame["counter_total"],
                "counter_increment": frame["counter_delta"],
                "frame_sha256": checksum,
                "palette_sha256": frame["palette_sha256"],
                "rotations_this_frame": frame["rotation_events"],
                "total_rotations": frame["rotation_events_total"],
            })
            result["summary"]["frames_written"] += 1
        if all(not frame["rotations_this_frame"] for frame in result["frames"]):
            diagnostic(
                "SEQUENCE_NO_ROTATIONS_IN_DURATION",
                "No palette-cycle rotation occurred during the requested interval; "
                "increase duration or inspect rate and timing assumptions",
                severity="warning")
        if all(frame["palette_sha256"] ==
               bg["initial_palette_sha256"] for frame in result["frames"]):
            diagnostic(
                "SEQUENCE_NO_PALETTE_DIFFERENCE",
                "All exported palettes match the initial palette; "
                "do not interpret the resulting static sequence as active animation",
                severity="warning")
        result["status"] = "success"
    except (OSError, ValueError, InspectionError, ImageDecodeError,
            PaletteProbeError, SequenceError) as exc:
        diagnostic(getattr(exc, "code", "SEQUENCE_EXPORT_ERROR"),
                   f"{type(exc).__name__}: {exc}")
        result["status"] = "partial" if result["files"] else "failed"
    if result["files"]:
        try:
            _write_new_verified(
                dest / "manifest.json",
                (json.dumps(result, indent=2) + "\n").encode("utf-8"))
        except OSError as exc:
            diagnostic("SEQUENCE_MANIFEST_WRITE_FAILED",
                       f"{type(exc).__name__}: {exc}")
            result["status"] = "partial"
    return result
