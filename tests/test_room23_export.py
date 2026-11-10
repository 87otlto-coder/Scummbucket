"""Public synthetic replay and optional private end-to-end PNG checks."""
from hashlib import sha256
from importlib.util import find_spec
import json
import os
from pathlib import Path
import tempfile
import unittest

from scummbucket.room23_capture_research import parse_room23_hook_log
from scummbucket.room23_export import INDEX_SHA, export_room23, verified_frames


class ExportTest(unittest.TestCase):
    def setUp(self):
        source = bytes(range(256)) * 3
        begin = bytearray(source)
        begin[0:3] = b"abc"
        self.bg = {"width": 2, "height": 1, "indexed_pixels": bytes([0, 1]), "initial_palette": source}
        self.records = [dict(id=1, start_color=1, end_color=2, flags=0, rate_raw=16384, offset=0)]
        swapped = bytearray(begin)
        swapped[3:9] = begin[6:9] + begin[3:6]
        self.capture = {"initial_palette": bytes(begin), "begin_millis": 7, "samples": [
            dict(sequence=i+1, var_timer=1, var_timer_next=1, millis=t, palette=bytes(p))
            for i, (t, p) in enumerate(zip((9, 9, 13009), (swapped, begin, swapped)))]}
        self.comparison = {"continuous_scheduler": {"status": "matched", "first_sample_equivalent_model_update": 1}}

    def frames(self):
        return list(verified_frames(self.bg, self.records, self.capture, self.comparison))

    def test_duplicate_clock_long_gap_and_unknown_tail(self):
        frames = self.frames()
        self.assertEqual([r["until_next_ms"] for _, r in frames], [0, 13000, None])
        self.assertEqual([r["offset_ms"] for _, r in frames], [2, 2, 13002])
        self.assertEqual(frames[0][0], frames[2][0])
        for (png, row), observed in zip(frames, self.capture["samples"]):
            self.assertEqual(row["palette_sha256"], sha256(observed["palette"]).hexdigest())
            self.assertEqual(row["png_sha256"], sha256(png).hexdigest())

    def test_does_not_copy_observed_samples(self):
        self.capture["samples"][0]["palette"] = bytes(768)
        with self.assertRaisesRegex(ValueError, "sample 1"):
            self.frames()

    def test_unresolved_phase_and_no_holdout_refused(self):
        for status in ("phase_unresolved", "no_holdout", "mismatch"):
            self.comparison["continuous_scheduler"]["status"] = status
            with self.assertRaisesRegex(ValueError, "holdout"):
                self.frames()


@unittest.skipUnless(os.getenv("SCUMMBUCKET_ROOM23_MIXED_LOG") and os.getenv("SCUMMBUCKET_MI2_GAME")
                     and find_spec("PIL"), "Private mixed trace, game and Pillow required")
class PrivateExportTest(unittest.TestCase):
    def test_all_exported_pngs_against_original_observations(self):
        from PIL import Image

        game = os.environ["SCUMMBUCKET_MI2_GAME"]
        log = Path(os.environ["SCUMMBUCKET_ROOM23_MIXED_LOG"])
        capture = parse_room23_hook_log(log.read_bytes())
        with tempfile.TemporaryDirectory() as folder:
            dest = Path(folder) / "export"
            export_room23(game, log, dest)
            manifest = json.loads((dest / "manifest.json").read_text())
            self.assertEqual(len(manifest["frames"]), 87)
            self.assertEqual(manifest["heldout_matches"], 84)
            self.assertFalse(manifest["capture_complete"])
            for f, row in zip(manifest["frames"], capture["samples"]):
                self.assertEqual(f["millis"], row["millis"])
                with Image.open(dest / f["file"]) as im:
                    self.assertEqual((im.mode, im.size), ("P", (320, 144)))
                    self.assertEqual(sha256(im.tobytes()).hexdigest(), INDEX_SHA)
                    self.assertEqual(bytes(im.getpalette()), row["palette"])
            with self.assertRaises(FileExistsError):
                export_room23(game, log, dest)
