"""Experimental DOS SCUMM v5 OBIM image-state decoding (P2 spike).

Produces independently indexed RGBA PNG state images plus *separate* depth
mask PNGs. No game archive bytes or ScummVM source code are distributed.

This decoder supports the limited strip codec families observed in the
fingerprinted Monkey Island 2 sample. It is NOT a full SCUMM renderer, and
output has NOT yet passed pixel-by-pixel comparison with ScummVM.
"""
from __future__ import annotations

from collections import Counter
from hashlib import sha256
from pathlib import Path
import struct
import zlib

from .extraction import _write_new_verified
from .inspector import XOR_KEY, _read_pair, inspect, InspectionError, chunks

MAX_PIXELS = 2_000_000
MAX_IMAGE_STATES = 256


class ImageDecodeError(Exception):
    def __init__(self, code: str, message: str, *, offset: int | None = None):
        super().__init__(message)
        self.code, self.offset = code, offset


def _need(ok: bool, code: str, message: str, *, offset: int | None = None):
    if not ok:
        raise ImageDecodeError(code, message, offset=offset)


def _read_bits_1stream(stream: bytes, count: list[int], n: int):
    """Read n least-significant-first bits; raise rather than reading past strip."""
    while count[0] < n:
        pos = count[1]
        _need(pos < len(stream), "STRIP_BITSTREAM_TRUNCATED",
              "Compressed strip ended before enough bits could be read")
        count[2] |= stream[pos] << count[0]
        count[0] += 8
        count[1] += 1
    out = count[2] & ((1 << n) - 1)
    count[2] >>= n
    count[0] -= n
    return out


def decode_strip(codec: int, stream: bytes, height: int) -> tuple[bytes, bool, int]:
    """Return 8xheight palette indices (row-major), transparency flag, bytes read.

    Only SCUMM v5 RAW256, zigzag 4–8-bit and major/minor 4–8-bit
    horizontal strip variants with bounded LSB-first bitstreams.
    """
    _need(1 <= height <= 1024, "STRIP_HEIGHT_INVALID", "Invalid strip height")
    _need(bool(stream), "STRIP_EMPTY", "No strip payload bytes")
    transparent = False
    width = 8
    count = height * width
    major_minor = (64 <= codec <= 68 or 84 <= codec <= 88
                   or 104 <= codec <= 108 or 124 <= codec <= 128)
    basic_vert = 14 <= codec <= 18 or 34 <= codec <= 38
    basic_horiz = 24 <= codec <= 28 or 44 <= codec <= 48
    transparent = (34 <= codec <= 38 or 44 <= codec <= 48
                   or 84 <= codec <= 88 or 124 <= codec <= 128 or codec == 149)
    if codec == 1 or codec == 149:
        _need(len(stream) >= count, "STRIP_RAW_TRUNCATED",
              f"RAW strip needs {count} bytes, found {len(stream)}")
        return stream[:count], transparent, count
    _need(major_minor or basic_vert or basic_horiz, "STRIP_CODEC_UNSUPPORTED",
          f"Compression code {codec} is not implemented")

    if major_minor:
        _need(len(stream) >= 3, "STRIP_HEADER_TRUNCATED", "Major/minor header missing")
        color = stream[0]
        bit_state = [16, 3, stream[1] | (stream[2] << 8)]
        repeated = 0
        pixels = bytearray(count)
        for i in range(count):
            pixels[i] = color
            if i == count - 1:
                break  # No following pixel: no following color-change bits needed.
            if repeated:
                repeated -= 1
                continue
            if _read_bits_1stream(stream, bit_state, 1) == 0:
                continue
            if _read_bits_1stream(stream, bit_state, 1) == 0:
                color = _read_bits_1stream(stream, bit_state, codec % 10)
                continue
            delta = _read_bits_1stream(stream, bit_state, 3) - 4
            if delta:
                color = (color + delta) & 0xFF
            else:
                # This is the v5 major/minor identical-pixel run extension.
                run = _read_bits_1stream(stream, bit_state, 8)
                repeated = (run - 1) & 0xFF
        return bytes(pixels), transparent, bit_state[1]

    _need(len(stream) >= 2, "STRIP_HEADER_TRUNCATED", "Basic-strip header missing")
    color = stream[0]
    direction = -1
    bit_state = [8, 2, stream[1]]
    pixels = bytearray(count)
    for i in range(count):
        x = i // height if basic_vert else i % 8
        y = i % height if basic_vert else i // 8
        pixels[y * 8 + x] = color
        if i == count - 1:
            break
        if not _read_bits_1stream(stream, bit_state, 1):
            continue
        if not _read_bits_1stream(stream, bit_state, 1):
            color = _read_bits_1stream(stream, bit_state, codec % 10)
            direction = -1
        elif not _read_bits_1stream(stream, bit_state, 1):
            color = (color + direction) & 0xFF
        else:
            direction = -direction
            color = (color + direction) & 0xFF
    return bytes(pixels), transparent, bit_state[1]


def decode_mask_strip(stream: bytes, height: int) -> tuple[bytes, int]:
    """Expand SCUMM ZPxx RLE into one byte of mask bits per scanline."""
    out = bytearray()
    pos = 0
    while len(out) < height:
        _need(pos < len(stream), "MASK_STREAM_TRUNCATED", "Mask run header missing")
        control = stream[pos]
        pos += 1
        length = control & 0x7F
        _need(length > 0, "MASK_ZERO_RUN", "Zero-length mask run is invalid")
        _need(len(out) + length <= height, "MASK_RUN_OVERFLOW",
              "Mask run exceeds the declared image height")
        if control & 0x80:
            _need(pos < len(stream), "MASK_STREAM_TRUNCATED", "Mask repeated value missing")
            out.extend([stream[pos]] * length)
            pos += 1
        else:
            _need(pos + length <= len(stream), "MASK_STREAM_TRUNCATED",
                  "Mask literal run exceeds compressed strip")
            out.extend(stream[pos:pos + length])
            pos += length
    return bytes(out), pos


def _png_chunk(tag: bytes, payload: bytes) -> bytes:
    return (struct.pack(">I", len(payload)) + tag + payload
            + struct.pack(">I", zlib.crc32(tag + payload) & 0xFFFFFFFF))


def encode_png(width: int, height: int, pixels: bytes, *, rgba: bool) -> bytes:
    """Write minimal, deterministic, standards-compliant PNG without Pillow."""
    bpp = 4 if rgba else 1
    _need(0 < width * height <= MAX_PIXELS, "PNG_DIMENSIONS_INVALID",
          "PNG dimensions outside supported bounds")
    _need(len(pixels) == width * height * bpp, "PNG_PIXEL_BUFFER_INVALID",
          "Decoded pixel count does not match image dimensions")
    stride = width * bpp
    filtered = b"".join(b"\x00" + pixels[y * stride:(y + 1) * stride]
                        for y in range(height))
    return (b"\x89PNG\r\n\x1a\n"
            + _png_chunk(b"IHDR", struct.pack(">IIBBBBB", width, height, 8,
                                              6 if rgba else 0, 0, 0, 0))
            + _png_chunk(b"IDAT", zlib.compress(filtered, level=9))
            + _png_chunk(b"IEND", b""))


def _subchunks(data: bytes, offset: int, size: int):
    return list(chunks(data, offset + 8, offset + size, "decoded MONKEY2.001"))


def _decode_stripmap(data: bytes, smap, *, width: int, height: int,
                     palette: bytes, transparent_color: int) -> tuple[bytes, list[dict]]:
    strips = width // 8
    minimum_offset = 8 + strips * 4
    _need(smap.length >= minimum_offset, "SMAP_TABLE_TRUNCATED", "SMAP table too short",
          offset=smap.offset)
    offsets = [struct.unpack_from("<I", data, smap.offset + 8 + i * 4)[0]
               for i in range(strips)]
    _need(all(minimum_offset <= off < smap.length for off in offsets),
          "SMAP_OFFSET_INVALID", "SMAP strip offset outside the chunk", offset=smap.offset)
    _need(all(a < b for a, b in zip(offsets, offsets[1:])),
          "SMAP_OFFSET_ORDER_INVALID", "SMAP offsets are not strictly increasing",
          offset=smap.offset)
    image = bytearray(width * height * 4)
    strip_records = []
    for strip, relative in enumerate(offsets):
        position = smap.offset + relative
        next_pos = smap.offset + (offsets[strip + 1] if strip + 1 < strips else smap.length)
        code = data[position]
        indices, has_transparency, consumed = decode_strip(
            code, data[position + 1:next_pos], height)
        _need(consumed <= next_pos - position - 1, "STRIP_CONSUMPTION_OVERFLOW",
              "Strip decoded beyond its bounded compressed data", offset=position)
        _need(not any(data[position + 1 + consumed:next_pos]),
              "STRIP_TRAILING_NONZERO",
              "Compressed strip has unexpected nonzero trailing bytes",
              offset=position + 1 + consumed)
        for y in range(height):
            for x in range(8):
                idx = indices[y * 8 + x]
                at = (y * width + strip * 8 + x) * 4
                if has_transparency and idx == transparent_color:
                    # Zero the invisible RGB channels, too, to avoid colored
                    # halos if a later scaling filter samples transparent pixels.
                    image[at:at + 4] = b"\x00\x00\x00\x00"
                else:
                    image[at:at + 3] = palette[idx * 3:idx * 3 + 3]
                    image[at + 3] = 255
        strip_records.append({
            "strip": strip, "source_offset": position, "codec": code,
            "compressed_length": next_pos - position - 1,
            "consumed_length": consumed, "transparent_codec": has_transparency})
    return bytes(image), strip_records


def _decode_zplane(data: bytes, plane, *, width: int, height: int) -> bytes:
    strips = width // 8
    min_offset = 8 + strips * 2
    _need(plane.length >= min_offset, "ZPLANE_TABLE_TRUNCATED",
          "Z plane strip-offset table too short", offset=plane.offset)
    offsets = [struct.unpack_from("<H", data, plane.offset + 8 + i * 2)[0]
               for i in range(strips)]
    _need(all(min_offset <= x < plane.length for x in offsets),
          "ZPLANE_OFFSET_INVALID", "Z plane strip offset is out of bounds",
          offset=plane.offset)
    _need(all(a < b for a, b in zip(offsets, offsets[1:])),
          "ZPLANE_OFFSET_ORDER_INVALID", "Z plane strip offsets out of order",
          offset=plane.offset)
    mask = bytearray(width * height)
    for strip, relative in enumerate(offsets):
        start = plane.offset + relative
        end = plane.offset + (offsets[strip + 1] if strip + 1 < strips else plane.length)
        scanlines, consumed = decode_mask_strip(data[start:end], height)
        _need(not any(data[start + consumed:end]), "MASK_TRAILING_NONZERO",
              "Depth-mask strip contains nonzero trailing bytes",
              offset=start + consumed)
        for y, bits in enumerate(scanlines):
            for x in range(8):
                mask[y * width + strip * 8 + x] = 255 if bits & (0x80 >> x) else 0
    return bytes(mask)


def decode_object_state(data: bytes, *, obim_offset: int, state_tag: str,
                        palette: bytes, transparent_color: int,
                        include_masks: bool = True) -> tuple[dict, bytes, dict[str, bytes]]:
    """Decode a single IMxx state, but do not composite it into a room."""
    _need(len(palette) == 768, "PALETTE_INVALID", "Expected 256 RGB palette entries")
    _need(0 <= transparent_color <= 255, "TRNS_INVALID", "Transparent index out of bounds")
    _need(0 <= obim_offset <= len(data) - 8, "OBIM_OFFSET_INVALID",
          "Object-image chunk header out of bounds", offset=obim_offset)
    _need(data[obim_offset:obim_offset + 4] == b"OBIM", "OBIM_TAG_INVALID",
          "Expected an OBIM object-image chunk", offset=obim_offset)
    root_size = struct.unpack_from(">I", data, obim_offset + 4)[0]
    _need(8 <= root_size <= len(data) - obim_offset, "OBIM_LENGTH_INVALID",
          "OBIM chunk length exceeds input", offset=obim_offset)
    images = _subchunks(data, obim_offset, root_size)
    header = [p for p in images if p.tag == "IMHD"]
    _need(len(header) == 1 and header[0].length >= 24,
          "IMHD_INVALID", "Expected one full v5 IMHD header", offset=obim_offset)
    obj_id, declared = struct.unpack_from("<HH", data, header[0].offset + 8)
    width, height = struct.unpack_from("<HH", data, header[0].offset + 20)
    _need(0 < width <= 2048 and width % 8 == 0 and 0 < height <= 1024
          and width * height <= MAX_PIXELS, "IMAGE_DIMENSIONS_UNSUPPORTED",
          f"Unsupported OBIM geometry: {width}x{height}", offset=header[0].offset)
    states = [p for p in images if p.tag.startswith("IM") and p.tag != "IMHD"]
    _need(len(states) == declared, "IMAGE_COUNT_MISMATCH",
          f"IMHD declares {declared} images but parsed {len(states)}", offset=header[0].offset)
    found = [p for p in states if p.tag == state_tag]
    _need(len(found) == 1, "STATE_NOT_FOUND",
          f"Expected one state {state_tag}; found {len(found)}", offset=obim_offset)
    child = _subchunks(data, found[0].offset, found[0].length)
    smaps = [p for p in child if p.tag == "SMAP"]
    _need(len(smaps) == 1, "SMAP_INVALID",
          f"State {state_tag}: expected exactly one SMAP", offset=found[0].offset)
    rgba, records = _decode_stripmap(data, smaps[0], width=width, height=height,
                                     palette=palette, transparent_color=transparent_color)
    mask_pngs = {}
    for p in child:
        if p.tag.startswith("ZP") and p.tag[2:].isdigit():
            _need(p.tag not in mask_pngs, "ZPLANE_DUPLICATE", "Repeated Z plane tag",
                  offset=p.offset)
            if include_masks:
                plane = _decode_zplane(data, p, width=width, height=height)
                mask_pngs[p.tag] = encode_png(width, height, plane, rgba=False)
    metadata = {"object_id": obj_id, "state_tag": state_tag, "width": width,
                "height": height, "source_offset": found[0].offset,
                "source_length": found[0].length,
                "pixel_rgba_sha256": sha256(rgba).hexdigest(),
                "strip_codecs": records, "zplane_tags": sorted(
                    p.tag for p in child if p.tag.startswith("ZP"))}
    return metadata, encode_png(width, height, rgba, rgba=True), mask_pngs


def export_object_images(input_path: str | Path, output_dir: str | Path, *,
                         room_id: int, object_id: int, include_masks: bool = True) -> dict:
    """Export state images without overwriting files; report every failure."""
    src, dest = Path(input_path), Path(output_dir)
    report = {"schema_version": "0.1", "operation": "export_object_images",
              "status": "failed", "input": str(src), "output_dir": str(dest),
              "selection": {"room_id": room_id, "object_id": object_id,
                            "include_masks": include_masks},
              "files": [], "states": [], "diagnostics": [],
              "summary": {"success": 0, "failed": 0, "skipped": 0, "unsupported": 0},
              "rendering_status": "pixel_decoded_not_compared_to_reference",
              "layering_status": "zplanes_separated_not_composited"}
    def problem(code, message, *, offset=None):
        report["diagnostics"].append({"severity": "error", "code": code,
                                       "message": message, "offset": offset,
                                       "source": str(src), "resource_id": object_id})
    if type(room_id) is not int or not 0 <= room_id <= 255 or (
            type(object_id) is not int or not 0 < object_id <= 65535):
        problem("SELECTION_INVALID", "Room/object IDs outside supported ranges")
        return report
    inventory = inspect(src)
    report["diagnostics"].extend(inventory["diagnostics"])
    if inventory["status"] != "success":
        problem("IMAGE_EXPORT_INSPECTION_FAILED", "Input archive did not pass inspection")
        return report
    scenes = [r for r in inventory["scene_inventory"]["rooms"] if r["room_id"] == room_id]
    matches = [o for scene in scenes for o in scene["objects"]
               if o["object_id"] == object_id and o["image"] is not None]
    if len(matches) != 1:
        problem("OBJECT_NOT_FOUND", f"Room {room_id} has no unique object {object_id}")
        return report
    if dest.is_symlink():
        problem("OUTPUT_SYMLINK_REFUSED", "Output directory may not be a symlink")
        return report
    manifest = dest / "manifest.json"
    if manifest.exists() or manifest.is_symlink():
        problem("MANIFEST_EXISTS", "Existing manifest; refusing overwrite")
        return report
    try:
        index_bytes, raw, index_label, label = _read_pair(src)
    except (InspectionError, OSError, ValueError) as exc:
        problem("IMAGE_EXPORT_INPUT_READ_FAILED", str(exc))
        return report
    if sha256(index_bytes).hexdigest() != inventory["sources"][0]["sha256"]:
        problem("IMAGE_EXPORT_INDEX_CHANGED", "Index file SHA-256 changed after inventory")
        return report
    if sha256(raw).hexdigest() != inventory["sources"][1]["sha256"]:
        problem("IMAGE_EXPORT_SOURCE_CHANGED", "Resource file SHA-256 changed after inventory")
        return report
    decoded = bytes(b ^ XOR_KEY for b in raw)
    chunks_in_room = [r for r in inventory["resources"]["resource_inventory"]
                      if r["room_id"] == room_id]
    def exact_chunk(tag):
        found = [r for r in chunks_in_room if r["tag"] == tag]
        _need(len(found) == 1, f"{tag}_COUNT_INVALID",
              f"Expected exactly one room {tag}; found {len(found)}")
        p = found[0]["offset"]
        return p + 8, found[0]["length"] - 8
    try:
        pal_start, pal_size = exact_chunk("CLUT")
        _need(pal_size >= 768, "CLUT_INVALID", "CLUT has fewer than 256 colors")
        palette = decoded[pal_start:pal_start + 768]
        trans_start, trans_size = exact_chunk("TRNS")
        _need(trans_size >= 1, "TRNS_INVALID", "Missing transparent palette index")
        trans = decoded[trans_start]
        object_offset = matches[0]["image"]["source_offset"]
        children = _subchunks(decoded, object_offset,
                             matches[0]["image"]["byte_length"])
        state_tags = [p.tag for p in children if p.tag.startswith("IM") and p.tag != "IMHD"]
        _need(state_tags and len(state_tags) <= MAX_IMAGE_STATES,
              "IMAGE_COUNT_UNSUPPORTED", "Missing or excessive image states")
        dest.mkdir(parents=True, exist_ok=True)
    except (ImageDecodeError, InspectionError, OSError) as exc:
        code = exc.code if isinstance(exc, (ImageDecodeError, InspectionError)) else "OUTPUT_DIRECTORY_FAILED"
        problem(code, str(exc))
        return report
    report["source"] = {"name": label, "sha256": sha256(raw).hexdigest(),
                         "obim_offset": object_offset, "palette_chunk_offset": pal_start - 8,
                         "transparent_index": trans}
    for tag in state_tags:
        result = {"state_tag": tag, "status": "failed", "image": None, "masks": []}
        report["states"].append(result)
        try:
            meta, image_png, masks = decode_object_state(
                decoded, obim_offset=object_offset, state_tag=tag,
                palette=palette, transparent_color=trans, include_masks=include_masks)
            result["metadata"] = meta
            stem = f"room-{room_id:03d}_object-{object_id:04d}_{tag.lower()}"
            image_path = dest / f"{stem}.png"
            result["image"] = image_path.name
            digest = _write_new_verified(image_path, image_png)
            report["files"].append({"name": image_path.name, "sha256": digest,
                                    "kind": "rgba_state", "state_tag": tag})
            for ztag, content in sorted(masks.items()):
                path = dest / f"{stem}_{ztag.lower()}.png"
                digest = _write_new_verified(path, content)
                result["masks"].append(path.name)
                report["files"].append({"name": path.name, "sha256": digest,
                                        "kind": "separate_depth_mask",
                                        "state_tag": tag, "mask_tag": ztag})
            result["status"] = "success"
        except (ImageDecodeError, InspectionError) as exc:
            problem(exc.code, f"{tag}: {exc}", offset=exc.offset)
            if exc.code == "STRIP_CODEC_UNSUPPORTED":
                report["summary"]["unsupported"] += 1
        except OSError as exc:
            problem("IMAGE_WRITE_FAILED", f"{tag}: {exc}")
        report["summary"][result["status"]] += 1
    ok = report["summary"]["success"]
    fail = report["summary"]["failed"]
    report["status"] = "success" if ok and not fail else "partial" if ok else "failed"
    # A failed write to manifest is never a successful export.
    import json
    try:
        _write_new_verified(manifest, (json.dumps(report, indent=2) + "\n").encode("utf-8"))
    except OSError as exc:
        problem("MANIFEST_WRITE_FAILED", str(exc))
        report["status"] = "partial" if ok else "failed"
    return report
