"""Locate and decode SCUMM v124 palette-cycle counters from saved game data.

ScummVM engines/scumm/saveload.cpp serializes exactly 16 ColorCycle objects
with fields <Uint16LE delay, Uint16LE counter, Uint16LE flags, Byte start,
Byte end>. We locate the entire 128-byte block by matching independent,
archive-decoded CYCL definitions, not by relying on a fragile fixed offset.

Bounded/read-only and edition-limited; does not load a game or attest that a
saved counter equals the counter at the first captured runtime frame.
"""
import gzip
import hashlib
from pathlib import Path
import struct
import zlib

from .palette_probe import prepare_cycles
from .scummvm_save import inspect_scummvm_save, SaveFormatError, MAX_SAVE_BYTES

COLOR_CYCLE_COUNT = 16
COLOR_CYCLE_RECORD_SIZE = 8
COLOR_CYCLE_STRUCT = struct.Struct("<HHHBB")


def _payload(path):
    path = Path(path)
    with path.open("rb") as stream:
        prefix = stream.read(2)
        stream.seek(0)
        if prefix == b"\x1f\x8b":
            try:
                with gzip.GzipFile(fileobj=stream, mode="rb") as compressed:
                    raw = compressed.read(MAX_SAVE_BYTES + 1)
            except (OSError, EOFError, zlib.error) as exc:
                raise SaveFormatError("Invalid gzip ScummVM save payload") from exc
        else:
            raw = stream.read(MAX_SAVE_BYTES + 1)
    if len(raw) > MAX_SAVE_BYTES:
        raise SaveFormatError("ScummVM save exceeds bounded inspection limit")
    return raw


def inspect_scummvm_color_cycles(path, archive_cycle_records):
    """Return a unique, source-format-checked 16-slot cycle block.

    Only the supplied archive cycle definition is authoritative for locating
    active slots. Inactive slots must be all zero. Refuse missing, duplicated,
    contradictory or unsupported structures rather than guessing offsets.
    """
    save = inspect_scummvm_save(path)
    records, warnings = prepare_cycles(archive_cycle_records)
    if warnings or not records:
        raise SaveFormatError(f"Unsupported palette cycle definitions: {warnings}")
    definitions = {}
    for cycle in records:
        cid = cycle["id"]
        delay = cycle["delay_counter_units"]
        if not (1 <= cid <= COLOR_CYCLE_COUNT and 0 < delay <= 65535):
            raise SaveFormatError(f"Unsupported cycle ID or delay: {cid}/{delay}")
        definitions[cid] = (
            delay,
            cycle["flags_raw"],
            cycle["start_color"],
            cycle["end_color"],
        )
    raw = _payload(path)
    first_id = min(definitions)
    anchor = struct.pack("<H", definitions[first_id][0])
    matches = []
    offset = 0
    size = COLOR_CYCLE_COUNT * COLOR_CYCLE_RECORD_SIZE
    while True:
        position = raw.find(anchor, offset)
        if position == -1:
            break
        offset = position + 1
        start = position - COLOR_CYCLE_RECORD_SIZE * (first_id - 1)
        if start < 0 or start + size > len(raw):
            continue
        slots = [COLOR_CYCLE_STRUCT.unpack_from(
            raw, start + index * COLOR_CYCLE_RECORD_SIZE)
            for index in range(COLOR_CYCLE_COUNT)]
        consistent = True
        for cid, (delay, counter, flags, first, last) in enumerate(slots, 1):
            if cid in definitions:
                if (delay, flags, first, last) != definitions[cid]:
                    consistent = False
                    break
            elif (delay, counter, flags, first, last) != (0, 0, 0, 0, 0):
                consistent = False
                break
        if consistent:
            matches.append((start, slots))
        if len(matches) > 1:
            break
    if not matches:
        raise SaveFormatError(
            "No source-anchored 16-slot ColorCycle block in ScummVM save"
        )
    if len(matches) != 1:
        raise SaveFormatError(
            "Ambiguous ColorCycle blocks in ScummVM save; refusing guess"
        )
    start, slots = matches[0]
    cycle_rows = []
    for cid in sorted(definitions):
        delay, counter, flags, first, last = slots[cid - 1]
        cycle_rows.append({
            "id": cid, "delay_counter_units": delay,
            "saved_counter": counter,
            "counter_in_normalized_range": 0 <= counter < delay,
            "flags_raw": flags, "start_color": first, "end_color": last,
        })
    return {
        "schema": "scummvm-v124-color-cycle-save/1",
        "save_version": save["save_version"],
        "saved_room": save["current_room"],
        "saved_room_resource": save["room_resource"],
        "layout": "16 ColorCycle structs of 8 bytes, Uint16LE x3 + Byte x2",
        "decompressed_block_offset": start,
        "block_sha256": hashlib.sha256(raw[start:start + size]).hexdigest(),
        "active_cycle_count": len(cycle_rows),
        "inactive_slots_all_zero": True,
        "cycles": cycle_rows,
        "saved_counter_evidence": "direct_decoding_of_scummvm_save",
        "first_engine_frame_counter_verified": False,
    }
