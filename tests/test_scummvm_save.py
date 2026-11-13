"""Synthetic tests for gzip-wrapped ScummVM saved-room inspection."""
from pathlib import Path
import struct
import tempfile
import unittest

from scummbucket.scummvm_save import inspect_scummvm_save, SaveFormatError
from fixture_scummvm_save import synthetic_scummvm_save


class ScummvmSaveTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.path = Path(self.tmp.name) / "monkey2.s01"

    def parse(self, payload):
        self.path.write_bytes(payload)
        result = inspect_scummvm_save(self.path)
        self.assertEqual(self.path.read_bytes(), payload)
        return result

    def test_realistic_gzip_room7(self):
        value = self.parse(synthetic_scummvm_save(room=7))
        self.assertEqual((value["current_room"], value["room_resource"]), (7, 7))
        self.assertEqual((value["container"], value["save_version"]), ("gzip", 124))

    def test_raw_room23(self):
        value = self.parse(synthetic_scummvm_save(room=23, compressed=False))
        self.assertEqual(value["current_room"], 23)
        self.assertEqual(value["container"], "none")

    def test_dos_save_rejected(self):
        self.path.write_bytes(b"123\0" + bytes(40))
        with self.assertRaisesRegex(SaveFormatError, "original DOS SAVEGAME"):
            inspect_scummvm_save(self.path)

    def test_malformed_gzip_rejected(self):
        self.path.write_bytes(b"\x1f\x8b\x08\x00" + bytes(20))
        with self.assertRaisesRegex(SaveFormatError, "Invalid or truncated"):
            inspect_scummvm_save(self.path)

    def test_unsupported_version_rejected(self):
        raw = bytearray(synthetic_scummvm_save(compressed=False))
        struct.pack_into("<I", raw, 8, 123)
        self.path.write_bytes(raw)
        with self.assertRaisesRegex(SaveFormatError, "requires 124"):
            inspect_scummvm_save(self.path)

    def test_truncated_thumbnail_rejected(self):
        self.path.write_bytes(synthetic_scummvm_save(compressed=False)[:48])
        with self.assertRaisesRegex(SaveFormatError, "Truncated or invalid"):
            inspect_scummvm_save(self.path)

    def test_corrupt_info_rejected(self):
        raw = bytearray(synthetic_scummvm_save(compressed=False))
        raw[52:56] = b"FAIL"
        self.path.write_bytes(raw)
        with self.assertRaisesRegex(SaveFormatError, "INFO section"):
            inspect_scummvm_save(self.path)

    def test_saved_room_field_is_not_guessed(self):
        raw = bytearray(synthetic_scummvm_save(room=7, compressed=False))
        # 44 header + 8 thumbnail + 26 INFO + 16 MD5 + 1 palette.
        raw[95] = 23
        value = self.parse(raw)
        self.assertEqual(value["current_room"], 23)
        self.assertEqual(value["room_resource"], 7)
