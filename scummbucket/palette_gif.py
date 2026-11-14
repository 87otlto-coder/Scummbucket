"""Experimental native indexed-background GIF previews for SCUMM v5.

Pillow (optional gif extra) supplies the established GIF/LZW encoder.
Indexed source pixels, modeled palette events and provenance remain in JSON.
GIF is a viewable convenience export, not proof of exact engine timing.
"""
from __future__ import annotations

from collections import Counter
from hashlib import sha256
from io import BytesIO
import json
from pathlib import Path

from .extraction import _write_new_verified
from .inspector import XOR_KEY, _read_pair, inspect, InspectionError
from .object_images import ImageDecodeError, MAX_PIXELS
from .palette_probe import PaletteProbeError, decode_room_background_indexed, prepare_cycles
from .palette_sequence import (
    MAX_SEQUENCE_FRAMES, MAX_OUTPUT_FPS, MAX_COUNTER_RATE,
    REFERENCE_RESOURCE_SHA256, SequenceError, simulate_frame_palettes,
)

# Guard worst-case memory before retaining many full-size Pillow images.
MAX_GIF_EXPANDED_PIXELS = 24_000_000


def _require(valid: bool, code: str, message: str) -> None:
    if not valid:
        raise SequenceError(code, message)


def _centiseconds(frame: int, fps: int) -> int:
    """Round absolute boundaries, preventing accumulated timing drift."""
    return (frame * 200 + fps) // (2 * fps)


def _rgb_pixels(indices: bytes, palette: bytes) -> bytes:
    lookup = [palette[i * 3:i * 3 + 3] for i in range(256)]
    return b"".join(lookup[i] for i in indices)


def build_gif_timeline(
    indices: bytes, initial_palette: bytes, records: list[dict], *,
    width: int, height: int, fps: int, frames: int, counter_rate: int,
) -> dict:
    """Collapse consecutive visually identical samples; retain all rotations.

    Nonadjacent repetitions remain separate. Changed palette entries that
    the background does not use still appear in event records.
    """
    _require(type(width) is int and type(height) is int and
             width > 0 and height > 0 and width * height <= MAX_PIXELS and
             len(indices) == width * height,
             "GIF_DIMENSIONS_INVALID", "Invalid native indexed image geometry")
    _require(len(initial_palette) == 768, "GIF_PALETTE_INVALID",
             "Expected 256 RGB palette entries")
    _require(type(fps) is int and 1 <= fps <= MAX_OUTPUT_FPS,
             "GIF_FPS_INVALID", "FPS must be 1..60")
    _require(type(frames) is int and 1 <= frames <= MAX_SEQUENCE_FRAMES,
             "GIF_FRAME_COUNT_INVALID", "Source frame count must be 1..240")
    _require(type(counter_rate) is int and 1 <= counter_rate <= MAX_COUNTER_RATE,
             "GIF_COUNTER_RATE_INVALID", "Counter rate must be 1..600")
    _require(len(indices) * frames <= MAX_GIF_EXPANDED_PIXELS,
             "GIF_MEMORY_LIMIT", "GIF frame budget exceeds safety limit")

    used = sorted(set(indices))
    histogram = Counter(indices)
    segments = []
    events = []
    unique_states = set()
    previous_signature = None
    for state in simulate_frame_palettes(
        initial_palette, records, fps=fps, frames=frames, counter_rate=counter_rate
    ):
        pal = state["palette"]
        signature = b"".join(pal[3 * i:3 * i + 3] for i in used)
        used_sha = sha256(signature).hexdigest()
        unique_states.add(used_sha)
        for event in state["rotation_events"]:
            a, b = event["start_color"], event["end_color"]
            events.append({
                "sample_frame": state["frame"],
                "time_fraction_seconds": {
                    "numerator": state["frame"], "denominator": fps,
                },
                "counter_total": state["counter_total"],
                "counter_increment": state["counter_delta"],
                "cycle_id": event["cycle_id"], "direction": event["direction"],
                "start_color": a, "end_color": b,
                "affected_indexed_pixel_positions": sum(
                    histogram[i] for i in range(a, b + 1)),
                "palette_sha256_after_sample": state["palette_sha256"],
                "observed_engine_event": False,
            })
        if previous_signature == signature:
            segments[-1]["end_source_frame_exclusive"] = state["frame"] + 1
        else:
            segments.append({
                "index": len(segments),
                "start_source_frame": state["frame"],
                "end_source_frame_exclusive": state["frame"] + 1,
                "start_counter_units": state["counter_total"],
                "source_palette_sha256": state["palette_sha256"],
                "used_color_values_sha256": used_sha,
                "_palette": pal,  # Only transient during GIF encoding.
            })
            previous_signature = signature

    for item in segments:
        first = item["start_source_frame"]
        after = item["end_source_frame_exclusive"]
        start = _centiseconds(first, fps)
        end = _centiseconds(after, fps)
        _require(end > start, "GIF_ZERO_DURATION",
                 "A visual segment has no duration after 10-ms GIF quantization")
        item["start_centiseconds"] = start
        item["end_centiseconds"] = end
        item["duration_ms"] = (end - start) * 10
        item["source_frame_count"] = after - first

    duration_ms = sum(x["duration_ms"] for x in segments)
    _require(duration_ms == 10 * _centiseconds(frames, fps),
             "GIF_DURATION_MISMATCH", "GIF timeline quantization changed total duration")
    return {
        "source_frames": frames,
        "unique_visual_states": len(unique_states),
        "segments": segments,
        "palette_events": events,
        "modeled_rotation_count": len(events),
        "duration_encoded_ms": duration_ms,
        "duration_source_numerator_ms": frames * 1000,
        "duration_source_denominator": fps,
        "short_delay_warning": any(s["duration_ms"] < 20 for s in segments),
        "compression_rule": "collapse only consecutive equal colors at used palette indices",
        "timing_engine_verified": False,
        "seamless_loop_verified": False,
    }


def _pillow_image():
    try:
        from PIL import Image
        return Image
    except ImportError as exc:
        raise SequenceError(
            "GIF_DEPENDENCY_MISSING",
            'Pillow is required. Install in ScummBucket with: python -m pip install -e ".[gif]"'
        ) from exc


def encode_gif_verified(indices: bytes, *, width: int, height: int,
                        segments: list[dict]) -> bytes:
    """Encode with Pillow, then read back all GIF RGB frames and durations."""
    _require(bool(segments), "GIF_NO_SEGMENTS", "No GIF frames to encode")
    _require(len(indices) == width * height and width > 0 and height > 0,
             "GIF_DIMENSIONS_INVALID", "Indexed pixels do not match GIF dimensions")
    _require(width * height * len(segments) <= MAX_GIF_EXPANDED_PIXELS,
             "GIF_MEMORY_LIMIT", "Encoded GIF frame budget too large")
    Image = _pillow_image()
    images = []
    try:
        for segment in segments:
            palette = segment["_palette"]
            _require(len(palette) == 768, "GIF_PALETTE_INVALID",
                     "GIF segment has an invalid RGB palette")
            im = Image.frombytes("P", (width, height), indices)
            im.putpalette(palette)
            images.append(im)
        durations = [seg["duration_ms"] for seg in segments]
        buf = BytesIO()
        # Do NOT specify a loop extension until looping has been proven.
        images[0].save(
            buf, format="GIF", save_all=True, append_images=images[1:],
            duration=durations, disposal=1, optimize=False, interlace=False
        )
        payload = buf.getvalue()
        _require(payload.startswith((b"GIF89a", b"GIF87a")),
                 "GIF_INVALID_HEADER", "Encoder did not return GIF data")
        with Image.open(BytesIO(payload)) as decoded:
            _require(decoded.n_frames == len(segments),
                     "GIF_ROUNDTRIP_FRAMES",
                     f"Encoded {decoded.n_frames}, expected {len(segments)} GIF segments")
            _require("loop" not in decoded.info,
                     "GIF_UNVERIFIED_LOOP", "GIF unexpectedly contains loop extension")
            for idx, seg in enumerate(segments):
                decoded.seek(idx)
                _require(decoded.info.get("duration") == seg["duration_ms"],
                         "GIF_ROUNDTRIP_DURATION",
                         f"GIF segment {idx} did not preserve its duration")
                observed = decoded.convert("RGB").tobytes()
                expected = _rgb_pixels(indices, seg["_palette"])
                _require(observed == expected, "GIF_ROUNDTRIP_PIXELS",
                         f"GIF segment {idx} differs from original indexed-color model")
        return payload
    except SequenceError:
        raise
    except (OSError, ValueError, TypeError, MemoryError) as exc:
        raise SequenceError("GIF_ENCODING_ERROR",
                            f"GIF write/readback error: {type(exc).__name__}: {exc}") from exc
    finally:
        for img in images:
            img.close()


def export_palette_gif(
    input_path: str | Path, output_path: str | Path, *,
    room_id: int, fps: int = 30, duration_seconds: int = 4,
    counter_rate: int = 60,
) -> dict:
    """Write GIF plus adjacent JSON manifest, refusing existing file names."""
    src, gif_path = Path(input_path), Path(output_path)
    manifest_path = gif_path.with_suffix(".manifest.json")
    report = {
        "schema_version": "0.1", "operation": "palette_gif",
        "status": "failed", "input": str(src), "output": str(gif_path),
        "manifest": str(manifest_path),
        "selection": {
            "room_id": room_id, "fps": fps,
            "duration_seconds": duration_seconds,
            "counter_units_per_second": counter_rate,
        },
        "summary": {"source_frames_sampled": 0, "gif_frames_written": 0,
                    "unique_visual_states": 0, "palette_rotation_events": 0,
                    "cycle_definitions": 0, "unique_source_cycle_pixels": 0},
        "source": {}, "cycles": [], "segments": [],
        "palette_events": [], "files": [], "diagnostics": [],
        "timing": {
            "model": "user_selected_counter_rate_hypothesis",
            "counter_units_per_second_assumed": counter_rate,
            "engine_timer_values_observed": False,
            "script_palette_changes_modelled": False,
            "loop_verified": False,
            "gif_loops": False,
            "quantization": "10ms centiseconds, rounded at absolute segment boundaries",
        },
        "fidelity": {
            "native_indexed_background_is_authoritative": True,
            "rendered_rgb_roundtrip_verified": False,
            "actors_objects_and_masks_included": False,
            "full_scene_and_runtime_verified": False,
        },
    }

    def diagnostic(code: str, message: str, severity="error"):
        report["diagnostics"].append({
            "severity": severity, "code": code, "message": message,
            "source": str(src), "room_id": room_id,
        })

    if type(room_id) is not int or not 0 <= room_id <= 255:
        diagnostic("ROOM_ID_INVALID", "Room ID must be integer 0..255")
        return report
    if type(fps) is not int or not 1 <= fps <= MAX_OUTPUT_FPS:
        diagnostic("GIF_FPS_INVALID", "Output FPS must be 1..60")
        return report
    if type(duration_seconds) is not int or not 1 <= duration_seconds <= 20:
        diagnostic("GIF_DURATION_INVALID", "Duration must be integer 1..20 seconds")
        return report
    if type(counter_rate) is not int or not 1 <= counter_rate <= MAX_COUNTER_RATE:
        diagnostic("GIF_COUNTER_RATE_INVALID", "Counter rate must be integer 1..600")
        return report
    frame_count = fps * duration_seconds
    if frame_count > MAX_SEQUENCE_FRAMES:
        diagnostic("GIF_FRAME_LIMIT", "A single export is limited to 240 sampled frames")
        return report
    report["summary"]["source_frames_sampled"] = frame_count
    if gif_path.suffix.lower() != ".gif":
        diagnostic("GIF_OUTPUT_EXTENSION", "Output must end in .gif")
        return report
    if (gif_path.exists() or gif_path.is_symlink() or
            manifest_path.exists() or manifest_path.is_symlink() or
            gif_path.parent.is_symlink()):
        diagnostic("OUTPUT_COLLISION", "GIF/manifest exists or output is symlinked")
        return report

    try:
        _pillow_image()  # Validate optional dependency before any output.
        inventory = inspect(src)
        report["diagnostics"].extend(inventory["diagnostics"])
        if inventory["status"] != "success":
            raise SequenceError("GIF_INSPECTION_FAILED",
                                "Input game archive did not pass inspection")
        matches = [r for r in inventory["resources"]["rooms"]
                   if r["id"] == room_id]
        if len(matches) != 1:
            raise SequenceError("GIF_ROOM_NOT_FOUND",
                                f"Expected unique room {room_id}, found {len(matches)}")
        index_raw, stored, _, label = _read_pair(src)
        if sha256(index_raw).hexdigest() != inventory["sources"][0]["sha256"]:
            raise SequenceError("GIF_SOURCE_CHANGED",
                                "Source index SHA-256 changed since inspection")
        source_hash = sha256(stored).hexdigest()
        if source_hash != inventory["sources"][1]["sha256"]:
            raise SequenceError("GIF_SOURCE_CHANGED",
                                "Source resource SHA-256 changed since inspection")
        decoded = bytes(x ^ XOR_KEY for x in stored)
        room = matches[0]
        bg = decode_room_background_indexed(
            decoded, room_offset=room["room_offset"], room_length=room["room_size"])
        cycles, issues = prepare_cycles(room["palette_cycles"])
        for issue in bg["diagnostics"] + issues:
            diagnostic(issue["code"], issue["message"], severity=issue["severity"])
        if not cycles:
            raise SequenceError("GIF_NO_CYCLES", "Room has no palette cycles")
        if any(x["severity"] == "error" for x in issues):
            raise SequenceError("GIF_UNSUPPORTED_CYCLES",
                                "Source palette cycles contain blocking errors")
        hist = Counter(bg["indexed_pixels"])
        cycled_indices = {i for c in cycles
                          for i in range(c["start_color"], c["end_color"] + 1)}
        report["summary"]["cycle_definitions"] = len(cycles)
        report["summary"]["unique_source_cycle_pixels"] = sum(
            hist[i] for i in cycled_indices)
        if report["summary"]["unique_source_cycle_pixels"] == 0:
            diagnostic("GIF_NO_VISIBLE_CYCLE_PIXELS",
                       "No background indices occur in the room's CYCL ranges",
                       severity="warning")
        if len(cycled_indices) != sum(
            c["end_color"] - c["start_color"] + 1 for c in cycles):
            diagnostic("GIF_OVERLAPPING_CYCLES",
                       "Some source CYCL ranges overlap", severity="warning")
        report["source"] = {
            "resource_name": label, "resource_sha256": source_hash,
            "native_size": [bg["width"], bg["height"]],
            "source_offsets": bg["source"],
            "room_offset": room["room_offset"],
            "indexed_pixels_sha256": bg["pixel_indices_sha256"],
            "initial_palette_sha256": bg["initial_palette_sha256"],
            "room_zplanes_not_composited": bg["background_zplanes"],
        }
        report["cycles"] = [
            {key: value for key, value in c.items()
             if key not in ("counter", "rotation_events")} for c in cycles]
        if (source_hash == REFERENCE_RESOURCE_SHA256 and
                room_id == 23 and counter_rate == 60):
            report["timing"]["model"] = "video_calibrated_60_units_per_second_hypothesis"
            report["timing"]["evidence_reference"] = (
                "docs/research/P4_ROOM23_VGA_SPATIAL_VALIDATION.md")
        timeline = build_gif_timeline(
            bg["indexed_pixels"], bg["initial_palette"], room["palette_cycles"],
            width=bg["width"], height=bg["height"], fps=fps,
            frames=frame_count, counter_rate=counter_rate)
        payload = encode_gif_verified(
            bg["indexed_pixels"], width=bg["width"], height=bg["height"],
            segments=timeline["segments"])
        report["fidelity"]["rendered_rgb_roundtrip_verified"] = True
        report["summary"]["unique_visual_states"] = timeline["unique_visual_states"]
        report["summary"]["gif_frames_written"] = len(timeline["segments"])
        report["summary"]["palette_rotation_events"] = timeline[
            "modeled_rotation_count"]
        report["timing"]["gif_duration_ms"] = timeline["duration_encoded_ms"]
        report["timing"]["source_duration_ms_fraction"] = {
            "numerator": timeline["duration_source_numerator_ms"],
            "denominator": timeline["duration_source_denominator"],
        }
        if timeline["short_delay_warning"]:
            diagnostic("GIF_SHORT_FRAME_DELAY",
                       "GIF segments below 20ms may be clamped by viewers",
                       severity="warning")
        if len(timeline["segments"]) == 1:
            diagnostic("GIF_SINGLE_VISUAL_FRAME",
                       "No change in visible pixels during requested duration",
                       severity="warning")
        if not timeline["modeled_rotation_count"]:
            diagnostic("GIF_NO_ROTATIONS",
                       "No palette rotations occurred in requested duration",
                       severity="warning")
        report["segments"] = [
            {k: v for k, v in seg.items() if k != "_palette"}
            for seg in timeline["segments"]]
        report["palette_events"] = timeline["palette_events"]

        # Do all encoding and readback before creating any output files.
        if gif_path.exists() or manifest_path.exists() or (
                gif_path.is_symlink() or manifest_path.is_symlink()):
            raise SequenceError("OUTPUT_COLLISION", "Output appeared during decoding")
        gif_path.parent.mkdir(parents=True, exist_ok=True)
        digest = _write_new_verified(gif_path, payload)
        report["files"].append({
            "name": gif_path.name, "sha256": digest,
            "byte_count": len(payload), "kind": "nonlooping_gif_preview"})
        report["status"] = "success"
    except (SequenceError, InspectionError, ImageDecodeError, PaletteProbeError,
            OSError, ValueError, MemoryError) as exc:
        diagnostic(getattr(exc, "code", "GIF_EXPORT_ERROR"),
                   f"{type(exc).__name__}: {exc}")
        report["status"] = "partial" if report["files"] else "failed"

    if report["files"]:
        try:
            _write_new_verified(
                manifest_path, (json.dumps(report, indent=2) + "\n").encode("utf-8"))
        except (OSError, ValueError) as exc:
            diagnostic("GIF_MANIFEST_WRITE_FAILED",
                       f"{type(exc).__name__}: {exc}")
            report["status"] = "partial"
    return report
