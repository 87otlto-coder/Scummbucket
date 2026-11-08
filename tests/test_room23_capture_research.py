"""Phase-aware research tests; all generated palettes are synthetic."""
import unittest

from scummbucket.palette_probe import prepare_cycles, advance_palette
from scummbucket.room23_capture_research import (
    ResearchInvalid, parse_room23_hook_log, compare_room23_palette_capture,
)
from scummbucket.engine_trace_import import EngineTraceError, parse_scummvm_palette_log


class Room23CaptureResearchTest(unittest.TestCase):
    def setUp(self):
        self.clut = bytes(range(256)) * 3
        # Four synthetic two-color cycles; delays ~10,13,17,19 counter units.
        self.records = [
            {"id": i + 1, "rate_raw": rate, "flags": 0,
             "start_color": 176 + 2 * i, "end_color": 177 + 2 * i,
             "offset": 1000 + 9 * i}
            for i, rate in enumerate([1490, 1260, 960, 860])
        ]

    def make_log(self, *, complete=False):
        def with_static_overrides(current):
            value = bytearray(current)
            for index in (1, 6):
                value[index * 3:index * 3 + 3] = b"\x00\x11\x22"
            return bytes(value)

        cycles, issues = prepare_cycles(self.records)
        self.assertFalse(issues)
        palette = bytearray(self.clut)
        for _ in range(7):
            advance_palette(palette, cycles, delta=6)
        lines = [f"SBP4|BEGIN|23|1000|{with_static_overrides(palette).hex()}"]
        for sequence in range(1, 41):
            if sequence == 21:
                # Deliberately reset source palette/counters after a clock gap.
                cycles, _ = prepare_cycles(self.records)
                palette = bytearray(self.clut)
            advance_palette(palette, cycles, delta=6)
            millis = 1000 + sequence * 100 + (27000 if sequence >= 21 else 0)
            lines.append(
                f"SBP4|SAMPLE|{sequence}|6|6|{millis}|"
                f"{with_static_overrides(palette).hex()}"
            )
        if complete:
            lines.append("SBP4|END|40|room_exit")
        return ("\n".join(lines) + "\n").encode("ascii")

    def verify(self, raw):
        parsed = parse_room23_hook_log(raw)
        result = compare_room23_palette_capture(
            self.clut, self.records, parsed, phase_search_limit=70)
        return parsed, result

    def test_incomplete_research_is_exact_but_not_completed(self):
        parsed, result = self.verify(self.make_log())
        self.assertFalse(parsed["complete"])
        self.assertEqual(parsed["stop_reason"], "missing_end")
        self.assertFalse(result["capture_complete"])
        self.assertEqual(result["model_comparison_status"], "matched")
        self.assertEqual(result["samples_matching_cycling"], 40)
        self.assertEqual(result["samples_matching_full_palette_with_observed_noncycle_baseline"], 40)
        self.assertEqual(result["heldout_samples_matching"], 34)
        self.assertEqual(result["runtime_noncycle_overrides_vs_source_clut"], [1, 6])
        self.assertEqual([part["first_sample_equivalent_model_update"]
                          for part in result["segments"]], [8, 1])
        self.assertEqual(result["clock_discontinuities"][0]["after_sequence"], 20)
        self.assertTrue(result["clock_discontinuities"][0]
                        ["source_cycle_colors_reinitialized_at_first_post_gap_sample"])

    def test_completed_log_can_be_phase_compared(self):
        parsed, result = self.verify(self.make_log(complete=True))
        self.assertTrue(parsed["complete"])
        self.assertEqual(parsed["stop_reason"], "room_exit")
        self.assertTrue(result["capture_complete"])
        self.assertEqual(result["model_comparison_status"], "matched")

    def test_existing_strict_importer_rejects_research_partial_log(self):
        with self.assertRaises(EngineTraceError):
            parse_scummvm_palette_log(
                self.make_log(), engine_commit="a" * 40,
                game_resource_sha256="b" * 64)

    def test_held_out_cycling_tamper_is_visible(self):
        parsed = parse_room23_hook_log(self.make_log())
        changed = bytearray(parsed["samples"][15]["palette"])
        changed[177 * 3] ^= 1
        parsed["samples"][15]["palette"] = bytes(changed)
        result = compare_room23_palette_capture(
            self.clut, self.records, parsed, phase_search_limit=70)
        self.assertEqual(result["model_comparison_status"], "mismatch_or_unresolved")
        self.assertEqual(result["segments"][0]["first_mismatch"]["sequence"], 16)
        self.assertEqual(result["segments"][0]["first_mismatch"]["cycling_indices"], [177])

    def test_held_out_noncycling_tamper_is_visible(self):
        parsed = parse_room23_hook_log(self.make_log())
        changed = bytearray(parsed["samples"][15]["palette"])
        changed[20 * 3] ^= 1
        parsed["samples"][15]["palette"] = bytes(changed)
        result = compare_room23_palette_capture(
            self.clut, self.records, parsed, phase_search_limit=70)
        self.assertEqual(result["model_comparison_status"], "mismatch_or_unresolved")
        self.assertEqual(result["segments"][0]["first_mismatch"]["noncycling_indices"], [20])

    def test_invalid_end_never_becomes_complete(self):
        raw = self.make_log(complete=True).replace(
            b"SBP4|END|40|", b"SBP4|END|41|")
        with self.assertRaises(ResearchInvalid) as error:
            parse_room23_hook_log(raw)
        self.assertEqual(error.exception.code, "RESEARCH_END_MISMATCH")

    def test_truncated_record_fails(self):
        with self.assertRaises(ResearchInvalid) as error:
            parse_room23_hook_log(self.make_log()[:-1])
        self.assertEqual(error.exception.code, "RESEARCH_LOG_TRUNCATED_LINE")

    def test_wrong_sequence_fails(self):
        raw = self.make_log().replace(b"SBP4|SAMPLE|15|", b"SBP4|SAMPLE|16|")
        with self.assertRaises(ResearchInvalid) as error:
            parse_room23_hook_log(raw)
        self.assertEqual(error.exception.code, "RESEARCH_SEQUENCE_INVALID")

    def test_outside_phase_limit_reports_unresolved_not_success(self):
        parsed = parse_room23_hook_log(self.make_log())
        result = compare_room23_palette_capture(
            self.clut, self.records, parsed, phase_search_limit=2)
        self.assertEqual(result["model_comparison_status"], "mismatch_or_unresolved")


if __name__ == "__main__":
    unittest.main()
