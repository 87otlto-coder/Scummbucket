import os
from pathlib import Path
import unittest

try:
    import PIL
except ImportError:
    raise unittest.SkipTest("walk diagnostics require Pillow")

from tools.compare_room23_walk import compare, measure


class Room23WalkTests(unittest.TestCase):
    def test_packed_mask_edges_and_index_equal_costume_pixels(self):
        bg = bytes(640)
        control = bytearray(bg)
        for index in (0, 7, 8, 319, 320, 639):
            control[index] = 42
        normal = bytearray(control)
        for index in (0, 7, 319, 320):
            normal[index] = 0
        mask = bytearray(80)
        mask[0], mask[39], mask[40] = 0xc1, 1, 128
        self.assertEqual(measure(bg, normal, control, mask),
                         dict(visible=2, hidden=4, hidden_bounds=[0, 0, 319, 1]))
        for index in (0, 8):
            damaged = bytearray(normal)
            damaged[index] ^= 1
            with self.assertRaisesRegex(ValueError, "clipping model mismatch"):
                measure(bg, damaged, control, mask)
        with self.assertRaises(ValueError):
            measure(bg, normal, control, mask[:-1])

    @unittest.skipUnless(all(os.getenv(k) for k in ("SCUMMBUCKET_WALK_NORMAL",
                         "SCUMMBUCKET_WALK_CONTROL", "SCUMMBUCKET_MI2_GAME")), "private walking runs")
    def test_full_crossing_and_unobstructed_recovery(self):
        normal, control, game = (Path(os.environ[k]) for k in (
            "SCUMMBUCKET_WALK_NORMAL", "SCUMMBUCKET_WALK_CONTROL", "SCUMMBUCKET_MI2_GAME"))
        frames = compare(normal, control, game)["frames"]
        self.assertEqual([r["id"] for r in frames], list(range(1, 88)))
        self.assertEqual({r["id"]: r["hidden"] for r in frames if r["hidden"]},
                         {26: 8, 28: 81, 29: 329, 30: 546, 31: 545, 32: 447, 33: 77, 36: 3})
        self.assertEqual([(r["walkbox"], r["plane"]) for r in frames],
                         [(2, 0)] * 14 + [(1, 0)] * 11 + [(12, 2)] * 62)
        self.assertEqual([r["visible"] for r in frames[29:31]], [4, 6])
        self.assertEqual([(r["x"], r["y"], r["moving"], r["visible"]) for r in frames[37:]],
                         [(280, 137, 0, 660)] * 50)
