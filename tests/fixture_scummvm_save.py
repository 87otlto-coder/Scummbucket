"""Source-free v124 save builder for unit tests only."""
import gzip
import struct


def synthetic_scummvm_save(*, room=7, compressed=True):
    header = (b"SCVM" + bytes(4) + struct.pack("<I", 124)
              + b"synthetic".ljust(32, b"\x00"))
    thumbnail = b"THMB" + struct.pack(">I", 8)
    info = b"INFO" + struct.pack(">II", 2, 26) + bytes(14)
    body = bytes(16) + bytes((0, room, room, 3, 255)) + bytes(64)
    value = header + thumbnail + info + body
    return gzip.compress(value, mtime=0) if compressed else value
