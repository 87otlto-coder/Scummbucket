"""Phase-aware research tests; synthetic cases and an optional pinned private trace."""
import os
import unittest

from scummbucket.palette_probe import prepare_cycles, advance_palette
from scummbucket.room23_capture_research import (
    ResearchInvalid, analyze_room23_capture, parse_room23_hook_log, compare_room23_palette_capture,
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

    def test_report_lists_actual_timer_distribution(self):
        parsed, result = self.verify(self.make_log())
        self.assertEqual(result["timer_pair_distribution"], [{
            "var_timer": 6, "var_timer_next": 6, "count": 40,
            "first_sequence": 1, "last_sequence": 40,
        }])

    def test_mixed_timer_regime_is_reported_without_relabeling(self):
        parsed = parse_room23_hook_log(self.make_log())
        # Keep palette data unchanged: this test examines the observation
        # histogram, not a claim that our modeled 60-delta replay matches.
        parsed["samples"][20]["var_timer"] = 60
        parsed["samples"][20]["var_timer_next"] = 60
        result = compare_room23_palette_capture(
            self.clut, self.records, parsed, phase_search_limit=70)
        self.assertIn({"var_timer": 60, "var_timer_next": 60, "count": 1,
                       "first_sequence": 21, "last_sequence": 21},
                      result["timer_pair_distribution"])

    def test_windows_stress_mode_requires_observed_timer_60(self):
        from pathlib import Path
        script = (Path(__file__).resolve().parents[1] /
                  "tools" / "run_scummvm_palette_capture.ps1").read_text()
        self.assertIn("CAPTURE_MODE_NOT_OBSERVED", script)
        self.assertIn("scumm_vars[19] 60", script)
        self.assertIn("AFTER entering Room 23", script)
        self.assertIn("timer_pair_distribution", script)

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

    def test_sixty_unit_stress_phase_needs_longer_calibration(self):
        # Original Room 23 cycle rates: the 60-unit setting causes several
        # cycles to rotate on almost every callback. Repeated short patterns
        # make the phase ambiguous with the old eight-sample cap.
        records = [
            {"id": i + 1, "rate_raw": rate, "flags": 0,
             "start_color": 176 + 2 * i, "end_color": 177 + 2 * i,
             "offset": 1000 + 9 * i}
            for i, rate in enumerate((230, 307, 153, 384, 460, 384, 230, 307))
        ]
        cycles, issues = prepare_cycles(records)
        self.assertFalse(issues)
        palette = bytearray(self.clut)
        samples = []
        for sequence in range(1, 33):
            advance_palette(palette, cycles, delta=60)
            samples.append({
                "sequence": sequence, "var_timer": 60,
                "var_timer_next": 60, "millis": 1000 + sequence * 1000,
                "palette": bytes(palette),
            })
        capture = {
            "complete": False, "stop_reason": "missing_end",
            "initial_palette": self.clut, "begin_millis": 1000,
            "samples": samples,
        }
        result = compare_room23_palette_capture(
            self.clut, records, capture, phase_search_limit=500)
        self.assertEqual(result["model_comparison_status"], "matched")
        self.assertEqual(result["samples_matching_cycling"], 32)
        self.assertEqual(result["segments"][0]["first_sample_equivalent_model_update"], 1)
        self.assertEqual(result["segments"][0]["calibration_samples"], 16)
        self.assertEqual(result["heldout_samples_matching"], 16)
        self.assertFalse(result["capture_complete"])

    def test_continuous_forecast_crosses_gap_without_slow_speed_calibration(self):
        rates = (230, 307, 153, 384, 460, 384, 230, 307)
        records = [dict(self.records[0], id=i + 1, rate_raw=rate,
                        start_color=176 + 2*i, end_color=177 + 2*i)
                   for i, rate in enumerate(rates)]
        # Independent two-color oracle: one swap on threshold, retain remainder.
        counters = [0] * len(records)
        palette = bytearray(self.clut)
        rows = []
        for seq in range(1, 88):
            timer = 6 if seq <= 28 else 60
            timer_next = 6 if seq <= 27 else 60
            for i, rate in enumerate(rates):
                counters[i] += max(timer, timer_next)
                delay = 16384 // rate
                if counters[i] >= delay:
                    counters[i] %= delay
                    a = records[i]["start_color"] * 3
                    palette[a:a+6] = palette[a+3:a+6] + palette[a:a+3]
            rows.append(dict(sequence=seq, var_timer=timer, var_timer_next=timer_next,
                             millis=100*seq if seq <= 27 else 15000 + (seq-28)*1000,
                             palette=bytes(palette)))
        capture = dict(samples=rows, initial_palette=self.clut, complete=False,
                       stop_reason="missing_end")

        def forecast():
            return compare_room23_palette_capture(
                self.clut, records, capture)["continuous_scheduler"]

        replay = forecast()
        self.assertLess(replay["calibration_samples"], 28)
        self.assertEqual(replay["status"], "matched")
        self.assertEqual(replay["heldout_matches"], 87 - replay["calibration_samples"])
        for prediction in replay["predictions"]:
            self.assertEqual(prediction["predicted_rotation_ids"], prediction["observed_changed_ids"])
        corrupted = bytearray(rows[28]["palette"])
        corrupted[176*3] ^= 1
        corrupted[0] ^= 1
        rows[28]["palette"] = bytes(corrupted)
        changed = forecast()
        self.assertEqual(changed["status"], "mismatch")
        self.assertEqual(changed["cycles"][0]["first_mismatch"], 29)
        mismatch = next(p for p in changed["predictions"] if p["sequence"] == 29)
        self.assertEqual(mismatch["noncycling_mismatch_indices"], [0])
        self.assertEqual(changed["heldout_matches"], replay["heldout_matches"] - 1)
        self.assertEqual([p["predicted_rotation_ids"] for p in replay["predictions"]],
                         [p["predicted_rotation_ids"] for p in changed["predictions"]])

    @unittest.skipUnless(os.environ.get("SCUMMBUCKET_ROOM23_MIXED_LOG") and
                         os.environ.get("SCUMMBUCKET_MI2_GAME"),
                         "Set private mixed trace and original game paths")
    def test_pinned_mixed_trace_predicts_entire_slow_suffix(self):
        report = analyze_room23_capture(os.environ["SCUMMBUCKET_MI2_GAME"],
                                        os.environ["SCUMMBUCKET_ROOM23_MIXED_LOG"])
        self.assertEqual(report["raw_log_sha256"],
                         "591c06aa6f518e48ef6e8da1b45f4bc357179640ac8c1fb506d6a1f9488a5e73")
        self.assertEqual(report["status"], "incomplete")
        evidence = report["evidence"]
        self.assertEqual(evidence["stop_reason"], "missing_end")
        self.assertFalse(evidence["capture_complete"])
        replay = evidence["continuous_scheduler"]
        self.assertEqual(replay["calibration_samples"], 3)
        self.assertEqual(replay["heldout_matches"], 84)
        slow = [p for p in replay["predictions"] if p["timer_pair"] == [60, 60]]
        self.assertEqual([p["sequence"] for p in slow], list(range(29, 88)))
        for p in replay["predictions"]:
            self.assertEqual(p["predicted_rotation_ids"], p["observed_changed_ids"])
        self.assertEqual([sum(g["id"] in p["observed_changed_ids"] for p in slow)
                          for g in replay["cycles"]], [49, 59, 33, 59, 59, 59, 49, 59])

    def test_windows_runner_preserves_strict_end_gate(self):
        from pathlib import Path
        script = (Path(__file__).resolve().parents[1] /
                  "tools" / "run_scummvm_palette_capture.ps1").read_text()
        forensic_at = script.index("analyze-room23-palette-log")
        end_gate_at = script.index("if ($lastLine -notmatch")
        strict_at = script.index("import-scummvm-palette-log")
        self.assertLess(forensic_at, end_gate_at)
        self.assertLess(end_gate_at, strict_at)
        self.assertIn("phase-research.json", script)

    def test_outside_phase_limit_reports_unresolved_not_success(self):
        parsed = parse_room23_hook_log(self.make_log())
        result = compare_room23_palette_capture(
            self.clut, self.records, parsed, phase_search_limit=2)
        self.assertEqual(result["model_comparison_status"], "mismatch_or_unresolved")


if __name__ == "__main__":
    unittest.main()
