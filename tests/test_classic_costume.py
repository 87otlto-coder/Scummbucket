import os
from pathlib import Path
import unittest

from scummbucket.classic_costume import ClassicCostume, apply_depth, compose


def sample(runs=b"\x11\x02\x20\x03"):
    # Two 3-pixel columns. The transparent run and extended run use local slots.
    chunk = bytearray(124)
    chunk[:4] = b"COST"
    chunk[8:10] = bytes([11, 0x58])
    chunk[10:13] = bytes([99, 42, 7])

    def pointer(offset, target):
        chunk[offset:offset+2] = (target - 2).to_bytes(2, "little")

    pointer(26, 96)
    pointer(28, 104)
    pointer(30, 104)
    pointer(76, 86)  # Walking toward the left
    chunk[86:94] = bytes([0, 192, 0, 0, 2, 3, 0, 0])
    chunk[96:100] = bytes([0, 0x78, 0, 0x79])
    pointer(104, 112)
    ClassicCostume.header.pack_into(chunk, 112, 2, 3, -1, -2, 1, 1)
    chunk.extend(runs)
    chunk[4:8] = len(chunk).to_bytes(4, "big")
    return ClassicCostume(bytes(chunk))


class CostumeTests(unittest.TestCase):
    def test_columns_palette_transparency_mirroring_and_limb_motion(self):
        costume = sample()
        state = [0, 0] + [65535] * 14
        result, limbs = compose(costume, bytes([9]) * 12, 4, 1, 2, 270, state)
        self.assertEqual([p["origin"] for p in limbs], [[2, 0], [1, -1]])
        self.assertEqual(list(result), [7, 7, 42, 9, 7, 7, 9, 9, 9, 7, 9, 9])

    def test_reverse_tick_wrap_skips_event_and_stops_retained_limb(self):
        costume = sample()
        for observed, drawn in [(0, 2), (2, 0)]:
            state = [observed, 0] + [65535] * 14
            self.assertEqual(costume.drawn_walk_positions(2, 270, state), [drawn] + [65535] * 15)
            self.assertEqual(state[1], 0)
        with self.assertRaises(ValueError):
            costume.drawn_walk_positions(2, 270, [1, 0] + [65535] * 14)

    def test_rejects_malformed_runs_and_pointers(self):
        for runs in (b"\x17", b"\x10", b"\x10\x00", b"\x13"):
            with self.subTest(runs=runs), self.assertRaises(ValueError):
                sample(runs).limb(0, 0)
        with self.assertRaises(ValueError):
            sample().limb(2, 0)

    def test_mask_preserves_background_indices(self):
        self.assertEqual(apply_depth(bytes(range(8)), bytes([30])*8, b"\x81"),
                         bytes([30, 1, 2, 3, 4, 5, 6, 30]))

    @unittest.skipUnless(os.getenv("SCUMMBUCKET_COSTUME_FIXTURE"), "private Room 23 evidence")
    def test_all_original_frame_pairs(self):
        from tools.verify_room23_costume import verify
        result = verify(Path(os.environ["SCUMMBUCKET_COSTUME_FIXTURE"]))
        self.assertEqual([r["id"] for r in result["frames"]], list(range(1, 88)))
        self.assertEqual(result["totals"], {"control": 0, "normal": 0})
        self.assertEqual(sum(r["suppressed_indices"] for r in result["frames"]), 2036)
        self.assertEqual(result["frames"][29]["suppressed_indices"], 546)
