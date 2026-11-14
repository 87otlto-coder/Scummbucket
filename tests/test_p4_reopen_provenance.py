"""Synthetic-only regression: all P4 exports reject a changed index on reopen.

Never writes an original SCUMM archive or requires a private game fixture.
"""
import hashlib
from importlib.util import find_spec
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from scummbucket.inspector import _read_pair
from scummbucket.palette_probe import palette_probe
from scummbucket.palette_sequence import export_palette_sequence
from scummbucket.palette_events import export_palette_events
from scummbucket.palette_coverage import export_cycle_coverage
from scummbucket.palette_gif import export_palette_gif
from test_inspector import index, resource, make_zip


class PaletteSourceReopenTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.archive = self.root / "synthetic-game.zip"
        make_zip(self.archive, a=index(), b=resource(multiple_states=True))
        first, second, index_name, resource_name = _read_pair(self.archive)
        self.original_zip_sha256 = hashlib.sha256(self.archive.read_bytes()).hexdigest()
        self.changed_index_only = (bytes([first[0] ^ 1]) + first[1:],
                                   second, index_name, resource_name)

    def assert_no_output_on_changed_index(self, module_path, target, operation, code):
        with patch(f"scummbucket.{module_path}._read_pair", return_value=self.changed_index_only):
            report = operation()
        self.assertEqual(report["status"], "failed", report["diagnostics"])
        self.assertIn(code, [d["code"] for d in report["diagnostics"]])
        self.assertFalse(target.exists(), "No export should be written using stale index metadata")
        self.assertEqual(hashlib.sha256(self.archive.read_bytes()).hexdigest(),
                         self.original_zip_sha256)

    def test_palette_probe_rejects_changed_index(self):
        output = self.root / "probe"
        self.assert_no_output_on_changed_index(
            "palette_probe", output,
            lambda: palette_probe(self.archive, output, room_id=1, ticks=[0]),
            "SOURCE_CHANGED")

    def test_palette_sequence_rejects_changed_index(self):
        output = self.root / "sequence"
        self.assert_no_output_on_changed_index(
            "palette_sequence", output,
            lambda: export_palette_sequence(self.archive, output, room_id=1, fps=1,
                                            duration_seconds=1),
            "SEQUENCE_SOURCE_CHANGED")

    def test_palette_events_rejects_changed_index(self):
        output = self.root / "events"
        self.assert_no_output_on_changed_index(
            "palette_events", output,
            lambda: export_palette_events(self.archive, output, room_id=1,
                                          duration_seconds=1),
            "EVENT_SOURCE_CHANGED")

    def test_palette_coverage_rejects_changed_index(self):
        output = self.root / "coverage"
        self.assert_no_output_on_changed_index(
            "palette_coverage", output,
            lambda: export_cycle_coverage(self.archive, output, room_id=1),
            "COVERAGE_SOURCE_CHANGED")

    @unittest.skipUnless(find_spec("PIL") is not None, "Pillow optional dependency absent")
    def test_palette_gif_rejects_changed_index(self):
        output = self.root / "palette.gif"
        self.assert_no_output_on_changed_index(
            "palette_gif", output,
            lambda: export_palette_gif(self.archive, output, room_id=1, fps=1,
                                       duration_seconds=1),
            "GIF_SOURCE_CHANGED")


if __name__ == "__main__":
    unittest.main()
