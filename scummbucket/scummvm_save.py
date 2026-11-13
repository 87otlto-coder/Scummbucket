"""Bounded read-only ScummVM SCUMM v124 save metadata inspection.

ScummVM .s01 files are often gzip-wrapped: SCVM begins after decompression.
The exact v124 THMB/INFO and serializer offsets are derived from upstream
engines/scumm/saveload.cpp. This does not load or execute a saved game.
"""
import gzip
from pathlib import Path
import struct
import zlib

MAX_SAVE_BYTES = 8 * 1024 * 1024


class SaveFormatError(ValueError):
    """Unsupported, malformed or truncated save."""


def inspect_scummvm_save(path):
    path = Path(path)
    with path.open("rb") as stream:
        prefix = stream.read(2)
        stream.seek(0)
        if prefix == b"\x1f\x8b":
            try:
                with gzip.GzipFile(fileobj=stream, mode="rb") as compressed:
                    raw = compressed.read(MAX_SAVE_BYTES + 1)
            except (OSError, EOFError, zlib.error) as exc:
                raise SaveFormatError("Invalid or truncated gzip ScummVM save") from exc
            container = "gzip"
        else:
            raw = stream.read(MAX_SAVE_BYTES + 1)
            container = "none"
    if len(raw) > MAX_SAVE_BYTES:
        raise SaveFormatError("ScummVM save exceeds 8 MiB inspection limit")
    if len(raw) < 44 or raw[:4] != b"SCVM":
        raise SaveFormatError("Not a ScummVM SCVM save; original DOS SAVEGAME.001 is incompatible")
    version = struct.unpack_from("<I", raw, 8)[0]
    if version != 124:
        raise SaveFormatError(f"Unsupported ScummVM save version {version}; pinned parser requires 124")
    name = raw[12:44].split(b"\x00", 1)[0].decode("utf-8", "replace")
    if raw[44:48] != b"THMB":
        raise SaveFormatError("Expected v124 THMB section at offset 44")
    if len(raw) < 52:
        raise SaveFormatError("Truncated or invalid thumbnail/serialized state")
    thumb_size = struct.unpack_from(">I", raw, 48)[0]
    if thumb_size < 8 or 44 + thumb_size + 26 + 21 > len(raw):
        raise SaveFormatError("Truncated or invalid thumbnail/serialized state")
    info = 44 + thumb_size
    if raw[info:info+4] != b"INFO":
        raise SaveFormatError("Missing post-thumbnail INFO section")
    info_version, info_size = struct.unpack_from(">II", raw, info+4)
    if (info_version, info_size) != (2, 26):
        raise SaveFormatError("Unexpected v124 INFO metadata layout")
    offset = info + info_size
    game_md5 = raw[offset:offset+16]
    palette, room, resource, objects, script = raw[offset+16:offset+21]
    return {
        "container": container, "save_version": version,
        "description": name, "game_md5": game_md5.hex(),
        "current_room": room, "room_resource": resource,
        "objects_in_room": objects, "current_script": script,
        "palette_index": palette,
    }
