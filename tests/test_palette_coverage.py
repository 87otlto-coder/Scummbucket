"""Source pixel-coordinate coverage for CYCL ranges, with synthetic fixtures.

These tests do not establish that gameplay executes a cycle or that any
on-screen effect is caused by a particular palette definition.
"""
from __future__ import annotations

import contextlib
import hashlib
import io
import json
from pathlib import Path
import struct
import tempfile
import unittest

from scummbucket.cli import main
from scummbucket.palette_coverage import (
    analyze_cycle_coverage, export_cycle_coverage,
)
from scummbucket.palette_probe import PaletteProbeError
from test_inspector import index, make_zip
from test_palette_probe import fixture


def cycle(cid: int, start: int, end: int) -> dict:
    return {"id": cid, "rate_raw": 4096, "flags": 0,
            "start_color": start, "end_color": end, "offset": 25}


class PaletteCoverageMathTest(unittest.TestCase):
    def test_all_pixels_covered_without_double_count(self):
        values = bytes([5, 6, 7, 8])
        summary, masks = analyze_cycle_coverage(
            values, width=4, height=1,
            records=[cycle(1, 5, 6), cycle(2, 6, 7)])
        self.assertEqual(summary["union_pixel_count"], 3)
        self.assertEqual(summary["total_native_pixels"], 4)
        self.assertEqual(summary["union_fraction"], 0.75)
        self.assertEqual([c["native_pixel_count"] for c in summary["cycles"]],
                         [2, 2])
        self.assertEqual([c["native_bounds_xyxy_inclusive"] for c in summary["cycles"]],
                         [[0, 0, 1, 0], [1, 0, 2, 0]])
        self.assertEqual(masks[0], bytes([255, 255, 255, 0]))
        self.assertEqual(masks[1], bytes([255, 255, 0, 0]))
        self.assertEqual(masks[2], bytes([0, 255, 255, 0]))
        self.assertEqual(summary["union_mask_sha256"],
                         hashlib.sha256(masks[0]).hexdigest())

    def test_empty_cycle_color_range_visible_count_zero(self):
        summary, masks = analyze_cycle_coverage(
            bytes([5, 5, 6, 6]), width=2, height=2,
            records=[cycle(1, 100, 101)])
        self.assertEqual(summary["union_pixel_count"], 0)
        self.assertEqual(summary["cycles"][0]["native_bounds_xyxy_inclusive"], None)
        self.assertEqual(masks[0], bytes(4))

    def test_invalid_dimensions_and_duplicate_cycle_rejected(self):
        with self.assertRaises(PaletteProbeError) as error:
            analyze_cycle_coverage(bytes([5]), width=2, height=1, records=[])
        self.assertEqual(error.exception.code, "COVERAGE_DIMENSIONS_INVALID")
        with self.assertRaises(PaletteProbeError):
            analyze_cycle_coverage(
                bytes([5]), width=1, height=1,
                records=[cycle(1, 5, 6), cycle(1, 6, 7)])


class PaletteCoverageExportTest(unittest.TestCase):
    def setUp(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.root = Path(directory.name)
        self.source = self.root / "synthetic.zip"
        self.target = self.root / "coverage"
        make_zip(self.source, a=index(), b=fixture())

    def test_export_one_overlay_and_one_native_mask(self):
        original_bytes = self.source.read_bytes()
        report = export_cycle_coverage(
            self.source, self.target, room_id=1)
        self.assertEqual(report["status"], "success", report["diagnostics"])
        self.assertEqual(report["summary"]["union_pixel_count"], 64)
        self.assertEqual(report["summary"]["cycle_records"], 1)
        self.assertEqual(report["summary"]["cycles"][0]["native_bounds_xyxy_inclusive"],
                         [0, 0, 7, 7])
        self.assertEqual(len(report["files"]), 2)
        self.assertEqual(report["evidence_level"],
                         "directly_decoded_source_pixels_and_CYCL_ranges")
        self.assertFalse(report["runtime_palette_changes_observed"])
        self.assertFalse(report["animation_timing_verified"])
        for file in report["files"]:
            png = (self.target / file["name"]).read_bytes()
            self.assertTrue(png.startswith(b"\x89PNG\r\n\x1a\n"))
            self.assertEqual(struct.unpack_from(">II", png, 16), (8, 8))
            self.assertEqual(hashlib.sha256(png).hexdigest(), file["sha256"])
        saved = json.loads((self.target / "manifest.json").read_text())
        self.assertEqual(saved["summary"]["union_pixel_count"], 64)
        self.assertEqual(self.source.read_bytes(), original_bytes)

    def test_missing_room_explicit_failure(self):
        report = export_cycle_coverage(
            self.source, self.target, room_id=99)
        self.assertEqual(report["status"], "failed")
        self.assertIn("COVERAGE_ROOM_NOT_FOUND",
                      [x["code"] for x in report["diagnostics"]])
        self.assertFalse(self.target.exists())

    def test_unsupported_source_codec_is_not_silent(self):
        make_zip(self.source, a=index(), b=fixture(image_code=251))
        report = export_cycle_coverage(
            self.source, self.target, room_id=1)
        self.assertEqual(report["status"], "failed")
        self.assertIn("STRIP_CODEC_UNSUPPORTED",
                      [x["code"] for x in report["diagnostics"]])
        self.assertFalse((self.target / "manifest.json").exists())

    def test_existing_manifest_never_overwritten(self):
        self.target.mkdir()
        (self.target / "manifest.json").write_text("KEEP")
        report = export_cycle_coverage(self.source, self.target, room_id=1)
        self.assertEqual(report["status"], "failed")
        self.assertIn("OUTPUT_COLLISION",
                      [x["code"] for x in report["diagnostics"]])
        self.assertEqual((self.target / "manifest.json").read_text(), "KEEP")

    def test_cli_prints_coordinates_with_no_runtime_claim(self):
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            exitcode = main(["palette-map", str(self.source), "--room", "1",
                             "--output-dir", str(self.target)])
        self.assertEqual(exitcode, 0)
        self.assertIn("64 unique indexed-background pixel positions",
                      output.getvalue())
        self.assertIn("runtime behavior", output.getvalue())
        self.assertIn("Cycle 1:", output.getvalue())

    def test_invalid_room_is_error(self):
        report = export_cycle_coverage(self.source, self.target, room_id=-1)
        self.assertEqual(report["status"], "failed")
        self.assertIn("ROOM_ID_INVALID", [x["code"] for x in report["diagnostics"]])


if __name__ == "__main__":
    unittest.main()
