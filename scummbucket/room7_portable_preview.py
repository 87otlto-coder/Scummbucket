"""Reproducible, source-backed Room 7 saved-palette preview verifier.

Checks a user-supplied ScummVM v124 save, original MI2 DOS VGA resource
archive, and standalone background-only preview ZIP without extracting
game assets or trusting the preview report as raw-engine evidence.

Evidence boundary: PNG palettes are matched to the *claimed* engine
post/final hashes in report.json. Actual engine-*.bin files are absent from
this portable format; use verify_room7_saved_palette_counters.py for them.
"""
import hashlib
import io
import json
from pathlib import Path
import zipfile

from PIL import Image

from .saved_counter_forecast import forecast_from_saved_counters
from .scummvm_color_cycles import inspect_scummvm_color_cycles
from .scummvm_save import inspect_scummvm_save

ARCHIVE_SHA256 = "ad045372e0d49626503bb50fca29a687ec8e01ef75d9b8bca702a366d143819e"
INDEX_SHA256 = "cde7aa8980317e3a750fbb3b49884cdddaf1ff3d4231a0c840b22cceed9033f1"
ROOM_OFFSET = 392340
ROOM_LENGTH = 82695
XOR_KEY = 0x69
MAX_ZIP_TOTAL_BYTES = 64 * 1024 * 1024
MAX_PNG_BYTES = 2 * 1024 * 1024
MAX_REPORT_BYTES = 3 * 1024 * 1024


class PortableRoom7Error(ValueError):
    pass


def digest(data):
    return hashlib.sha256(data).hexdigest()


def parse_room7_cycles(source, *, expected_sha=ARCHIVE_SHA256,
                       room_offset=ROOM_OFFSET, room_length=ROOM_LENGTH):
    """Decode CYCL from a pinned original DOS room resource, not a report."""
    if digest(source) != expected_sha:
        raise PortableRoom7Error("Original MONKEY2.001 resource archive hash mismatch")
    if room_offset < 0 or room_length < 8 or room_offset + room_length > len(source):
        raise PortableRoom7Error("Room 7 source range outside archive")
    room = bytes(byte ^ XOR_KEY for byte in
                 source[room_offset:room_offset + room_length])
    if room[:4] != b"ROOM" or int.from_bytes(room[4:8], "big") != room_length:
        raise PortableRoom7Error("Pinned room resource header does not match")
    location = 8
    blocks = []
    while location < len(room):
        if location + 8 > len(room):
            raise PortableRoom7Error("Truncated room chunk header")
        length = int.from_bytes(room[location+4:location+8], "big")
        if length < 8 or location + length > len(room):
            raise PortableRoom7Error("Invalid room child chunk extent")
        if room[location:location+4] == b"CYCL":
            blocks.append((location, room[location+8:location+length]))
        location += length
    if location != len(room) or len(blocks) != 1:
        raise PortableRoom7Error("Expected exactly one complete CYCL chunk")
    offset, data = blocks[0]
    if len(data) < 11 or data[-2:] != bytes(2) or (len(data)-2) % 9:
        raise PortableRoom7Error("Invalid CYCL records or terminator")
    rows = []
    for index in range(0, len(data)-2, 9):
        entry = data[index:index+9]
        rows.append({
            "id": entry[0],
            "rate_raw": int.from_bytes(entry[3:5], "big"),
            "flags": int.from_bytes(entry[5:7], "big"),
            "start_color": entry[7],
            "end_color": entry[8],
            "offset": room_offset + offset + 8 + index,
        })
    if len(rows) != 6 or sorted(row["id"] for row in rows) != list(range(1, 7)):
        raise PortableRoom7Error("Unexpected pinned Room 7 cycle inventory")
    return rows


def _read_limited(zf, name, limit):
    info = zf.getinfo(name)
    if info.file_size > limit:
        raise PortableRoom7Error(f"ZIP member exceeds limit: {name}")
    with zf.open(info) as stream:
        data = stream.read(limit + 1)
    if len(data) > limit:
        raise PortableRoom7Error(f"ZIP member expanded beyond limit: {name}")
    return data


def verify_saved_preview(preview_zip, save_path, archive_bytes, *,
                         expected_sha=ARCHIVE_SHA256,
                         expected_index_sha=INDEX_SHA256,
                         room_offset=ROOM_OFFSET, room_length=ROOM_LENGTH,
                         expected_frames=87):
    """Compare saved CYCL counters to each preview PNG's verified palette.

    Returns metadata-only diagnostics. May be run on small *synthetic* frames
    by passing test-specific source hash and room geometry parameters.
    """
    archive_cycles = parse_room7_cycles(
        archive_bytes, expected_sha=expected_sha,
        room_offset=room_offset, room_length=room_length)
    save_path, preview_zip = Path(save_path), Path(preview_zip)
    save_raw = save_path.read_bytes()
    save_state = inspect_scummvm_save(save_path)
    if (save_state["current_room"], save_state["room_resource"]) != (7, 7):
        raise PortableRoom7Error("Original ScummVM saved state is not Room 7")
    saved_cycles = inspect_scummvm_color_cycles(save_path, archive_cycles)
    expected = {"play.html", "report.json"}
    expected |= {f"viewport-{i:03}.png" for i in range(1, expected_frames + 1)}
    png_records = []
    sample_rows = []
    index_hashes = set()
    first_palette = None
    previous_ms = None
    with zipfile.ZipFile(preview_zip) as zf:
        entries = zf.infolist()
        names = [item.filename for item in entries]
        if len(names) != len(expected) or set(names) != expected:
            raise PortableRoom7Error("ZIP inventory mismatch or duplicate entries")
        if sum(item.file_size for item in entries) > MAX_ZIP_TOTAL_BYTES:
            raise PortableRoom7Error("ZIP uncompressed inventory exceeds limit")
        report = json.loads(_read_limited(zf, "report.json", MAX_REPORT_BYTES))
        run = report.get("run", {})
        if (report.get("schema") != "room7-sweep/1" or run.get("room") != 7 or
                run.get("archives") !=
                {"MONKEY2.000": expected_index_sha,
                 "MONKEY2.001": expected_sha} or
                run.get("save_sha256") != digest(save_raw)):
            raise PortableRoom7Error("ZIP report provenance mismatches source inputs")
        if (run.get("debugger_equivalent_entry") is not False or "walk" in run or
                run.get("entry_provenance", {}).get("method") !=
                "loaded_private_save_no_debugger_or_injected_walk"):
            raise PortableRoom7Error("Preview is not labeled saved-game entry")
        frames = report.get("frames")
        if not isinstance(frames, list) or len(frames) != expected_frames:
            raise PortableRoom7Error("Expected complete ordered frame records")
        _read_limited(zf, "play.html", MAX_REPORT_BYTES)
        for n, row in enumerate(frames, 1):
            name = f"viewport-{n:03}.png"
            if row.get("id") != n:
                raise PortableRoom7Error(f"Nonsequential report frame at {n}")
            palette_hashes = row.get("palette_stages_sha256")
            if not isinstance(palette_hashes, list) or len(palette_hashes) != 4:
                raise PortableRoom7Error(f"Missing four palette stages at frame {n}")
            ms = row.get("present_ms")
            if type(ms) is not int or (previous_ms is not None and ms < previous_ms):
                raise PortableRoom7Error(f"Invalid frame timing at {n}")
            previous_ms = ms
            png = _read_limited(zf, name, MAX_PNG_BYTES)
            with Image.open(io.BytesIO(png)) as image:
                if image.format != "PNG" or image.mode != "P" or image.size != (320, 144):
                    raise PortableRoom7Error(f"Unexpected indexed PNG geometry at {n}")
                palette_values = image.getpalette()
                if palette_values is None or len(palette_values) != 768:
                    raise PortableRoom7Error(f"Invalid 768-byte PNG palette at {n}")
                palette = bytes(palette_values)
                index_hashes.add(digest(image.tobytes()))
            if digest(palette) != palette_hashes[1] or digest(palette) != palette_hashes[3]:
                raise PortableRoom7Error(
                    f"PNG palette differs from reported post/final palette at {n}")
            if n == 1:
                if digest(palette) != palette_hashes[0]:
                    raise PortableRoom7Error(
                        "First pre-cycle palette unavailable from preview; "
                        "use raw engine frame validation")
                first_palette = palette
            sample_rows.append({
                "timer_pair": row.get("timer_pair"),
                "post_palette": palette,
            })
            png_records.append({
                "frame": n, "png_sha256": digest(png),
                "post_final_palette_sha256": digest(palette),
            })
        if zf.testzip() is not None:
            raise PortableRoom7Error("ZIP CRC integrity test failed")
    outcome = forecast_from_saved_counters(
        archive_cycles, saved_cycles["cycles"], first_palette, sample_rows)
    return {
        "schema": "room7-portable-saved-preview-verification/1",
        "status": ("portable_palettes_matched" if outcome["mismatch_frame_count"] == 0
                   else "portable_palette_mismatch"),
        "evidence_boundary": {
            "save_counters": "direct_scummvm_v124_save_bytes",
            "cycle_definitions": "pinned_archive_decoded_CYCL",
            "initial_palette": "first_png_matches_reported_engine_pre_palette_hash",
            "timer_pair": "supplied_capture_report",
            "observed_palette": "PNG_values_hash_correlated_to_supplied_report",
            "actual_raw_engine_buffers_reexamined": False,
            "browser_playback_confirmed": False,
            "actor_or_frontbuffer_independently_rendered": False,
        },
        "source_sha256": {
            "save": digest(save_raw),
            "original_resource_archive": digest(archive_bytes),
            "preview_zip": digest(preview_zip.read_bytes()),
            "serialized_cycle_block": saved_cycles["block_sha256"],
        },
        "saved_room": saved_state["current_room"],
        "saved_cycle_counters": {
            str(row["id"]): row["saved_counter"] for row in saved_cycles["cycles"]
        },
        "cycle_definitions": archive_cycles,
        "frame_count": len(sample_rows),
        "distinct_index_planes": len(index_hashes),
        "exact_palette_count": outcome["exact_frame_count"],
        "mismatching_palette_count": outcome["mismatch_frame_count"],
        "first_mismatch_frame": outcome["first_mismatch_frame"],
        "palette_mismatches": [
            row for row in outcome["frames"] if not row["matches"]
        ],
        "per_frame": png_records,
        "counter_phase_fitting_used": False,
    }
