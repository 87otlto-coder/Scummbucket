import os
from pathlib import Path
import unittest

try:
    import PIL
except ImportError:
    raise unittest.SkipTest("frame diagnostics require Pillow")

from tools.compare_room23_frames import compare, engine, present, rgb_errors, rgb_image


class FrameReferenceTests(unittest.TestCase):
    def test_planes_have_distinct_boundaries(self):
        fields = b"R23E1 4 1299 6 6 0 3 1 0 0\nv\nactor 1 2 3 1 1 1 2 0\nDATA\n"
        planes = [bytes([i]) * n for i, n in enumerate([768]*4 + [46080]*2 + [5760]*3 + [64000])]
        data = fields + b"".join(planes)
        meta, palette, bg, front, screen = engine(data, 4)
        self.assertEqual(meta["mask_count"], 3)
        self.assertEqual((palette, bg, front, screen), (planes[:4], planes[4], planes[5], planes[-1]))
        for invalid, seq in ((data[:-1], 4), (data+b"\0", 4), (data, 3)):
            with self.assertRaises(ValueError):
                engine(invalid, seq)

    def test_display_validates_id_and_exact_rgb_size(self):
        data = b"R23D1 2 1300 2 1 software\n\x01\x02\x03\x03\x02\x01"
        _, _, actual = present(data, 2)
        expected = rgb_image((2, 1), b"\0\0", b"\1\2\3" * 256)
        self.assertEqual(rgb_errors(actual, expected), 1)
        for raw, seq in ((data[:-1], 2), (data, 1)):
            with self.assertRaises(ValueError):
                present(raw, seq)

    @unittest.skipUnless(os.getenv("SCUMMBUCKET_REFERENCE_CAPTURE") and os.getenv("SCUMMBUCKET_NATIVE_EXPORT"),
                         "set private frame-reference and export paths")
    def test_recorded_room23_reference(self):
        report = compare(Path(os.environ["SCUMMBUCKET_REFERENCE_CAPTURE"]),
                         Path(os.environ["SCUMMBUCKET_NATIVE_EXPORT"]))
        frames = report["frames"]
        self.assertEqual(len(frames), 87)
        self.assertTrue(all(row["background_index_errors"] == 0 for row in frames))
        self.assertTrue(all(row["backend_changed_from_front"] == 0 for row in frames))
        self.assertEqual(sum(bool(row["legacy_samples_with_exact_post_palette"]) for row in frames), 58)
