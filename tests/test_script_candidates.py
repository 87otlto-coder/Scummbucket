"""Synthetic byte-pattern tests: no claim of instruction alignment or execution."""
import struct
import tempfile
import unittest
from pathlib import Path

from scummbucket.inspector import inspect
from scummbucket.script_candidates import scan_room_script_patterns
from test_inspector import chunk, index, make_zip, resource


def with_local_script(bytecode: bytes, *, script_id=201) -> bytes:
    """Append a synthetic local script to a valid single-room SCUMM v5 fixture."""
    original = resource(multiple_states=True)
    room_len = struct.unpack_from(">I", original, 34)[0]
    original_room_data = original[38:30 + room_len]
    replacement_room = chunk(
        "ROOM", original_room_data + chunk("LSCR", bytes([script_id]) + bytecode))
    return chunk("LECF", original[8:22] + chunk("LFLF", replacement_room))


class ScriptPatternTest(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.path = Path(temp.name) / "synthetic.zip"

    def inspect_script(self, bytecode):
        make_zip(self.path, a=index(), b=with_local_script(bytecode))
        return inspect(self.path)

    def test_draw_object_and_set_state_literal_candidates(self):
        # Synthetic object ID 99 = 0x0063, little-endian.
        report = self.inspect_script(
            b"\x05\x63\x00\x02\x01\x00"  # drawObject(obj=99, state=1)
            b"\x07\x63\x00\x00")         # setState(obj=99, state=0)
        self.assertEqual(report["status"], "success", report["diagnostics"])
        room = report["scene_inventory"]["rooms"][0]
        hits = room["script_state_candidates"]
        self.assertEqual(len(hits), 2)
        self.assertEqual([h["operation_candidate"] for h in hits], ["drawObject", "setState"])
        self.assertEqual([h["state_operand_raw"] for h in hits], [1, 0])
        self.assertEqual([h["raw_pattern_hex"] for h in hits], ["056300020100", "07630000"])
        self.assertEqual([h["script_id"] for h in hits], [201, 201])
        self.assertEqual(room["objects"][0]["script_state_pattern_count"], 2)
        self.assertFalse(hits[0]["instruction_alignment_verified"])
        self.assertFalse(hits[0]["runtime_execution_verified"])
        self.assertFalse(room["objects"][0]["script_control_verified"])

    def test_state_operands_can_reference_variables(self):
        report = self.inspect_script(
            b"\x05\x63\x00\x82\x64\x00"  # drawObject with state read from var 100
            b"\x47\x63\x00\x20\x00")     # setState with state read from var 32
        hits = report["scene_inventory"]["rooms"][0]["script_state_candidates"]
        self.assertEqual(len(hits), 2)
        self.assertEqual([h["state_operand_mode"] for h in hits],
                         ["variable_reference", "variable_reference"])
        self.assertEqual([h["state_operand_raw"] for h in hits], [100, 32])

    def test_unknown_object_id_is_not_linked_to_this_room(self):
        report = self.inspect_script(b"\x05\x64\x00\x02\x01\x00")
        self.assertEqual(report["status"], "success")
        self.assertEqual(report["scene_inventory"]["summary"]["script_pattern_candidates"]
                         ["all_patterns"], 0)

    def test_non_state_draw_subopcodes_are_out_of_scope(self):
        report = self.inspect_script(b"\x05\x63\x00\x1f")
        self.assertEqual(report["status"], "success")
        self.assertEqual(report["scene_inventory"]["rooms"][0]["script_state_candidates"], [])

    def test_incomplete_pattern_is_reported_not_silently_dropped(self):
        report = self.inspect_script(b"\x07\x63\x00")
        self.assertEqual(report["status"], "success", report["diagnostics"])
        self.assertEqual(report["scene_inventory"]["rooms"][0]["script_state_candidates"], [])
        self.assertIn("SCRIPT_PATTERN_INCOMPLETE",
                      [d["code"] for d in report["diagnostics"]])

    def test_false_positive_looking_text_is_marked_unverified(self):
        # Identical bytes can occur inside a string or numeric argument.
        report = self.inspect_script(b"This is data " + b"\x05\x63\x00\x02\x01\x00")
        hits = report["scene_inventory"]["rooms"][0]["script_state_candidates"]
        self.assertEqual(len(hits), 1)
        self.assertEqual(hits[0]["evidence"],
                         "raw_pattern_matches_scumm_v5_operand_layout")
        self.assertFalse(hits[0]["instruction_alignment_verified"])

    def test_invalid_script_range_emits_structured_error(self):
        scene = {"room_id": 1, "objects": [{"object_id": 99}],
                 "local_script_chunks": [
                     {"tag": "LSCR", "source_offset": 50, "byte_length": 999}]}
        summary, problems = scan_room_script_patterns(b"\x00" * 70, [scene],
                                                      source="synthetic")
        self.assertEqual(summary["all_patterns"], 0)
        self.assertEqual(problems[0]["code"], "SCRIPT_CHUNK_RANGE_INVALID")


if __name__ == "__main__":
    unittest.main()
