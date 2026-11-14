"""Render native indexed PNG frames solely from a validated palette-events bundle.

No original game archive, Pillow, SCUMM cycle simulation, or external encoder
is required. This replays *saved* palette patches, verifies every original
sidecar fingerprint, and retains the original timeline's uncertain timing.
"""
from __future__ import annotations

from hashlib import sha256
import json
from pathlib import Path
import re
import struct
import zlib

from .extraction import _write_new_verified
from .object_images import MAX_PIXELS
from .palette_events import replay_event_palettes
from .palette_sequence import SequenceError, encode_indexed_png, MAX_SEQUENCE_FRAMES

MAX_BUNDLE_JSON_BYTES = 2_000_000
MAX_COMPRESSED_PNG_BYTES = 12_000_000
MAX_RENDER_PIXELS = 24_000_000
PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"
HEX_SHA256 = re.compile(r"^[0-9a-f]{64}$")


def _need(ok: bool, code: str, message: str):
    if not ok:
        raise SequenceError(code, message)


def read_bundle_indexed_png(data: bytes) -> tuple[int, int, bytes, bytes]:
    """Strictly parse the PNG subset written by encode_indexed_png.

    Requires 8-bit indexed, no interlace, exactly 256 PLTE colors, and
    unfiltered scanlines. Rejects inflated bombs and malformed chunk CRCs.
    It is intentionally *not* a generic PNG reader.
    """
    _need(data.startswith(PNG_SIGNATURE), "EVENT_PNG_SIGNATURE_INVALID",
          "Source image is not a PNG")
    offset = len(PNG_SIGNATURE)
    chunks: dict[bytes, bytes] = {}
    sequence = []
    while offset < len(data):
        _need(offset + 12 <= len(data), "EVENT_PNG_CHUNK_TRUNCATED",
              "PNG chunk header or CRC truncated")
        length = struct.unpack_from(">I", data, offset)[0]
        tag = data[offset + 4:offset + 8]
        _need(length <= MAX_COMPRESSED_PNG_BYTES and offset + 12 + length <= len(data),
              "EVENT_PNG_CHUNK_INVALID", "PNG chunk exceeds input or bounded size")
        payload = data[offset + 8:offset + 8 + length]
        stored_crc = struct.unpack_from(">I", data, offset + 8 + length)[0]
        _need((zlib.crc32(tag + payload) & 0xFFFFFFFF) == stored_crc,
              "EVENT_PNG_CRC_INVALID", f"PNG chunk {tag!r} CRC differs")
        _need(tag not in chunks and tag in (b"IHDR", b"PLTE", b"IDAT", b"IEND"),
              "EVENT_PNG_CHUNK_UNSUPPORTED",
              f"Unexpected or repeated PNG chunk {tag!r}")
        chunks[tag] = payload
        sequence.append(tag)
        offset += 12 + length
        if tag == b"IEND":
            break
    _need(sequence == [b"IHDR", b"PLTE", b"IDAT", b"IEND"]
          and offset == len(data), "EVENT_PNG_STRUCTURE_INVALID",
          "Expected exactly IHDR, PLTE, IDAT, IEND with no trailing bytes")
    _need(len(chunks[b"IHDR"]) == 13 and not chunks[b"IEND"],
          "EVENT_PNG_HEADER_INVALID", "Malformed PNG metadata")
    width, height, depth, color_type, compression, filtering, interlace = (
        struct.unpack(">IIBBBBB", chunks[b"IHDR"]))
    _need(0 < width * height <= MAX_PIXELS and width > 0 and height > 0
          and (depth, color_type, compression, filtering, interlace) == (8, 3, 0, 0, 0),
          "EVENT_PNG_FORMAT_UNSUPPORTED",
          "Only native 8-bit indexed, noninterlaced PNG from ScummBucket is supported")
    palette = chunks[b"PLTE"]
    _need(len(palette) == 768, "EVENT_PNG_PLTE_INVALID",
          "Original PNG must contain 256 RGB colors")
    expected_bytes = height * (width + 1)
    try:
        inflater = zlib.decompressobj()
        decoded = inflater.decompress(chunks[b"IDAT"], expected_bytes + 1)
        _need(len(decoded) == expected_bytes and inflater.eof
              and not inflater.unconsumed_tail and not inflater.unused_data,
              "EVENT_PNG_INFLATE_INVALID",
              "PNG IDAT is truncated, contains trailing data or expands excessively")
    except zlib.error as exc:
        raise SequenceError("EVENT_PNG_INFLATE_INVALID",
                            f"PNG decompression failed: {exc}") from exc
    indices = bytearray(width * height)
    for y in range(height):
        start = y * (width + 1)
        _need(decoded[start] == 0, "EVENT_PNG_FILTER_UNSUPPORTED",
              "Bundle PNG must use row filter type 0")
        indices[y*width:(y+1)*width] = decoded[start+1:start+1+width]
    return width, height, bytes(indices), palette


def read_palette_event_bundle(bundle_dir: str | Path) -> dict:
    """Validate original sidecar bytes against their event manifest.

    This verifies the *bundle*, not the absent original proprietary archive.
    """
    directory = Path(bundle_dir)
    _need(directory.is_dir() and not directory.is_symlink(),
          "EVENT_BUNDLE_DIRECTORY_INVALID", "Bundle directory is absent or symlinked")
    manifest_file = directory / "timeline.json"
    _need(manifest_file.is_file() and not manifest_file.is_symlink(),
          "EVENT_BUNDLE_MANIFEST_MISSING", "Expected timeline.json in bundle folder")
    _need(manifest_file.stat().st_size <= MAX_BUNDLE_JSON_BYTES,
          "EVENT_BUNDLE_MANIFEST_TOO_LARGE", "Timeline JSON exceeds safe size limit")
    raw_manifest = manifest_file.read_bytes()
    try:
        manifest = json.loads(raw_manifest)
    except (ValueError, UnicodeError) as exc:
        raise SequenceError("EVENT_BUNDLE_JSON_INVALID", "Invalid timeline JSON") from exc
    _need(isinstance(manifest, dict) and manifest.get("schema_version") == "0.1"
          and manifest.get("operation") == "palette_counter_events"
          and manifest.get("status") == "success",
          "EVENT_BUNDLE_SCHEMA_UNSUPPORTED",
          "Expected a successful palette_counter_events schema v0.1 manifest")
    selection = manifest["selection"]
    source = manifest["source"]
    _need(isinstance(selection, dict) and isinstance(source, dict),
          "EVENT_BUNDLE_STRUCTURE_INVALID", "Missing source or selection metadata")
    room = selection["room_id"]
    _need(type(room) is int and 0 <= room <= 255, "EVENT_BUNDLE_ROOM_INVALID",
          "Bundle room ID is invalid")
    timeline = manifest["timeline"]
    _need(isinstance(timeline, dict) and
          timeline.get("model") == "synthetic_one_cycle_update_per_counter_unit",
          "EVENT_BUNDLE_MODEL_UNSUPPORTED",
          "Bundle is not a supported synthetic counter-unit timeline")
    counter_rate = timeline["counter_rate_assumed"]
    duration = timeline["duration_seconds"]
    _need(type(counter_rate) is int and type(duration) is int and
          1 <= counter_rate <= 600 and 1 <= duration <= 20 and
          timeline["end_counter_tick_exclusive"] == counter_rate * duration and
          selection["counter_rate_assumed"] == counter_rate and
          selection["duration_seconds"] == duration,
          "EVENT_BUNDLE_TIMING_INVALID", "Manifest counter/duration values disagree")
    _need(timeline.get("engine_timer_values_observed") is False and
          manifest.get("timing", {}).get("actual_engine_schedule_observed") is False,
          "EVENT_BUNDLE_STATUS_INVALID",
          "Model must explicitly remain labeled as unverified engine timing")

    filenames = (f"room-{room:03d}_indexed.png",
                 f"room-{room:03d}_initial-clut.rgb")
    files = manifest.get("files")
    _need(isinstance(files, list) and len(files) == 2,
          "EVENT_BUNDLE_FILES_INVALID", "Expected exactly the original two source sidecars")
    declared = {}
    for item in files:
        _need(isinstance(item, dict), "EVENT_BUNDLE_FILES_INVALID",
              "Malformed source-sidecar record")
        name, digest = item["filename"], item["sha256"]
        _need(name in filenames and name not in declared
              and isinstance(digest, str) and HEX_SHA256.fullmatch(digest) is not None,
              "EVENT_BUNDLE_FILES_INVALID", "Unexpected file name or checksum")
        declared[name] = item
    _need(set(declared) == set(filenames), "EVENT_BUNDLE_FILES_INVALID",
          "Original indexed PNG and CLUT must both exist in file manifest")
    payloads = {}
    for name in filenames:
        path = directory / name
        _need(path.is_file() and not path.is_symlink(),
              "EVENT_BUNDLE_FILE_MISSING", f"Missing source bundle file {name}")
        _need(path.stat().st_size <= MAX_COMPRESSED_PNG_BYTES,
              "EVENT_BUNDLE_FILE_TOO_LARGE", f"Bundle sidecar {name} is too large")
        payload = path.read_bytes()
        _need(sha256(payload).hexdigest() == declared[name]["sha256"] and
              len(payload) == declared[name]["bytes"],
              "EVENT_BUNDLE_FILE_HASH_MISMATCH",
              f"Bundle source file {name} does not match its manifest")
        payloads[name] = payload
    width, height, indices, png_pal = read_bundle_indexed_png(payloads[filenames[0]])
    clut = payloads[filenames[1]]
    _need(png_pal == clut and len(clut) == 768,
          "EVENT_BUNDLE_PALETTE_MISMATCH", "Indexed PNG PLTE differs from original CLUT")
    _need(source["native_size"] == [width, height]
          and sha256(indices).hexdigest() == source["indexed_pixels_sha256"]
          and sha256(clut).hexdigest() == source["initial_palette_sha256"]
          and timeline["initial_palette_sha256"] == source["initial_palette_sha256"]
          and timeline["initial_indexed_pixels_sha256"] == source["indexed_pixels_sha256"],
          "EVENT_BUNDLE_SOURCE_HASH_MISMATCH",
          "Original room dimensions or decoded source fingerprint disagree")
    _need(isinstance(timeline.get("events"), list) and
          len(timeline["events"]) <= 12000,
          "EVENT_BUNDLE_EVENTS_INVALID", "Missing or excessively large event log")
    return {
        "room": room, "width": width, "height": height,
        "indices": indices, "initial_palette": clut,
        "counter_rate": counter_rate, "duration_seconds": duration,
        "events": timeline["events"], "manifest_sha256": sha256(raw_manifest).hexdigest(),
        "manifest": manifest,
    }


def render_palette_event_bundle(
    bundle_dir: str | Path, output_dir: str | Path, *, fps: int = 30,
) -> dict:
    """Export PNG sequence from saved palette patches, with no SCUMM simulation."""
    bundle_path, dest = Path(bundle_dir), Path(output_dir)
    result = {
        "schema_version": "0.1", "operation": "palette_event_bundle_render",
        "input_bundle": str(bundle_path), "output_dir": str(dest),
        "status": "failed", "fps": fps, "frames_written": 0,
        "files": [], "diagnostics": [], "provenance": {},
        "timing": {"model": "replay_of_saved_synthetic_palette_events",
                   "engine_timer_values_observed": False,
                   "real_engine_update_schedule_verified": False,
                   "seamless_loop_verified": False},
        "sampling": {},
    }

    def diag(code: str, message: str, *, severity: str = "error"):
        result["diagnostics"].append({
            "severity": severity, "code": code, "message": message,
            "source": str(bundle_path),
        })

    if type(fps) is not int or not 1 <= fps <= 60:
        diag("EVENT_RENDER_FPS_INVALID", "Output FPS must be an integer 1..60")
        return result
    if dest.is_symlink() or (dest / "render-manifest.json").exists():
        diag("OUTPUT_COLLISION", "Output folder symlink or render manifest already exists")
        return result

    try:
        bundle = read_palette_event_bundle(bundle_path)
        originals = bundle["manifest"]
        for issue in originals.get("diagnostics", []):
            result["diagnostics"].append(issue)
        frames = fps * bundle["duration_seconds"]
        if frames > MAX_SEQUENCE_FRAMES:
            raise SequenceError("EVENT_RENDER_FRAME_LIMIT",
                                f"Requested {frames} exceeds the 240-frame export limit")
        if frames * bundle["width"] * bundle["height"] > MAX_RENDER_PIXELS:
            raise SequenceError("EVENT_RENDER_PIXEL_LIMIT",
                                "Output exceeds bounded native-resolution frame budget")
        rendered = replay_event_palettes(
            bundle["initial_palette"], bundle["events"],
            counter_rate=bundle["counter_rate"],
            duration_seconds=bundle["duration_seconds"], fps=fps,
            include_palette=True)
        _need(len(rendered) == frames, "EVENT_RENDER_REPLAY_INCOMPLETE",
              "Palette replay did not yield every requested frame")
        sample_ticks = {s["modeled_counter_tick"] for s in rendered}
        # A state that exists strictly between two sampled ticks is still in
        # the authoritative event bundle, but will be omitted in this raster.
        omitted = []
        events = bundle["events"]
        final_tick = bundle["counter_rate"] * bundle["duration_seconds"]
        for event, following in zip(events, events[1:] + [{"counter_tick": final_tick}]):
            first, after = event["counter_tick"], following["counter_tick"]
            if not any(first <= sample < after for sample in sample_ticks):
                omitted.append(first)
        result["sampling"] = {
            "original_event_ticks": len(events),
            "sampled_output_frames": frames,
            "event_states_not_sampled": len(omitted),
            "omitted_event_ticks": omitted,
            "output_fps": fps,
            "duration_seconds": bundle["duration_seconds"],
            "source_counter_rate": bundle["counter_rate"],
        }
        if omitted:
            diag("EVENT_RENDER_UNSAMPLED_STATES",
                 f"{len(omitted)} intermediate modeled palette states not sampled "
                 f"at {fps} fps; originals remain in timeline.json", severity="warning")
        result["provenance"] = {
            "bundle_manifest_sha256": bundle["manifest_sha256"],
            "declared_original_resource_sha256": originals["source"]["resource_sha256"],
            "source_indexed_pixels_sha256": originals["source"]["indexed_pixels_sha256"],
            "source_initial_palette_sha256": originals["source"]["initial_palette_sha256"],
            "native_size": [bundle["width"], bundle["height"]],
            "source_game_archive_reopened": False,
            "rendered_from_saved_patches_only": True,
        }
        names = [f"room-{bundle['room']:03d}_event-frame-{i:04d}.png"
                 for i in range(frames)]
        names.append("render-manifest.json")
        if any((dest / name).exists() or (dest / name).is_symlink() for name in names):
            raise SequenceError("OUTPUT_COLLISION", "One or more output names already exist")
        dest.mkdir(parents=True, exist_ok=True)
        for state, name in zip(rendered, names):
            binary = encode_indexed_png(
                bundle["width"], bundle["height"],
                bundle["indices"], state["palette_bytes"])
            digest = _write_new_verified(dest / name, binary)
            result["files"].append({
                "filename": name, "sha256": digest, "bytes": len(binary),
                "source_palette_sha256": state["palette_sha256"],
                "sample_counter_tick": state["modeled_counter_tick"],
                "time_seconds_fraction": {
                    "numerator": state["timestamp_numerator"],
                    "denominator": state["timestamp_denominator"],
                },
            })
            result["frames_written"] += 1
        result["status"] = "success"
    except (OSError, ValueError, TypeError, KeyError, IndexError, OverflowError,
            SequenceError) as exc:
        diag(getattr(exc, "code", "EVENT_RENDER_BUNDLE_INVALID"),
             f"{type(exc).__name__}: {exc}")
        result["status"] = "partial" if result["files"] else "failed"
    if result["files"]:
        try:
            _write_new_verified(
                dest / "render-manifest.json",
                (json.dumps(result, indent=2) + "\n").encode("utf-8"))
        except (OSError, ValueError) as exc:
            diag("EVENT_RENDER_MANIFEST_WRITE_FAILED", str(exc))
            result["status"] = "partial"
    return result
