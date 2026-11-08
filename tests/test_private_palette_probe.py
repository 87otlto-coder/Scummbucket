"""Optional original DOS MI2 palette-cycle research regression.

No game assets are committed. Set SCUMMBUCKET_MI2_ARCHIVE locally to run.
This validates original resource structure, pixel-index fingerprints and
hypothetical palette snapshots; it is NOT a gameplay/rendering reference test.
"""
import hashlib
import os
from pathlib import Path
import tempfile
import unittest

from scummbucket.inspector import XOR_KEY, inspect, _read_pair
from scummbucket.palette_coverage import analyze_cycle_coverage
from scummbucket.palette_sequence import export_palette_sequence
from scummbucket.palette_probe import (
    decode_room_background_indexed, palette_probe,
)

ARCHIVE = os.environ.get("SCUMMBUCKET_MI2_ARCHIVE")
EXPECTED_RESOURCE_SHA256 = "ad045372e0d49626503bb50fca29a687ec8e01ef75d9b8bca702a366d143819e"


@unittest.skipUnless(ARCHIVE, "Private original-game archive not provided")
class PrivatePaletteProbeTest(unittest.TestCase):
    def test_room23_native_indexed_sequence_first_rotation_and_manifest(self):
        source = Path(ARCHIVE)
        with tempfile.TemporaryDirectory() as tempdir:
            result = export_palette_sequence(
                source, Path(tempdir) / "frames", room_id=23,
                fps=30, duration_seconds=4, counter_rate=60)
            self.assertEqual(result["status"], "success", result["diagnostics"])
            self.assertEqual(result["provenance"]["resource_sha256"],
                             EXPECTED_RESOURCE_SHA256)
            self.assertEqual(result["provenance"]["native_size"], [320, 144])
            self.assertEqual(result["summary"]["frames_requested"], 120)
            self.assertEqual(result["summary"]["frames_written"], 120)
            self.assertEqual(result["summary"]["cycle_records"], 8)
            self.assertEqual(result["summary"]["unique_cycled_source_pixels"], 480)
            self.assertEqual(result["timing"]["model"],
                             "video_calibrated_60_units_per_second_hypothesis")
            self.assertFalse(result["timing"]["engine_timer_values_observed"])
            self.assertFalse(result["timing"]["seamless_loop_verified"])
            self.assertEqual(result["frames"][0]["counter_delta"], 0)
            self.assertEqual(result["frames"][18]["cumulative_counter_units"], 36)
            self.assertEqual(result["frames"][36]["cumulative_counter_units"], 72)
            self.assertTrue(any(event["cycle_id"] == 5
                                for event in result["frames"][18]["rotations_this_frame"]))
            self.assertTrue(any(event["cycle_id"] == 1
                                for event in result["frames"][36]["rotations_this_frame"]))
            self.assertNotEqual(result["frames"][0]["palette_sha256"],
                                result["frames"][36]["palette_sha256"])
            self.assertEqual(len(result["files"]), 122)
            self.assertTrue((Path(tempdir) / "frames" / "manifest.json").is_file())

    def test_room23_and_109_indexed_pixel_fingerprints_and_visible_cycles(self):
        source = Path(ARCHIVE)
        report = inspect(source)
        self.assertEqual(report["status"], "success", report["diagnostics"])
        self.assertEqual(report["sources"][1]["sha256"], EXPECTED_RESOURCE_SHA256)
        _, raw, _, _ = _read_pair(source)
        self.assertEqual(hashlib.sha256(raw).hexdigest(), EXPECTED_RESOURCE_SHA256)
        decoded = bytes(b ^ XOR_KEY for b in raw)
        cases = (
            (23, "94b7b2d675778bf73c73a87eca05ab74dca470ad67555faecd03ab112acbcd9f",
             8, 480, [0, 65, 373]),
            (109, "47adf2c2d270f2cabaeca483feadd5b5c1d524b7c64df2d1a14a3356adfcca79",
             5, 65, [0, 50, 30]),
        )
        for room_id, hash_expected, cycle_count, visible_pixels, changed_counts in cases:
            with self.subTest(room_id=room_id):
                room = next(r for r in report["resources"]["rooms"] if r["id"] == room_id)
                bg = decode_room_background_indexed(
                    decoded, room_offset=room["room_offset"], room_length=room["room_size"])
                self.assertEqual(bg["pixel_indices_sha256"], hash_expected)
                coverage, masks = analyze_cycle_coverage(
                    bg["indexed_pixels"], width=bg["width"], height=bg["height"],
                    records=room["palette_cycles"])
                self.assertEqual(coverage["union_pixel_count"], visible_pixels)
                self.assertEqual(coverage["cycle_records"], cycle_count)
                self.assertEqual(coverage["union_pixel_count"],
                                 sum(value > 0 for value in masks[0]))
                if room_id == 23:
                    self.assertEqual(
                        [c["native_pixel_count"] for c in coverage["cycles"]],
                        [90, 55, 42, 75, 65, 49, 84, 20])
                    self.assertTrue(all(
                        c["native_bounds_xyxy_inclusive"][1] >= 52
                        for c in coverage["cycles"]))
                self.assertEqual(bg["width"], 320)
                self.assertEqual(len(bg["strips"]), 40)
                self.assertTrue(all(strip["codec"] == 68 for strip in bg["strips"]))
                with tempfile.TemporaryDirectory() as tempdir:
                    result = palette_probe(source, Path(tempdir) / "frames",
                                           room_id=room_id, ticks=[0, 35, 71])
                    self.assertEqual(result["status"], "success", result["diagnostics"])
                    self.assertEqual(result["summary"]["cycle_records"], cycle_count)
                    self.assertEqual(result["summary"]["visible_cycle_pixels"], visible_pixels)
                    self.assertEqual(
                        [s["visible_changed_pixels_vs_initial"] for s in result["snapshots"]],
                        changed_counts)
                    self.assertFalse(result["verification"]["runtime_observed"])
                    self.assertFalse(result["verification"]["rendering_reference_verified"])


if __name__ == "__main__":
    unittest.main()
