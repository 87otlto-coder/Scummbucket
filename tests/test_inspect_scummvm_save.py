"""Synthetic saved-game inspection CLI tests, no original game files."""
from pathlib import Path
import tempfile
import unittest

from scummbucket.scummvm_save import SaveFormatError
from tools.inspect_scummvm_save import inspect, main
from fixture_scummvm_save import synthetic_scummvm_save


class SaveInspectorCliTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.path = Path(self.tmp.name) / "monkey2.s01"

    def test_room7_inspection_read_only(self):
        data = synthetic_scummvm_save(room=7)
        self.path.write_bytes(data)
        result = inspect(self.path, require_room=7)
        self.assertEqual(result["state"]["current_room"], 7)
        self.assertEqual(result["state"]["room_resource"], 7)
        self.assertEqual(result["state"]["container"], "gzip")
        self.assertFalse(result["gameplay_entry_verified"])
        self.assertEqual(self.path.read_bytes(), data)
        self.assertEqual(set(self.path.parent.iterdir()), {self.path})

    def test_wrong_room_causes_explicit_error(self):
        self.path.write_bytes(synthetic_scummvm_save(room=23))
        with self.assertRaisesRegex(SaveFormatError, "not required Room 7"):
            inspect(self.path, require_room=7)

    def test_dos_save_refused_without_output(self):
        self.path.write_bytes(b"123\x00" + bytes(100))
        with self.assertRaisesRegex(SaveFormatError, "original DOS SAVEGAME"):
            inspect(self.path, require_room=7)

    def test_cli_exit_2_for_wrong_room_and_no_report_written(self):
        self.path.write_bytes(synthetic_scummvm_save(room=23))
        with self.assertRaises(SystemExit) as error:
            main([str(self.path), "--require-room", "7"])
        self.assertEqual(error.exception.code, 2)
        self.assertEqual(set(self.path.parent.iterdir()), {self.path})


if __name__ == "__main__":
    unittest.main()
