"""Synthetic validation of direct-save (non-fitted) palette forecasts."""
import copy
import unittest

from scummbucket.palette_probe import advance_palette, prepare_cycles
from scummbucket.saved_counter_forecast import (
    forecast_from_saved_counters, SavedCounterForecastError)


class SavedCounterForecastTests(unittest.TestCase):
    def setUp(self):
        self.records = [
            {"id":1,"rate_raw":4096,"flags":0,"start_color":16,"end_color":18,"offset":8},
            {"id":2,"rate_raw":2048,"flags":0,"start_color":176,"end_color":177,"offset":9},
        ]
        self.rows = [
            {"id":1,"delay_counter_units":4,"saved_counter":2,
             "flags_raw":0,"start_color":16,"end_color":18},
            {"id":2,"delay_counter_units":8,"saved_counter":5,
             "flags_raw":0,"start_color":176,"end_color":177},
        ]
        initial = bytearray(768)
        for idx in (16,17,18,176,177):
            initial[idx*3:idx*3+3] = bytes([idx,idx ^ 19,idx ^ 37])
        self.initial = bytes(initial)
        cycles, warnings = prepare_cycles(self.records)
        self.assertFalse(warnings)
        for cycle in cycles:
            cycle["counter"] = self.rows[cycle["id"]-1]["saved_counter"]
        pal = bytearray(initial)
        self.samples = []
        for idx in range(15):
            delta = 1 if idx < 8 else 2
            advance_palette(pal, cycles, delta=delta)
            self.samples.append({
                "timer_pair": [delta,delta],
                "post_palette": bytes(pal),
            })

    def predict(self):
        return forecast_from_saved_counters(
            self.records, self.rows, self.initial, self.samples)

    def test_all_predictions_use_stored_counter_without_fit(self):
        saved_rows = copy.deepcopy(self.rows)
        saved_samples = copy.deepcopy(self.samples)
        outcome = self.predict()
        self.assertEqual(outcome["status"], "direct_saved_counter_forecast_matched")
        self.assertEqual(outcome["exact_frame_count"], 15)
        self.assertEqual(outcome["mismatch_frame_count"], 0)
        self.assertFalse(outcome["evidence"]["phase_fitting_used"])
        self.assertEqual(saved_rows, self.rows)
        self.assertEqual(saved_samples, self.samples)

    def test_wrong_saved_counter_cannot_be_silently_fitted(self):
        self.rows[0]["saved_counter"] = 0
        outcome = self.predict()
        self.assertEqual(outcome["status"], "direct_saved_counter_forecast_mismatch")
        self.assertGreater(outcome["mismatch_frame_count"], 0)
        self.assertIn(1, outcome["mismatch_frames_per_cycle"])
        self.assertGreater(outcome["mismatch_frames_per_cycle"][1], 0)

    def test_noncyle_change_is_reported(self):
        row = bytearray(self.samples[6]["post_palette"])
        row[3] = 44  # index 1 does not belong to either CYCL group
        self.samples[6]["post_palette"] = bytes(row)
        outcome = self.predict()
        self.assertEqual(outcome["noncycle_mismatch_frames"], [7])
        self.assertEqual(outcome["first_mismatch_frame"], 7)
        self.assertEqual(
            outcome["frames"][6]["mismatching_noncycle_color_indices"], [1])

    def test_wrong_cycle_definition_rejected(self):
        self.rows[0]["delay_counter_units"] = 5
        with self.assertRaisesRegex(SavedCounterForecastError, "differs from archive"):
            self.predict()

    def test_invalid_timer_pair_rejected(self):
        self.samples[4]["timer_pair"] = [1, -1]
        with self.assertRaisesRegex(SavedCounterForecastError, "Invalid timer pair"):
            self.predict()

    def test_bad_palettes_are_rejected(self):
        self.samples[2]["post_palette"] = b"short"
        with self.assertRaisesRegex(SavedCounterForecastError, "post palette"):
            self.predict()

    def test_duplicate_or_missing_cycle_rows_rejected(self):
        self.rows[1] = copy.deepcopy(self.rows[0])
        with self.assertRaisesRegex(SavedCounterForecastError, "IDs differ"):
            self.predict()
