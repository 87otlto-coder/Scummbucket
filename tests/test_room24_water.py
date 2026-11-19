import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from scummbucket.room24_water import choose_nonrepeating, export_room24


class Room24WaterTests(unittest.TestCase):
    def test_rejected_candidates_are_visible(self):
        self.assertEqual(list(choose_nonrepeating([1, 1, 3, 3, 1], (1, 2, 3))),
                         [(1, True), (1, False), (3, True), (3, False), (1, True)])
        with self.assertRaises(ValueError):
            list(choose_nonrepeating([True], (1, 2, 3)))

    def test_synthetic_raster_manifest_is_reproducible_and_exclusive(self):
        cycles = [dict(id=1, rate_raw=8192, flags=0, start_color=0, end_color=1, offset=0)]
        background = dict(width=2, height=1, indexed_pixels=b"\x09\x09",
                          initial_palette=bytes([1, 2, 3, 4, 5, 6]) + bytes(762), source={})
        room = dict(palette_cycles=cycles)
        with (tempfile.TemporaryDirectory() as tmp,
              patch("scummbucket.room24_water.load_room24",
                    return_value=({}, room, b"", background, {246: {}}, 0)),
              patch("scummbucket.room24_water.authored_position", return_value=(1, 0, 32)),
              patch("scummbucket.room24_water.decode_layer",
                    side_effect=lambda data, obj, state, trns:
                    (dict(width=1, height=1), bytes([state]), b"\xff", {}))):
            first, second = Path(tmp) / "first", Path(tmp) / "second"
            export_room24(None, first, [1, 1, 2], [1, 1])
            export_room24(None, second, [1, 1, 2], [1, 1])
            manifest = (first / "manifest.json").read_bytes()
            self.assertEqual(manifest, (second / "manifest.json").read_bytes())
            events = [row for row in json.loads(manifest)["events"] if row["kind"] == "random_choice"]
            self.assertEqual([row["payload"]["accepted"] for row in events], [True, False, True])
            self.assertEqual((first / "sample-0001.indices").read_bytes(), b"\x09\x01")
            self.assertEqual((first / "sample-0002.indices").read_bytes(), b"\x09\x02")
            self.assertEqual((first / "sample-0002.rgb").read_bytes()[:6], bytes([4, 5, 6, 1, 2, 3]))
            with self.assertRaises(FileExistsError):
                export_room24(None, first, [1, 1, 2], [1, 1])
