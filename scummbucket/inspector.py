"""Read-only, bounded inspection of the original DOS Monkey Island 2 SCUMM v5 files.

This is a resource inventory, not an image, animation, audio, or script decoder.
The input format and XOR key are intentionally edition-specific.
"""
from __future__ import annotations

from collections import Counter
from dataclasses import asdict, dataclass
import hashlib
import os
from pathlib import Path
import re
import struct
import zipfile

from .linking import link_index_resources

MAX_FILE_BYTES = 64 * 1024 * 1024
MAX_INPUT_ENTRIES = 4096
MAX_CHUNKS = 100_000
XOR_KEY = 0x69
DIRECTORY_TAGS = ("DROO", "DSCR", "DSOU", "DCOS", "DCHR")


@dataclass(frozen=True)
class Diagnostic:
    severity: str
    code: str
    message: str
    source: str | None = None
    offset: int | None = None
    tag: str | None = None
    resource_id: int | None = None


class InspectionError(Exception):
    def __init__(self, code: str, message: str, source: str | None = None,
                 offset: int | None = None, tag: str | None = None):
        super().__init__(message)
        self.code, self.source, self.offset, self.tag = code, source, offset, tag


@dataclass(frozen=True)
class Chunk:
    tag: str
    offset: int
    length: int

    @property
    def end(self) -> int:
        return self.offset + self.length


def _u16le(data: bytes, offset: int) -> int:
    return struct.unpack_from("<H", data, offset)[0]


def _u16be(data: bytes, offset: int) -> int:
    return struct.unpack_from(">H", data, offset)[0]


def _u32le(data: bytes, offset: int) -> int:
    return struct.unpack_from("<I", data, offset)[0]


def _u32be(data: bytes, offset: int) -> int:
    return struct.unpack_from(">I", data, offset)[0]


def chunks(data: bytes, start: int, end: int, source: str) -> list[Chunk]:
    """Walk a chunk sequence. Chunk sizes include their eight-byte headers."""
    if not (0 <= start <= end <= len(data)):
        raise InspectionError("CHUNK_RANGE_INVALID", "Chunk range exceeds input", source, start)
    results: list[Chunk] = []
    cursor = start
    while cursor < end:
        if end - cursor < 8:
            raise InspectionError("CHUNK_HEADER_TRUNCATED", "Less than eight bytes remain", source, cursor)
        tag_bytes = data[cursor:cursor + 4]
        if not all(48 <= b <= 57 or 65 <= b <= 90 for b in tag_bytes):
            raise InspectionError("CHUNK_TAG_INVALID", "Non-ASCII or invalid chunk tag", source, cursor)
        tag = tag_bytes.decode("ascii")
        size = _u32be(data, cursor + 4)
        if size < 8:
            raise InspectionError("CHUNK_LENGTH_INVALID", "Chunk length smaller than header", source, cursor, tag)
        if size > end - cursor:
            raise InspectionError("CHUNK_OUT_OF_BOUNDS", "Chunk extends beyond parent boundary", source, cursor, tag)
        results.append(Chunk(tag, cursor, size))
        if len(results) > MAX_CHUNKS:
            raise InspectionError("CHUNK_LIMIT_EXCEEDED", "Too many chunks", source, cursor, tag)
        cursor += size
    return results


def _read_pair(path: Path) -> tuple[bytes, bytes, str, str]:
    """Find exactly one same-directory MONKEY2.000/.001 pair; do not trust a ZIP label."""
    if not path.exists():
        raise InspectionError("INPUT_NOT_FOUND", f"Input not found: {path}")
    entries: dict[str, tuple[str, object]] = {}
    if path.is_file() and path.suffix.lower() == ".zip" and not zipfile.is_zipfile(path):
        raise InspectionError("ZIP_INVALID", "Input has ZIP extension but is not a readable ZIP", str(path))
    if path.is_file() and zipfile.is_zipfile(path):
        try:
            with zipfile.ZipFile(path) as archive:
                members = [m for m in archive.infolist() if not m.is_dir()]
                if len(members) > MAX_INPUT_ENTRIES:
                    raise InspectionError("INPUT_ENTRY_LIMIT", "Archive contains too many entries", str(path))
                candidates = []
                for m in members:
                    name = m.filename.replace("\\", "/")
                    base = name.rsplit("/", 1)[-1].upper()
                    if base in ("MONKEY2.000", "MONKEY2.001"):
                        candidates.append((name, m))
                for name, m in candidates:
                    key = name.casefold()
                    if key in entries:
                        raise InspectionError("INPUT_AMBIGUOUS", "Duplicate matching archive member", str(path))
                    entries[key] = (f"{path}!{name}", m)
                pairs = _select_pairs(entries)
                if len(pairs) != 1:
                    raise InspectionError("GAME_PAIR_AMBIGUOUS" if pairs else "GAME_PAIR_NOT_FOUND",
                                          "Expected exactly one matching MONKEY2.000/.001 pair", str(path))
                first, second = pairs[0]
                result = []
                for key in (first, second):
                    label, info = entries[key]
                    if info.file_size > MAX_FILE_BYTES:
                        raise InspectionError("INPUT_TOO_LARGE", "Input member exceeds configured limit", label)
                    result.append((archive.read(info), label))
                return result[0][0], result[1][0], result[0][1], result[1][1]
        except (zipfile.BadZipFile, RuntimeError, EOFError) as exc:
            raise InspectionError("ZIP_READ_FAILED", f"Could not read ZIP: {exc}", str(path)) from exc

    if path.is_file():
        folder = path.parent
        listing = list(folder.iterdir())
        if len(listing) > MAX_INPUT_ENTRIES:
            raise InspectionError("INPUT_ENTRY_LIMIT", "Too many folder entries", str(folder))
        for p in listing:
            if p.is_file() and p.name.upper() in ("MONKEY2.000", "MONKEY2.001"):
                entries[p.name.casefold()] = (str(p), p)
    elif path.is_dir():
        inspected = 0
        for root, dirs, filenames in os.walk(path, followlinks=False):
            dirs[:] = [name for name in dirs if not (Path(root) / name).is_symlink()]
            inspected += len(dirs) + len(filenames)
            if inspected > MAX_INPUT_ENTRIES:
                raise InspectionError("INPUT_ENTRY_LIMIT", "Directory tree too large", str(path))
            for filename in filenames:
                if filename.upper() not in ("MONKEY2.000", "MONKEY2.001"):
                    continue
                p = Path(root) / filename
                if p.is_symlink():
                    continue
                rel = p.relative_to(path).as_posix().casefold()
                entries[rel] = (str(p), p)
    else:
        raise InspectionError("INPUT_TYPE_UNSUPPORTED", "Not a directory, ZIP, or game file", str(path))

    pairs = _select_pairs(entries)
    if len(pairs) != 1:
        raise InspectionError("GAME_PAIR_AMBIGUOUS" if pairs else "GAME_PAIR_NOT_FOUND",
                              "Expected exactly one matching MONKEY2.000/.001 pair", str(path))
    result = []
    for key in pairs[0]:
        label, p = entries[key]
        if p.stat().st_size > MAX_FILE_BYTES:
            raise InspectionError("INPUT_TOO_LARGE", "Input file exceeds configured limit", label)
        result.append((p.read_bytes(), label))
    return result[0][0], result[1][0], result[0][1], result[1][1]


def _select_pairs(entries: dict[str, tuple[str, object]]) -> list[tuple[str, str]]:
    pairs = []
    for name in entries:
        if name.endswith("monkey2.000"):
            sibling = name[:-3] + "001"
            if sibling in entries:
                pairs.append((name, sibling))
    return pairs


def _parse_index(data: bytes, source: str) -> tuple[dict, list[Chunk]]:
    top = chunks(data, 0, len(data), source)
    index: dict = {}
    seen = set()
    for c in top:
        if c.tag in seen:
            raise InspectionError("INDEX_TAG_DUPLICATE", "Repeated index chunk", source, c.offset, c.tag)
        seen.add(c.tag)
        if c.tag in DIRECTORY_TAGS:
            if c.length < 10:
                raise InspectionError("DIRECTORY_TRUNCATED", "Missing resource count", source, c.offset, c.tag)
            number = _u16le(data, c.offset + 8)
            if c.length != 10 + 5 * number:
                raise InspectionError("DIRECTORY_LENGTH_INVALID", "Directory count does not match chunk size", source, c.offset, c.tag)
            start = c.offset + 10
            roomnos = data[start:start + number]
            offsets = [_u32le(data, start + number + i * 4) for i in range(number)]
            index[c.tag] = {"slots": number, "offsets_not_sentinel": sum(x != 0xFFFFFFFF for x in offsets),
                            "resource_locations": [{"id": i, "room_number": roomnos[i], "offset": offsets[i]}
                                                   for i in range(number)]}
        elif c.tag == "DOBJ":
            if c.length < 10:
                raise InspectionError("OBJECT_INDEX_TRUNCATED", "Missing object count", source, c.offset, c.tag)
            number = _u16le(data, c.offset + 8)
            if c.length != 10 + 5 * number:
                raise InspectionError("OBJECT_INDEX_LENGTH_INVALID", "DOBJ count does not match size", source, c.offset, c.tag)
            index[c.tag] = {"global_object_slots": number}
        else:
            index[c.tag] = {"size": c.length, "offset": c.offset}
    for required in ("DROO", "DSCR", "DSOU", "DCOS", "DCHR", "DOBJ", "MAXS", "RNAM"):
        if required not in seen:
            raise InspectionError("INDEX_TAG_MISSING", f"Missing index chunk {required}", source)
    return index, top


def _parse_cycles(data: bytes, c: Chunk, source: str, room_id: int,
                  diagnostics: list[Diagnostic]) -> list[dict]:
    pos, end, cycles = c.offset + 8, c.end, []
    found_end = False
    while pos < end:
        record_offset = pos
        number = data[pos]
        pos += 1
        if number == 0:
            found_end = True
            break
        if pos + 8 > end:
            raise InspectionError("CYCLE_TRUNCATED", "Palette cycle record truncated", source, record_offset, c.tag)
        rate = _u16be(data, pos + 2)
        flags = _u16be(data, pos + 4)
        start, finish = data[pos + 6], data[pos + 7]
        if not 1 <= number <= 16 or start > finish or rate == 0:
            diagnostics.append(Diagnostic("warning", "CYCLE_FIELDS_SUSPICIOUS",
                                          f"Cycle id={number}, rate={rate}, colors={start}-{finish}",
                                          source, record_offset, "CYCL", room_id))
        if flags & ~0x0003:
            diagnostics.append(Diagnostic("warning", "CYCLE_FLAGS_UNVERIFIED",
                                          f"Cycle flags 0x{flags:04X} need interpretation", source,
                                          record_offset, "CYCL", room_id))
        if rate > 16384:
            diagnostics.append(Diagnostic(
                "warning", "CYCLE_DELAY_ZERO_IN_ENGINE",
                f"Cycle id={number} rate={rate} produces zero delay "
                "(16384 // rate); ScummVM skips this cycle while delay is zero",
                source, record_offset, "CYCL", room_id))
        cycles.append({"id": number, "reserved_bytes_hex": data[pos:pos + 2].hex(),
                       "rate_raw": rate, "flags": flags,
                       "start_color": start, "end_color": finish, "offset": record_offset})
        pos += 8
        if len(cycles) > 16:
            diagnostics.append(Diagnostic("warning", "CYCLE_COUNT_UNUSUAL", "More than 16 cycle records", source,
                                          record_offset, "CYCL", room_id))
    if not found_end:
        raise InspectionError("CYCLE_TERMINATOR_MISSING", "CYCL has no zero terminator", source, c.offset, "CYCL")
    # Some original rooms pad CYCL chunks with an extra zero byte. This is
    # harmless alignment data, not an error. Non-zero suffixes remain visible.
    if any(data[pos:end]):
        diagnostics.append(Diagnostic("warning", "CYCLE_TRAILING_BYTES", "Non-zero bytes after cycle terminator", source,
                                      pos, "CYCL", room_id))
    return cycles


def _parse_resource(data: bytes, source: str, diagnostics: list[Diagnostic]) -> dict:
    top = chunks(data, 0, len(data), source)
    if len(top) != 1 or top[0].tag != "LECF":
        raise InspectionError("RESOURCE_HEADER_UNSUPPORTED", "Expected one LECF chunk", source, 0)
    children = chunks(data, 8, top[0].end, source)
    loffs = [c for c in children if c.tag == "LOFF"]
    bundles = [c for c in children if c.tag == "LFLF"]
    unknown = [c.tag for c in children if c.tag not in ("LOFF", "LFLF")]
    if unknown:
        diagnostics.append(Diagnostic("warning", "RESOURCE_CHILD_UNKNOWN", f"Unknown LECF children: {unknown}", source))
    if len(loffs) != 1:
        raise InspectionError("LOFF_COUNT_INVALID", "Exactly one LOFF required", source)
    loff = loffs[0]
    if loff.length < 9:
        raise InspectionError("LOFF_TRUNCATED", "LOFF record count is missing", source, loff.offset, "LOFF")
    count = data[loff.offset + 8]
    if loff.length != 9 + count * 5:
        raise InspectionError("LOFF_LENGTH_INVALID", "LOFF record count doesn't match size", source, loff.offset, "LOFF")
    room_lookup = {}
    seen_offsets = set()
    for i in range(count):
        at = loff.offset + 9 + i * 5
        room_id, target = data[at], _u32le(data, at + 1)
        if room_id in room_lookup:
            raise InspectionError("LOFF_ROOM_DUPLICATE", f"Duplicate room {room_id}", source, at, "LOFF")
        if target in seen_offsets:
            raise InspectionError("LOFF_OFFSET_DUPLICATE", f"Duplicate room target {target}", source, at, "LOFF")
        room_lookup[room_id] = target
        seen_offsets.add(target)
    if len(room_lookup) != len(bundles):
        raise InspectionError("LOFF_BUNDLE_COUNT_MISMATCH", "Room offsets differ from LFLF count", source)
    room_starts = {b.offset + 8: b for b in bundles}
    for room_id, target in room_lookup.items():
        if target not in room_starts:
            raise InspectionError("LOFF_TARGET_INVALID", f"Room {room_id} offset {target} is not LFLF+8", source,
                                  target, "LOFF")
        if data[target:target + 4] != b"ROOM":
            raise InspectionError("LOFF_TARGET_NOT_ROOM", f"Room {room_id} does not point to ROOM", source,
                                  target, "LOFF")

    id_by_start = {v: k for k, v in room_lookup.items()}
    counts: Counter = Counter()
    rooms = []
    inventory = []
    for bundle in bundles:
        room_id = id_by_start[bundle.offset + 8]
        contents = chunks(data, bundle.offset + 8, bundle.end, source)
        if not contents or contents[0].tag != "ROOM":
            raise InspectionError("ROOM_CHUNK_MISSING", f"Room {room_id} has no ROOM chunk", source, bundle.offset)
        room_chunk = contents[0]
        room_kids = chunks(data, room_chunk.offset + 8, room_chunk.end, source)
        per_room = Counter()
        cycles = []
        multi_state = 0
        for chunk in contents:
            if chunk.tag != "ROOM":
                counts[chunk.tag] += 1
                inventory.append({"tag": chunk.tag, "offset": chunk.offset, "length": chunk.length,
                                  "room_id": room_id, "scope": "bundle"})
        for c in room_kids:
            counts[c.tag] += 1
            per_room[c.tag] += 1
            entry = {"tag": c.tag, "offset": c.offset, "length": c.length,
                     "room_id": room_id, "scope": "room"}
            if c.tag == "CYCL":
                cycles = _parse_cycles(data, c, source, room_id, diagnostics)
                entry["palette_cycles"] = cycles
            if c.tag == "OBIM":
                inside = chunks(data, c.offset + 8, c.end, source)
                states = [p.tag for p in inside if re.fullmatch(r"IM[0-9A-F]{2}", p.tag) and p.tag != "IMHD"]
                entry["image_states"] = states
                if len(states) >= 2:
                    multi_state += 1
                if "IMHD" not in [p.tag for p in inside]:
                    diagnostics.append(Diagnostic("warning", "OBJECT_IMAGE_HEADER_MISSING",
                                                  "OBIM missing IMHD", source, c.offset, c.tag, room_id))
            inventory.append(entry)
        rooms.append({"id": room_id, "room_offset": room_chunk.offset, "room_size": room_chunk.length,
                      "chunk_counts": dict(per_room), "palette_cycles": cycles,
                      "multistate_object_images": multi_state})
    rooms.sort(key=lambda r: r["id"])
    return {"room_count": len(rooms), "rooms": rooms, "resource_counts": dict(sorted(counts.items())),
            "cycle_count": sum(len(r["palette_cycles"]) for r in rooms),
            "rooms_with_cycles": sum(bool(r["palette_cycles"]) for r in rooms),
            "multistate_object_images": sum(r["multistate_object_images"] for r in rooms),
            "resource_inventory": inventory}


def inspect(path: str | Path) -> dict:
    """Return a JSON-serializable report. Never conceal or discard failures."""
    path = Path(path)
    report = {"schema_version": "0.1", "status": "failed", "detected_game": None,
              "input": str(path), "sources": [], "index": {}, "resources": {},
              "directory_links": {}, "scene_inventory": {}, "diagnostics": []}
    diagnostics: list[Diagnostic] = []
    try:
        left, right, label0, label1 = _read_pair(path)
        for b, label in ((left, label0), (right, label1)):
            report["sources"].append({"label": label, "size": len(b),
                                      "sha256": hashlib.sha256(b).hexdigest(), "xor_key": "0x69"})
        decoded0 = bytes(x ^ XOR_KEY for x in left)
        decoded1 = bytes(x ^ XOR_KEY for x in right)
        if decoded0[:4] != b"RNAM" or decoded1[:4] != b"LECF":
            raise InspectionError("GAME_SIGNATURE_UNSUPPORTED",
                                  "Expected XOR-0x69 SCUMM v5 RNAM/LECF pair", str(path))
        report["index"], _ = _parse_index(decoded0, label0)
        report["resources"] = _parse_resource(decoded1, label1, diagnostics)
        report["directory_links"], link_diagnostics = link_index_resources(
            report["index"], report["resources"], source=label1)
        diagnostics.extend(Diagnostic(**detail) for detail in link_diagnostics)
        # Local import avoids circular import with scene_inventory's reuse of chunks().
        from .scene_inventory import build_scene_inventory
        report["scene_inventory"], scene_diagnostics = build_scene_inventory(
            decoded1, report["resources"], report["directory_links"], source=label1)
        diagnostics.extend(Diagnostic(**detail) for detail in scene_diagnostics)
        report["detected_game"] = {"id": "monkey2", "format": "SCUMM v5-style DOS",
                                   "edition_confidence": "structural; exact retail edition unverified"}
        report["status"] = ("partial" if any(d.severity in ("error", "fatal") for d in diagnostics)
                            else "success")
    except InspectionError as exc:
        diagnostics.append(Diagnostic("error", exc.code, str(exc), exc.source, exc.offset, exc.tag))
    except (OSError, ValueError, struct.error, zipfile.BadZipFile) as exc:
        diagnostics.append(Diagnostic("error", "INPUT_OR_PARSE_FAILED", f"{type(exc).__name__}: {exc}", str(path)))
    report["diagnostics"] = [asdict(d) for d in diagnostics]
    report["diagnostic_counts"] = dict(Counter(d.severity for d in diagnostics))
    return report
