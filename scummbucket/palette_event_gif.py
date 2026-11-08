"""Make a play-once GIF from *saved* palette event patches, without game archives.

Visual changes are timed at modeled event boundaries, not sampled at an output
FPS. Timing is hypothetical until an actual ScummVM engine trace is verified.
"""
from __future__ import annotations

from hashlib import sha256
import json
from pathlib import Path

from .extraction import _write_new_verified
from .palette_bundle_render import read_palette_event_bundle
from .palette_events import replay_event_palettes
from .palette_gif import (MAX_GIF_EXPANDED_PIXELS, _centiseconds,
                          _pillow_image, encode_gif_verified)
from .palette_sequence import MAX_SEQUENCE_FRAMES, SequenceError


def _need(condition: bool, code: str, message: str) -> None:
    if not condition:
        raise SequenceError(code, message)


def build_event_gif_timeline(bundle: dict) -> dict:
    """Validate all saved patches and retain every distinct *visible* event state.

    Non-consecutive repeat states are not collapsed. Hidden palette changes
    remain in the source timeline; no new engine cycle simulation is performed.
    """
    indices = bundle["indices"]
    initial = bundle["initial_palette"]
    rate = bundle["counter_rate"]
    duration = bundle["duration_seconds"]
    events = bundle["events"]
    width, height = bundle["width"], bundle["height"]

    _need(width > 0 and height > 0 and len(indices) == width * height,
          "EVENT_GIF_DIMENSIONS_INVALID", "Original indexed pixels do not match dimensions")
    _need(len(initial) == 768, "EVENT_GIF_PALETTE_INVALID",
          "Expected original 768-byte palette")
    # Replays and verifies *every* saved event, even if it never affects the image.
    # At 1 fps, this is inexpensive and doesn't determine GIF sampling.
    replay_event_palettes(initial, events, counter_rate=rate,
                          duration_seconds=duration, fps=1)

    visible_indices = sorted(set(indices))
    def signature(pal: bytes) -> bytes:
        return b"".join(pal[3*i:3*i+3] for i in visible_indices)

    last_signature = signature(initial)
    palette = bytearray(initial)
    unique_signatures = {sha256(last_signature).hexdigest()}
    segments = [{
        "index": 0, "start_counter_tick": 0,
        "end_counter_tick_exclusive": duration * rate,
        "source_palette_sha256": sha256(initial).hexdigest(),
        "used_color_values_sha256": sha256(last_signature).hexdigest(),
        "_palette": initial,
    }]
    hidden_events = 0
    for event in events:
        for patch in event["palette_patches"]:
            i = patch["index"]
            palette[3*i:3*i+3] = bytes.fromhex(patch["after_rgb_hex"])
        now = signature(palette)
        if now == last_signature:
            hidden_events += 1
            continue
        tick = event["counter_tick"]
        segments[-1]["end_counter_tick_exclusive"] = tick
        last_signature = now
        fingerprint = sha256(now).hexdigest()
        unique_signatures.add(fingerprint)
        segments.append({
            "index": len(segments), "start_counter_tick": tick,
            "end_counter_tick_exclusive": duration * rate,
            "source_palette_sha256": sha256(palette).hexdigest(),
            "used_color_values_sha256": fingerprint,
            "_palette": bytes(palette),
        })
        _need(len(segments) <= MAX_SEQUENCE_FRAMES and
              len(segments) * width * height <= MAX_GIF_EXPANDED_PIXELS,
              "EVENT_GIF_FRAME_LIMIT",
              "Too many distinct visual event segments for bounded GIF encoding")

    for segment in segments:
        first = segment["start_counter_tick"]
        after = segment["end_counter_tick_exclusive"]
        begin = _centiseconds(first, rate)
        end = _centiseconds(after, rate)
        _need(end > begin, "EVENT_GIF_ZERO_DURATION",
              f"Visual state starting at tick {first} is unrepresentable at GIF 10ms precision")
        segment["start_centiseconds"] = begin
        segment["end_centiseconds"] = end
        segment["duration_ms"] = 10 * (end - begin)
        segment["modeled_time_fraction_seconds"] = {
            "numerator": first, "denominator": rate}

    total_ms = sum(s["duration_ms"] for s in segments)
    _need(total_ms == duration * 1000, "EVENT_GIF_DURATION_MISMATCH",
          "Quantized GIF timeline does not preserve total model duration")
    return {
        "segments": segments,
        "source_event_ticks": len(events),
        "visible_event_boundaries": len(segments) - 1,
        "nonvisual_event_ticks": hidden_events,
        "unique_visual_states": len(unique_signatures),
        "duration_encoded_ms": total_ms,
        "short_delay_warning": any(s["duration_ms"] < 20 for s in segments),
        "quantization_rule": "round absolute event boundaries to GIF 10ms centiseconds",
        "compression_rule": "collapse only consecutive equal RGB values at source-used indices",
    }


def export_palette_event_gif(bundle_dir: str | Path, output_path: str | Path) -> dict:
    """Write non-looping GIF and sidecar manifest, never replacing existing files."""
    src = Path(bundle_dir)
    output = Path(output_path)
    manifest = output.with_suffix(".manifest.json")
    report = {
        "schema_version": "0.1", "operation": "palette_event_bundle_gif",
        "status": "failed", "input_bundle": str(src),
        "output": str(output), "manifest": str(manifest),
        "summary": {}, "segments": [], "files": [], "diagnostics": [],
        "provenance": {},
        "timing": {
            "model": "replay_of_saved_synthetic_palette_events",
            "engine_timer_values_observed": False,
            "real_engine_update_schedule_verified": False,
            "seamless_loop_verified": False, "gif_loops": False,
            "quantization": "10ms centiseconds at absolute event boundaries",
        },
        "fidelity": {
            "rendered_rgb_roundtrip_verified": False,
            "source_indexed_pixels_preserved": True,
            "actors_objects_and_masks_included": False,
            "script_palette_changes_modelled": False,
        },
    }

    def diagnostic(code: str, message: str, severity: str = "error"):
        report["diagnostics"].append({
            "severity": severity, "code": code,
            "message": message, "source": str(src),
        })

    if output.suffix.lower() != ".gif":
        diagnostic("EVENT_GIF_OUTPUT_EXTENSION", "Output must end with .gif")
        return report
    if (output.exists() or output.is_symlink() or
            manifest.exists() or manifest.is_symlink() or
            output.parent.is_symlink()):
        diagnostic("OUTPUT_COLLISION", "Output GIF, manifest or parent symlink already exists")
        return report
    try:
        _pillow_image()  # Fail before writing if the optional dependency is absent.
        bundle = read_palette_event_bundle(src)
        report["diagnostics"].extend(bundle["manifest"].get("diagnostics", []))
        result = build_event_gif_timeline(bundle)
        if result["short_delay_warning"]:
            diagnostic("GIF_SHORT_FRAME_DELAY",
                       "Some GIF states last under 20ms and may be clamped by viewers",
                       severity="warning")
        if len(result["segments"]) == 1:
            diagnostic("GIF_SINGLE_VISUAL_FRAME",
                       "No changes to source-visible pixels during modeled duration",
                       severity="warning")
        payload = encode_gif_verified(
            bundle["indices"], width=bundle["width"],
            height=bundle["height"], segments=result["segments"])
        report["fidelity"]["rendered_rgb_roundtrip_verified"] = True
        report["summary"] = {
            "original_event_ticks": result["source_event_ticks"],
            "visible_event_boundaries": result["visible_event_boundaries"],
            "nonvisual_event_ticks": result["nonvisual_event_ticks"],
            "gif_frames_written": len(result["segments"]),
            "unique_visual_states": result["unique_visual_states"],
            "duration_encoded_ms": result["duration_encoded_ms"],
            "source_counter_rate_assumed": bundle["counter_rate"],
        }
        report["segments"] = [
            {k: v for k, v in seg.items() if k != "_palette"}
            for seg in result["segments"]]
        originals = bundle["manifest"]
        report["provenance"] = {
            "bundle_manifest_sha256": bundle["manifest_sha256"],
            "declared_original_resource_sha256": originals["source"]["resource_sha256"],
            "source_indexed_pixels_sha256": originals["source"]["indexed_pixels_sha256"],
            "source_initial_palette_sha256": originals["source"]["initial_palette_sha256"],
            "native_size": [bundle["width"], bundle["height"]],
            "source_game_archive_reopened": False,
            "rendered_from_saved_patches_only": True,
        }
        if output.exists() or output.is_symlink() or manifest.exists() or manifest.is_symlink():
            raise SequenceError("OUTPUT_COLLISION", "Output appeared during GIF encoding")
        output.parent.mkdir(parents=True, exist_ok=True)
        digest = _write_new_verified(output, payload)
        report["files"].append({
            "filename": output.name, "sha256": digest,
            "bytes": len(payload), "kind": "nonlooping_event_gif_preview",
        })
        report["status"] = "success"
    except (OSError, ValueError, TypeError, KeyError, IndexError,
            MemoryError, OverflowError, SequenceError) as exc:
        diagnostic(getattr(exc, "code", "EVENT_GIF_EXPORT_ERROR"),
                   f"{type(exc).__name__}: {exc}")
        report["status"] = "partial" if report["files"] else "failed"

    if report["files"]:
        try:
            _write_new_verified(
                manifest, (json.dumps(report, indent=2) + "\n").encode("utf-8"))
        except (OSError, ValueError) as exc:
            diagnostic("EVENT_GIF_MANIFEST_WRITE_FAILED", str(exc))
            report["status"] = "partial"
    return report
