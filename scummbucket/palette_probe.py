"""Experimental palette-cycle/background probe for original DOS MI2 SCUMM v5.

A native room bitmap is decoded into immutable palette indices; the initial
CLUT is rotated on a *synthetic* one-counter-unit-per-update schedule.
These snapshots are not observed gameplay frames, verified wall-clock timing,
or evidence that gameplay scripts leave the cycle configuration unchanged.

No copyrighted input bytes are embedded in this module.
"""
from __future__ import annotations

from collections import Counter
from hashlib import sha256
import json
from pathlib import Path
import struct

from .extraction import _write_new_verified
from .inspector import chunks, inspect, _read_pair, XOR_KEY, InspectionError
from .object_images import ImageDecodeError, decode_strip, encode_png, MAX_PIXELS

MAX_SIMULATED_TICKS = 4096
MAX_SNAPSHOTS = 16


class PaletteProbeError(Exception):
    def __init__(self, code: str, message: str, *, offset: int | None = None):
        super().__init__(message)
        self.code = code
        self.offset = offset


def _require(condition: bool, code: str, message: str, *, offset: int | None = None):
    if not condition:
        raise PaletteProbeError(code, message, offset=offset)


def _one(children, tag: str):
    matches = [p for p in children if p.tag == tag]
    _require(len(matches) == 1, f"BACKGROUND_{tag}_COUNT",
             f"Expected exactly one {tag} child, found {len(matches)}")
    return matches[0]


def decode_room_background_indexed(data: bytes, *, room_offset: int,
                                   room_length: int) -> dict:
    """Decode RMIM > IM00 > SMAP to palette indices, not pre-colored pixels."""
    _require(0 <= room_offset <= len(data) - 8 and
             8 <= room_length <= len(data) - room_offset,
             "BACKGROUND_ROOM_RANGE_INVALID", "Invalid room chunk range",
             offset=room_offset)
    _require(data[room_offset:room_offset + 4] == b"ROOM" and
             struct.unpack_from(">I", data, room_offset + 4)[0] == room_length,
             "BACKGROUND_ROOM_HEADER_INVALID", "Invalid ROOM tag or size",
             offset=room_offset)
    room_children = chunks(data, room_offset + 8, room_offset + room_length,
                           "decoded MONKEY2.001")
    rmhd = _one(room_children, "RMHD")
    _require(rmhd.length >= 12, "BACKGROUND_RMHD_TRUNCATED",
             "Missing room width/height", offset=rmhd.offset)
    width, height = struct.unpack_from("<HH", data, rmhd.offset + 8)
    _require(0 < width <= 2048 and width % 8 == 0 and
             0 < height <= 1024 and width * height <= MAX_PIXELS,
             "BACKGROUND_DIMENSIONS_UNSUPPORTED",
             f"Unsupported room geometry {width}x{height}", offset=rmhd.offset)

    clut = _one(room_children, "CLUT")
    _require(clut.length == 776, "BACKGROUND_CLUT_SIZE_INVALID",
             f"Expected 256 RGB colors, got {clut.length - 8} palette bytes",
             offset=clut.offset)
    palette = bytes(data[clut.offset + 8:clut.offset + clut.length])

    rmim = _one(room_children, "RMIM")
    rmim_children = chunks(data, rmim.offset + 8, rmim.end, "decoded MONKEY2.001")
    im00 = _one(rmim_children, "IM00")
    im00_children = chunks(data, im00.offset + 8, im00.end, "decoded MONKEY2.001")
    smap = _one(im00_children, "SMAP")

    num_strips = width // 8
    min_offset = 8 + num_strips * 4
    _require(smap.length >= min_offset, "BACKGROUND_SMAP_TABLE_TRUNCATED",
             "SMAP cannot contain required strip-offset table", offset=smap.offset)
    offsets = [struct.unpack_from("<I", data, smap.offset + 8 + i * 4)[0]
               for i in range(num_strips)]
    _require(all(min_offset <= value < smap.length for value in offsets),
             "BACKGROUND_SMAP_OFFSET_INVALID",
             "SMAP strip pointer outside its chunk", offset=smap.offset)
    _require(all(a < b for a, b in zip(offsets, offsets[1:])),
             "BACKGROUND_SMAP_OFFSET_ORDER",
             "SMAP strip pointers are not strictly increasing", offset=smap.offset)

    indexed = bytearray(width * height)
    strips = []
    unusual_trailing = []
    for strip, relative in enumerate(offsets):
        start = smap.offset + relative
        end = smap.offset + (offsets[strip + 1] if strip + 1 < num_strips
                             else smap.length)
        codec = data[start]
        pixels, transparent, consumed = decode_strip(
            codec, data[start + 1:end], height)
        # A transparent-background strip may require the previous framebuffer;
        # the current preview cannot safely infer its resulting pixels.
        _require(not transparent, "BACKGROUND_TRANSPARENT_CODEC_UNSUPPORTED",
                 f"Room background strip {strip} uses transparency-aware codec {codec}",
                 offset=start)
        _require(len(pixels) == height * 8, "BACKGROUND_PIXEL_COUNT_INVALID",
                 "Decoded strip has wrong pixel count", offset=start)
        if any(data[start + 1 + consumed:end]):
            unusual_trailing.append({
                "code": "BACKGROUND_STRIP_NONZERO_TRAILING_DATA",
                "severity": "warning", "offset": start + 1 + consumed,
                "message": (f"Strip {strip} has nonzero bytes after decoding "
                            "the expected pixel count; requires investigation")})
        for y in range(height):
            begin = y * width + strip * 8
            indexed[begin:begin + 8] = pixels[y * 8:y * 8 + 8]
        strips.append({"index": strip, "source_offset": start, "codec": codec,
                       "compressed_length": end - start - 1,
                       "consumed_length": consumed})
    return {
        "width": width, "height": height,
        "indexed_pixels": bytes(indexed), "initial_palette": palette,
        "pixel_indices_sha256": sha256(indexed).hexdigest(),
        "initial_palette_sha256": sha256(palette).hexdigest(),
        "strips": strips,
        "background_zplanes": sorted(
            p.tag for p in im00_children if p.tag.startswith("ZP")),
        "diagnostics": unusual_trailing,
        "source": {"room_offset": room_offset, "rmhd_offset": rmhd.offset,
                   "clut_offset": clut.offset, "rmim_offset": rmim.offset,
                   "im00_offset": im00.offset, "smap_offset": smap.offset},
    }


def prepare_cycles(records: list[dict]) -> tuple[list[dict], list[dict]]:
    """Calculate engine counter thresholds; do not interpret counter units as ms."""
    output = []
    problems = []
    seen = set()
    for record in records:
        cid, rate, flags = record["id"], record["rate_raw"], record["flags"]
        first, last = record["start_color"], record["end_color"]
        _require(1 <= cid <= 16 and cid not in seen,
                 "CYCLE_ID_INVALID", f"Invalid or duplicate cycle ID {cid}")
        seen.add(cid)
        _require(0 <= first <= last <= 255, "CYCLE_RANGE_INVALID",
                 f"Invalid color range {first}..{last} for cycle {cid}")
        if rate == 0:
            problems.append({"severity": "error", "code": "CYCLE_RATE_ZERO",
                             "message": f"Cycle {cid} has zero divisor"})
            threshold = 0
        else:
            threshold = 16384 // rate
        if threshold == 0:
            problems.append({"severity": "warning", "code": "CYCLE_DISABLED_ZERO_THRESHOLD",
                             "message": (f"Cycle {cid} has zero computed delay "
                                         "(engine would skip it)")})
        output.append({"id": cid, "rate_raw": rate,
                       "flags_raw": flags, "start_color": first,
                       "end_color": last,
                       "delay_counter_units": threshold,
                       "direction_from_flag_bit_1": ("reverse" if flags & 2 else "forward"),
                       "counter": 0, "rotation_events": 0,
                       "nonstandard_flag_bits": flags & ~2,
                       "source_offset": record["offset"]})
    return output, problems


def advance_palette(palette: bytearray, cycles: list[dict]) -> list[dict]:
    """One hypothetical scheduler update, with delta=1 counter unit.

    ScummVM: one rotation at most per update if counter >= delay.
    Rendering/real-time scheduling and script-side modifications are unmodeled.
    """
    changed = []
    for cycle in cycles:
        delay = cycle["delay_counter_units"]
        if not delay or cycle["start_color"] >= cycle["end_color"]:
            continue
        cycle["counter"] += 1
        if cycle["counter"] < delay:
            continue
        cycle["counter"] %= delay
        a, b = cycle["start_color"], cycle["end_color"]
        colors = [bytes(palette[i * 3:i * 3 + 3]) for i in range(a, b + 1)]
        # SCUMM forward moves the last entry into the first position.
        shifted = (colors[1:] + colors[:1] if cycle["flags_raw"] & 2
                   else colors[-1:] + colors[:-1])
        for i, color in enumerate(shifted, a):
            palette[i * 3:i * 3 + 3] = color
        cycle["rotation_events"] += 1
        changed.append({"cycle_id": cycle["id"], "start_color": a,
                        "end_color": b,
                        "direction": cycle["direction_from_flag_bit_1"]})
    return changed


def _render_rgb(indexed: bytes, palette: bytes) -> bytes:
    return b"".join(palette[i * 3:i * 3 + 3] for i in indexed)


def _render_rgba(indexed: bytes, palette: bytes) -> bytes:
    return b"".join(palette[i * 3:i * 3 + 3] + b"\xff" for i in indexed)


def simulate_palette_snapshots(indexed: bytes, initial_palette: bytes,
                               cycles: list[dict], ticks: list[int]) -> list[dict]:
    """Calculate reproducible *hypothetical* frames and event logs, not runtime."""
    _require(bool(ticks) and len(ticks) <= MAX_SNAPSHOTS and
             len(set(ticks)) == len(ticks) and all(
                 type(tick) is int and 0 <= tick <= MAX_SIMULATED_TICKS for tick in ticks),
             "TICKS_INVALID", f"Choose 1..{MAX_SNAPSHOTS} distinct ticks from "
                              f"0..{MAX_SIMULATED_TICKS}")
    _require(len(initial_palette) == 768, "PALETTE_INVALID",
             "Expected exactly 256 RGB palette entries")
    _require(all(0 <= idx <= 255 for idx in indexed), "INDEX_INVALID",
             "Palette index outside 0..255")
    requested = set(ticks)
    palette = bytearray(initial_palette)
    history = []
    frames = []
    initial_rgb = _render_rgb(indexed, initial_palette)
    for tick in range(max(ticks) + 1):
        if tick:
            for event in advance_palette(palette, cycles):
                history.append({"simulated_counter_tick": tick, **event})
        if tick in requested:
            current = _render_rgb(indexed, palette)
            changed = sum(initial_rgb[p:p + 3] != current[p:p + 3]
                          for p in range(0, len(current), 3))
            frames.append({"tick": tick, "palette": bytes(palette),
                           "visible_changed_pixels": changed,
                           "total_rotation_events": len(history),
                           "palette_sha256": sha256(palette).hexdigest(),
                           "palette_events_so_far": len(history)})
    return sorted(frames, key=lambda f: f["tick"])


def palette_probe(input_path: str | Path, output_dir: str | Path, *,
                  room_id: int, ticks: list[int]) -> dict:
    src, dest = Path(input_path), Path(output_dir)
    report = {"schema_version": "0.1", "operation": "palette_probe",
              "input": str(src), "output_dir": str(dest),
              "status": "failed", "selection": {"room_id": room_id, "ticks": ticks},
              "summary": {"snapshots": 0, "visible_cycle_pixels": 0,
                          "cycle_records": 0},
              "files": [], "cycles": [], "snapshots": [], "diagnostics": [],
              "verification": {"engine_source": "ScummVM palette.cpp initCycl/cyclePalette",
                               "clock": "hypothetical 1 counter unit per update",
                               "runtime_observed": False,
                               "rendering_reference_verified": False,
                               "script_interference_modelled": False}}
    def problem(code, message, *, severity="error", offset=None):
        report["diagnostics"].append({
            "severity": severity, "code": code, "message": message,
            "source": str(src), "offset": offset, "resource_id": room_id})
    if type(room_id) is not int or not 0 <= room_id <= 255:
        problem("ROOM_ID_INVALID", "Room ID must be between 0 and 255")
        return report
    try:
        _require(bool(ticks) and len(ticks) <= MAX_SNAPSHOTS
                 and len(set(ticks)) == len(ticks)
                 and all(type(t) is int and 0 <= t <= MAX_SIMULATED_TICKS
                         for t in ticks), "TICKS_INVALID",
                 f"Require 1..{MAX_SNAPSHOTS} distinct ticks in 0..{MAX_SIMULATED_TICKS}")
    except (TypeError, PaletteProbeError) as exc:
        problem(getattr(exc, "code", "TICKS_INVALID"), str(exc))
        return report
    inv = inspect(src)
    report["diagnostics"].extend(inv["diagnostics"])
    if inv["status"] != "success":
        problem("PALETTE_PROBE_INSPECTION_FAILED",
                "Source inspection failed; no preview produced")
        return report
    scenes = [r for r in inv["resources"]["rooms"] if r["id"] == room_id]
    if len(scenes) != 1:
        problem("ROOM_NOT_FOUND", f"Expected unique room {room_id}")
        return report
    if dest.is_symlink() or (dest / "manifest.json").exists():
        problem("OUTPUT_COLLISION", "Output directory is a symlink or manifest exists")
        return report
    try:
        _, raw, _, label = _read_pair(src)
        _require(sha256(raw).hexdigest() == inv["sources"][1]["sha256"],
                 "SOURCE_CHANGED", "Source hash changed after inspection")
        decoded = bytes(x ^ XOR_KEY for x in raw)
        room = scenes[0]
        bg = decode_room_background_indexed(
            decoded, room_offset=room["room_offset"], room_length=room["room_size"])
        cycles, issues = prepare_cycles(room["palette_cycles"])
        for issue in bg["diagnostics"] + issues:
            problem(issue["code"], issue["message"],
                    severity=issue["severity"], offset=issue.get("offset"))
        # Preserve rate=0 as an error rather than pretending the engine can
        # initialize that cycle safely.
        _require(not any(x["severity"] == "error" for x in issues),
                 "PALETTE_CYCLE_INVALID", "Cannot model a cycle with invalid rate")
        histogram = Counter(bg["indexed_pixels"])
        report["summary"]["cycle_records"] = len(cycles)
        report["summary"]["visible_cycle_pixels"] = sum(
            sum(histogram[i] for i in range(c["start_color"], c["end_color"] + 1))
            for c in cycles)
        report["source"] = {"resource_name": label,
                            "resource_sha256": sha256(raw).hexdigest(),
                            **bg["source"],
                            "native_size": [bg["width"], bg["height"]],
                            "indexed_pixels_sha256": bg["pixel_indices_sha256"],
                            "clut_sha256": bg["initial_palette_sha256"],
                            "background_zplanes_present_not_composited":
                                bg["background_zplanes"]}
        frames = simulate_palette_snapshots(bg["indexed_pixels"],
                                            bg["initial_palette"], cycles, ticks)
        dest.mkdir(parents=True, exist_ok=True)
        report["cycles"] = cycles
        for frame in frames:
            filename = f"room-{room_id:03d}_hypothetical-tick-{frame['tick']:04d}.png"
            image = encode_png(bg["width"], bg["height"],
                               _render_rgba(bg["indexed_pixels"], frame["palette"]),
                               rgba=True)
            digest = _write_new_verified(dest / filename, image)
            report["files"].append({"filename": filename, "sha256": digest})
            report["snapshots"].append({
                "synthetic_counter_tick": frame["tick"], "filename": filename,
                "visible_changed_pixels_vs_initial": frame["visible_changed_pixels"],
                "cycle_rotation_events": frame["total_rotation_events"],
                "palette_sha256": frame["palette_sha256"]})
            report["summary"]["snapshots"] += 1
        report["status"] = "success"
    except (OSError, ValueError, InspectionError, PaletteProbeError,
            ImageDecodeError) as exc:
        problem(getattr(exc, "code", "PALETTE_PROBE_ERROR"),
                f"{type(exc).__name__}: {exc}", offset=getattr(exc, "offset", None))
        report["status"] = "partial" if report["files"] else "failed"
    if report["files"]:
        try:
            _write_new_verified(dest / "manifest.json",
                                (json.dumps(report, indent=2) + "\n").encode("utf-8"))
        except OSError as exc:
            problem("MANIFEST_WRITE_FAILED", str(exc))
            report["status"] = "partial"
    return report
