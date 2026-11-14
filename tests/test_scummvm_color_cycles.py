"""Source-free tests for archive-anchored ScummVM ColorCycle save extraction."""
import gzip
from pathlib import Path
import struct
import tempfile
import unittest

from fixture_scummvm_save import synthetic_scummvm_save
from scummbucket.scummvm_color_cycles import inspect_scummvm_color_cycles
from scummbucket.scummvm_save import SaveFormatError


CYCLES = [
    {"id":1,"rate_raw":384,"flags":0,"start_color":16,"end_color":18,"offset":1},
    {"id":2,"rate_raw":384,"flags":0,"start_color":176,"end_color":177,"offset":2},
    {"id":3,"rate_raw":459,"flags":0,"start_color":178,"end_color":179,"offset":3},
    {"id":4,"rate_raw":306,"flags":0,"start_color":180,"end_color":181,"offset":4},
    {"id":5,"rate_raw":228,"flags":0,"start_color":182,"end_color":183,"offset":5},
    {"id":6,"rate_raw":153,"flags":0,"start_color":184,"end_color":185,"offset":6},
]
COUNTERS = [12,12,26,35,13,80]


def block(counters=COUNTERS):
    raw = bytearray(16*8)
    for index, record in enumerate(CYCLES):
        delay = 16384 // record["rate_raw"]
        struct.pack_into(
            "<HHHBB", raw, index*8,
            delay, counters[index], record["flags"],
            record["start_color"], record["end_color"],
        )
    return bytes(raw)


class ColorCycleSaveTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.path = Path(self.tmp.name) / "monkey2.s01"
        self.base = synthetic_scummvm_save(compressed=False)
        self.build()

    def build(self, *, blocks=None, compressed=True):
        if blocks is None:
            blocks = [block()]
        raw = self.base + b"synthetic-byte-gap" + b"synthetic-other-state".join(blocks)
        self.path.write_bytes(gzip.compress(raw, mtime=0) if compressed else raw)

    def parse(self):
        return inspect_scummvm_color_cycles(self.path, CYCLES)

    def test_unique_original_order_and_values(self):
        original = self.path.read_bytes()
        out = self.parse()
        self.assertEqual([x["saved_counter"] for x in out["cycles"]], COUNTERS)
        self.assertEqual([x["id"] for x in out["cycles"]], [1,2,3,4,5,6])
        self.assertTrue(all(x["counter_in_normalized_range"] for x in out["cycles"]))
        self.assertEqual(out["active_cycle_count"], 6)
        self.assertTrue(out["inactive_slots_all_zero"])
        self.assertEqual(out["saved_room"], 7)
        self.assertFalse(out["first_engine_frame_counter_verified"])
        self.assertEqual(self.path.read_bytes(), original)
        self.assertEqual(list(self.path.parent.iterdir()), [self.path])

    def test_plain_scvm_save(self):
        self.build(compressed=False)
        self.assertEqual(self.parse()["cycles"][5]["saved_counter"], 80)

    def test_missing_cycle_block_is_an_explicit_error(self):
        self.build(blocks=[])
        with self.assertRaisesRegex(SaveFormatError, "No source-anchored"):
            self.parse()

    def test_duplicate_valid_blocks_are_refused(self):
        self.build(blocks=[block(),block()])
        with self.assertRaisesRegex(SaveFormatError, "Ambiguous ColorCycle"):
            self.parse()

    def test_wrong_cycle_color_range_rejected(self):
        data = bytearray(block())
        data[6] = 21
        self.build(blocks=[bytes(data)])
        with self.assertRaisesRegex(SaveFormatError, "No source-anchored"):
            self.parse()

    def test_nonzero_inactive_slot_is_rejected(self):
        data = bytearray(block())
        data[6*8] = 1
        self.build(blocks=[bytes(data)])
        with self.assertRaisesRegex(SaveFormatError, "No source-anchored"):
            self.parse()

    def test_counter_outside_delay_is_visible_not_silently_normalized(self):
        changed = COUNTERS.copy()
        changed[0] = 99
        self.build(blocks=[block(changed)])
        result = self.parse()
        self.assertEqual(result["cycles"][0]["saved_counter"], 99)
        self.assertFalse(result["cycles"][0]["counter_in_normalized_range"])

    def test_wrong_archive_definition_is_refused(self):
        changed = [dict(x) for x in CYCLES]
        changed[0]["start_color"] = 15
        with self.assertRaisesRegex(SaveFormatError, "No source-anchored"):
            inspect_scummvm_color_cycles(self.path, changed)

    def test_dos_save_is_incompatible(self):
        self.path.write_bytes(b"123\x00" + bytes(60))
        with self.assertRaisesRegex(SaveFormatError, "original DOS SAVEGAME"):
            self.parse()


if __name__ == "__main__":
    unittest.main()
