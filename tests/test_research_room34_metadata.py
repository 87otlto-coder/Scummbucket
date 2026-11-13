"""Research metadata *consistency* checks, not game execution tests.

The metadata was derived from user-supplied external disassembly reports.
No original game assets or disassembly transcripts are kept in the repo.
"""
import json
from collections import Counter
from pathlib import Path
import unittest


EVIDENCE_FILE = (Path(__file__).resolve().parents[1] /
                 "docs" / "research" / "P1_ROOM34_OBJECT_EVENTS.json")


class Room34ResearchMetadataTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.evidence = json.loads(EVIDENCE_FILE.read_text(encoding="utf-8"))

    def test_event_counts_and_offsets(self):
        d = self.evidence
        events = d["instruction_events"]
        self.assertEqual(len(events), 17)
        self.assertEqual(Counter(e["script_id"] for e in events), {201: 11, 202: 6})
        self.assertEqual(Counter(e["operation"] for e in events),
                         {"drawObject": 11, "setState": 6})
        bases = {201: 2740982 + 9, 202: 2746032 + 9}
        for e in events:
            with self.subTest(script=e["script_id"], offset=e["relative_instruction_offset_hex"]):
                self.assertEqual(
                    e["source_byte_offset"],
                    bases[e["script_id"]] + int(e["relative_instruction_offset_hex"], 16))
                self.assertEqual(e["object_id"], 358)
                self.assertTrue(e["instruction_alignment_verified"])
                self.assertFalse(e["runtime_execution_observed"])
                self.assertFalse(e["visual_output_observed"])
        self.assertEqual(len(set(e["source_byte_offset"] for e in events)), 17)

    def test_only_four_draws_use_random_selection_variable(self):
        events = self.evidence["instruction_events"]
        variable_draws = [e for e in events if e["operation"] == "drawObject"
                          and e["state_operand_type"] == "variable_reference"]
        literal_draws = [e for e in events if e["operation"] == "drawObject"
                         and e["state_operand_type"] == "literal"]
        resets = [e for e in events if e["operation"] == "setState"]
        self.assertEqual(len(variable_draws), 4)
        self.assertTrue(all(e["state_operand_value"] == 100 for e in variable_draws))
        self.assertEqual(len(literal_draws), 7)
        self.assertTrue(all(e["state_operand_value"] == 1 for e in literal_draws))
        self.assertEqual(len(resets), 6)
        self.assertTrue(all(e["state_operand_value"] == 0 for e in resets))

    def test_formula_and_clamp(self):
        info = self.evidence["random_select"]
        self.assertEqual(info["random_range_inclusive"], [0, 2])
        self.assertEqual(info["number_range"], [1, 5])
        self.assertEqual(info["formula"], "min(15, (3*n - 1) + r)")
        for number in range(1, 6):
            expected = [min(15, 3 * number - 1 + offset) for offset in range(3)]
            self.assertEqual(info["possible_states_by_number"][str(number)], expected)
        self.assertEqual(info["possible_states_by_number"]["5"], [14, 15, 15])

    def test_object_357_relation_not_misreported_as_animation(self):
        metadata = self.evidence["additional_context"]
        self.assertFalse(metadata["object357"]["joint_animation_verified"])
        self.assertEqual(metadata["object357"]["set_state_zero"]["source_byte_offset"], 2747105)
        self.assertFalse(metadata["timing"]["elapsed_milliseconds_verified"])
        self.assertFalse(metadata["timing"]["frame_rate_verified"])
        self.assertEqual(metadata["palette_cycle_flag_warnings"]["count"], 4)

    def test_discussion_is_not_mistaken_for_runtime_verification(self):
        verification = self.evidence["verification"]
        self.assertEqual(verification["script201"]["confirmed_starts"], 11)
        self.assertEqual(verification["script202"]["confirmed_starts"], 6)
        self.assertEqual(verification["script201"]["not_emitted"], 0)
        self.assertEqual(verification["script202"]["conflicts"], 0)
        self.assertIn("neither execution", verification["statement"])
        self.assertEqual(self.evidence["classification"],
                         "interactive_script_directed_image_state_changes")


if __name__ == "__main__":
    unittest.main()
