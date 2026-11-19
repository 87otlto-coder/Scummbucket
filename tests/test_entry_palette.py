import unittest

from scummbucket.entry_palette import apply_vga_entry_palette
from tools.room24_probe_log import palette_hook, room24_rng


class EntryPaletteTests(unittest.TestCase):
    def test_applies_only_source_mapped_slots(self):
        original = bytes([199]) * 768
        variables = {i: i - 469 for i in range(469, 481)}
        expected = bytearray(original)
        for index, values in {2: [0, 1, 2], 3: [3, 4, 5], 1: [6, 7, 8], 6: [9, 10, 11]}.items():
            expected[index * 3:index * 3 + 3] = bytes(values)
        self.assertEqual(apply_vga_entry_palette(original, variables, hook=6, video_mode=19), expected)
        with self.assertRaises(ValueError):
            apply_vga_entry_palette(original, variables, hook=6, video_mode=0)
        with self.assertRaises(ValueError):
            apply_vga_entry_palette(original, {}, hook=6, video_mode=19)

    def test_hook_context_rejects_duplicate_records(self):
        log = "SBPAL hook-context room=24 hook=6 mode=19\n"
        log += "\n".join(f"SBPAL var {key} {key-469}" for key in range(469, 481))
        self.assertEqual(palette_hook(log, 24)[2][479], 10)
        with self.assertRaises(ValueError):
            palette_hook(log + "\nSBPAL var 479 10", 24)


class Room24RNGProbeTests(unittest.TestCase):
    def test_distinguishes_entry_draw_retry_and_accepted_result(self):
        log = "\n".join([
            "SB24 RNG max=2 result=0 previous=0",
            "SB24 entry room=24 resource=24",
            "SB24 RNG max=2 result=0 previous=1",
            "SB24 RNG max=2 result=2 previous=1",
            "SB24 RNG max=2 result=1 previous=3",
        ])
        observed = room24_rng(log, [3, 2])
        self.assertEqual([row["accepted"] for row in observed[0]], [False, True])
        self.assertEqual(observed[0][-1]["result"], 2)
        with self.assertRaises(ValueError):
            room24_rng(log, [1, 2])
