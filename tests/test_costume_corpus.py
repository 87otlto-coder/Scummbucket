"""Source-only SCUMM v5 costume audit tests, synthetic bytes only."""
from hashlib import sha256
from pathlib import Path
from unittest.mock import patch
import struct
import unittest

from scummbucket.classic_costume import ClassicCostume
from scummbucket.costume_corpus import audit_costume_selectors
from tools.audit_costume_corpus import audit
from test_classic_costume import sample, sample_32


class CostumeCorpusTests(unittest.TestCase):
    def test_audit_covers_defined_and_unused_selector_slots(self):
        for costume in (sample(), sample_32()):
            with self.subTest(colors=costume.colors):
                before = costume.data
                report = audit_costume_selectors(costume)
                self.assertEqual(report["declared_selector_slots"], 12)
                self.assertEqual(report["defined_pointer_slots"], 1)
                self.assertEqual(report["consistent_selector_slots"], 1)
                self.assertEqual(report["unused_selector_slots"], 11)
                self.assertEqual(report["failed_selector_slots"], 0)
                self.assertEqual(report["selector_slots_with_ranges"], 1)
                self.assertGreater(report["cel_references_examined"], 0)
                self.assertEqual(costume.data, before)

    def test_broken_cel_is_preserved_as_a_selector_failure(self):
        source = sample(runs=b"\x17")
        report = audit_costume_selectors(source)
        self.assertEqual(report["failed_selector_slots"], 1)
        self.assertEqual(report["failures"][0]["selector"], 8)
        self.assertIn("cel run length", report["failures"][0]["message"])
        self.assertEqual(report["unused_selector_slots"], 11)

    def test_multiple_selectors_share_one_failed_source_reference(self):
        data = bytearray(sample(runs=b"\x17").data)
        # Selector 9 points at the same v5 limb record as selector 8.
        table = 10 + 16
        first = table + 34 + 2 * 8
        second = table + 34 + 2 * 9
        data[second:second + 2] = data[first:first + 2]
        before = bytes(data)
        result = audit_costume_selectors(ClassicCostume(before))
        self.assertEqual(result["failed_selector_slots"], 2)
        self.assertEqual([x["selector"] for x in result["failures"]], [8, 9])
        self.assertEqual(result["distinct_failed_reference_groups"], 1)
        self.assertEqual(result["failure_groups"], [{
            "limb": 0, "position": 0, "type": "ValueError",
            "message": "invalid cel run length", "selectors": [8, 9],
            "source_reference_known": True,
        }])
        self.assertEqual(bytes(data), before)

    def test_stop_resume_control_extents_are_not_drawable_ranges(self):
        from test_classic_animation import costume as animation_fixture
        sample = animation_fixture([4, 0x79, 0x7a],
                                   {1: {0: (1, 127)}, 2: {0: (2, 127)}})
        # The general animation fixture reserves 32 selectors but stores
        # synthetic records within that unused table tail. Limit the table
        # to the 0..8 selectors actually present in this audit fixture.
        data = bytearray(sample.data)
        data[8] = 8
        sample.data = bytes(data)
        report = audit_costume_selectors(sample)
        self.assertEqual(report["failed_selector_slots"], 0)
        self.assertEqual(report["selector_slots_with_ranges"], 0)
        self.assertEqual(report["defined_pointer_slots"], 2)

    def test_source_initialization_and_range_controls_are_counted(self):
        from test_classic_animation import costume as animation_fixture
        source = animation_fixture([4, 0x78, 0x7c, 5, 0x79, 0x7a], {
            1: {0: (4, 127)}, 2: {0: (5, 127)},
            3: {0: (65535, 0)}, 4: {0: (0, 131)},
        })
        # Only selector slots 0..16 exist in this miniature corpus.
        data = bytearray(source.data)
        data[8] = 16
        source.data = bytes(data)
        # The generic animation-record fixture has no cel decoder; supply
        # a synthetic opaque cel so this test isolates command accounting.
        from types import SimpleNamespace
        source.limb = lambda limb, position: (
            0, SimpleNamespace(width=1, height=1))
        before = source.data
        report = audit_costume_selectors(source)
        controls = report["control_references"]
        self.assertEqual(report["failed_selector_slots"], 0)
        self.assertEqual(report["defined_pointer_slots"], 4)
        self.assertEqual(controls, {
            "limb_clear_entries": 1,
            "initial_stop_entries": 1,
            "initial_resume_entries": 1,
            "initialized_limb_ranges": 1,
            "one_shot_flags": 1,
            "sound_command_references": 1,
            "counter_command_references": 1,
        })
        self.assertEqual(source.data, before)

    def test_zero_area_cels_are_counted_not_rejected(self):
        data = bytearray(sample().data)
        ClassicCostume.header.pack_into(data, 112, 0, 0, 0, 0, 2, -1)
        costume = ClassicCostume(bytes(data))
        result = audit_costume_selectors(costume)
        self.assertEqual(result["failed_selector_slots"], 0)
        self.assertGreater(result["zero_area_references"], [])
        self.assertTrue(all(x["width"] == 0 and x["height"] == 0
                            for x in result["zero_area_references"]))

    @staticmethod
    def fake_inventory(raw, index):
        return {
            "status": "success",
            "sources": [{"sha256": sha256(index).hexdigest()},
                        {"sha256": sha256(raw).hexdigest()}],
            "directory_links": {"entries": [
                {"directory": "DCOS", "id": 1, "room_id": 7, "status": "linked",
                 "source_offset": 0, "byte_length": len(raw)},
                {"directory": "DCOS", "id": 2, "room_id": None, "status": "unused"},
            ]},
        }

    def test_archive_audit_retains_success_and_failure_without_writing_source(self):
        source = sample().data
        for cel in (sample().data, sample(runs=b"\x17").data):
            raw = bytes(b ^ 0x69 for b in cel)
            index = b"synthetic index"
            inv = self.fake_inventory(raw, index)
            with patch("tools.audit_costume_corpus.inspect", return_value=inv), patch(
                "tools.audit_costume_corpus._read_pair",
                return_value=(index, raw, "MONKEY2.000", "MONKEY2.001")):
                report = audit(Path("synthetic-game.zip"))
            self.assertEqual(report["summary"]["linked_costumes"], 1)
            self.assertEqual(report["summary"]["unused_costume_slots"], 1)
            self.assertEqual(report["source_hashes"][1]["sha256"], sha256(raw).hexdigest())
            self.assertEqual(report["costumes"][0]["colors"], 16)
            self.assertEqual(report["status"], "success" if cel == source else "partial")
            if cel != source:
                self.assertEqual(report["summary"]["failed_selector_slots"], 1)
                self.assertEqual(report["diagnostics"][0]["code"], "SELECTOR_CEL_FAILED")

    def test_changed_archive_reopen_fails_closed_before_costume_scan(self):
        cost = sample().data
        index = b"synthetic index"
        original = bytes(v ^ 0x69 for v in cost)
        altered = original[:-1] + bytes([original[-1] ^ 1])
        inv = self.fake_inventory(original, index)
        with patch("tools.audit_costume_corpus.inspect", return_value=inv), patch(
            "tools.audit_costume_corpus._read_pair",
            return_value=(index, altered, "MONKEY2.000", "MONKEY2.001")):
            report = audit(Path("synthetic-game.zip"))
        self.assertEqual(report["status"], "failed")
        self.assertEqual(report["diagnostics"][0]["code"], "SOURCE_PREFLIGHT_FAILED")
        self.assertEqual(report["costumes"], [])


if __name__ == "__main__":
    unittest.main()
