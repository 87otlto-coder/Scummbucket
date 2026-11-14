"""Synthetic holdout tests for saved Room 7 palette-cycle phase research."""
import copy
import unittest

from scummbucket.palette_probe import prepare_cycles, advance_palette
from scummbucket.room7_palette_phase import (
    analyze_saved_palette_cycles, PhaseResearchError)


class Room7SavedPalettePhaseTests(unittest.TestCase):
    def setUp(self):
        self.records = [
            dict(id=1, rate_raw=1638, flags=0, start_color=16,
                 end_color=18, offset=8),
            dict(id=2, rate_raw=1170, flags=0, start_color=176,
                 end_color=177, offset=8),
        ]
        self.initial = bytearray(768)
        for index in (16, 17, 18, 176, 177):
            self.initial[index*3:index*3+3] = bytes(
                (index, index ^ 37, index ^ 19))
        self.cycles, issues = prepare_cycles(self.records)
        self.assertEqual(issues, [])
        self.cycles[0]["counter"] = 7
        self.cycles[1]["counter"] = 4
        self.samples = []
        current = bytearray(self.initial)
        for n in range(87):
            advance_palette(current, self.cycles, delta=1)
            self.samples.append({
                "timer_pair": [1, 1],
                "post_palette": bytes(current),
            })

    def run_model(self, calibration=24):
        return analyze_saved_palette_cycles(
            self.records, bytes(self.initial), self.samples,
            calibration_frames=calibration)

    def test_saved_counter_calibration_predicts_heldout(self):
        result = self.run_model()
        self.assertEqual(result["status"], "heldout_matched")
        self.assertEqual(result["calibration_frames"], 24)
        self.assertEqual(result["heldout_frames"], 63)
        self.assertEqual(result["phase_uniquely_identified_count"], 2)
        self.assertEqual(result["heldout_full_palette_matches"], 63)
        self.assertEqual([row["calibration_matching_phases"] for row in
                          result["per_cycle"]], [[7], [4]])
        self.assertEqual(result["heldout_full_palette_mismatch_frames"], [])

    def test_tamper_in_heldout_cycling_color_is_reported(self):
        corrupt = bytearray(self.samples[37]["post_palette"])
        corrupt[16*3] ^= 1
        self.samples[37]["post_palette"] = bytes(corrupt)
        result = self.run_model()
        self.assertEqual(result["status"], "heldout_mismatch")
        self.assertIn(38, [row["frame"] for row in
                          result["heldout_full_palette_mismatch_frames"]])
        self.assertGreater(result["heldout_cycle_mismatch_total"], 0)

    def test_noncyle_changes_cannot_be_explained_as_phase(self):
        corrupt = bytearray(self.samples[40]["post_palette"])
        corrupt[3] = 33
        self.samples[40]["post_palette"] = bytes(corrupt)
        result = self.run_model()
        self.assertEqual(result["status"], "heldout_mismatch")
        self.assertEqual(result["heldout_noncycle_changed_frames"][0],
                         {"frame": 41, "palette_indices": [1]})

    def test_ambiguous_phase_but_unambiguous_forecast_is_valid(self):
        samples = [{"timer_pair": [0, 0],
                    "post_palette": bytes(self.initial)} for _ in range(30)]
        result = analyze_saved_palette_cycles(
            self.records, bytes(self.initial), samples, calibration_frames=8)
        self.assertEqual(result["status"], "heldout_matched")
        self.assertEqual(result["phase_uniquely_identified_count"], 0)
        self.assertEqual(result["heldout_full_palette_matches"], 22)
        self.assertGreater(len(result["per_cycle"][0]["calibration_matching_phases"]), 1)

    def test_ambiguous_future_never_selects_arbitrary_phase(self):
        samples = [{"timer_pair": [0, 0],
                    "post_palette": bytes(self.initial)} for _ in range(8)]
        # One held-out update: different surviving counter residues
        # disagree about whether the first rotation has occurred.
        samples += [{"timer_pair": [1, 1],
                     "post_palette": bytes(self.initial)}]
        result = analyze_saved_palette_cycles(
            self.records, bytes(self.initial), samples, calibration_frames=8)
        self.assertEqual(result["status"], "forecast_ambiguous")
        self.assertTrue(result["heldout_ambiguous_frames"])

    def test_unresolved_calibration_does_not_claim_success(self):
        corrupt = bytearray(self.samples[3]["post_palette"])
        corrupt[16*3:16*3+3] = bytes((255, 255, 255))
        self.samples[3]["post_palette"] = bytes(corrupt)
        result = self.run_model()
        self.assertEqual(result["status"], "calibration_unresolved")
        self.assertEqual(result["cycles_without_calibration_solution"], [1])

    def test_does_not_mutate_inputs(self):
        prior_samples = copy.deepcopy(self.samples)
        prior_records = copy.deepcopy(self.records)
        self.run_model()
        self.assertEqual(self.samples, prior_samples)
        self.assertEqual(self.records, prior_records)

    def test_bad_palette_and_overlap_fail_explicitly(self):
        self.samples[20]["post_palette"] = b"short"
        with self.assertRaisesRegex(PhaseResearchError, "Invalid post-palette"):
            self.run_model()
        self.samples[20]["post_palette"] = bytes(self.initial)
        overlapping = self.records + [
            dict(id=3, rate_raw=2048, flags=0, start_color=17,
                 end_color=19, offset=8),
        ]
        with self.assertRaisesRegex(PhaseResearchError, "Overlapping cycles"):
            analyze_saved_palette_cycles(
                overlapping, bytes(self.initial), self.samples)
