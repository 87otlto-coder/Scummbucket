"""Saved palette event bundle rendering tests; synthetic game resources only."""
from __future__ import annotations

import contextlib
from hashlib import sha256
from io import StringIO
import json
from pathlib import Path
import tempfile
import unittest

from scummbucket.cli import main
from scummbucket.palette_events import export_palette_events
from scummbucket.palette_bundle_render import (
    read_palette_event_bundle, read_bundle_indexed_png,
    render_palette_event_bundle,
)
from scummbucket.palette_sequence import SequenceError
from test_inspector import index, make_zip
from test_palette_probe import fixture
from test_palette_sequence import parse_indexed_png


class SourceBundleRenderTest(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.archive = self.root / "source.zip"
        self.bundle_dir = self.root / "original-event-bundle"
        self.output = self.root / "renderer-output"
        make_zip(self.archive, a=index(), b=fixture())
        result = export_palette_events(
            self.archive, self.bundle_dir,
            room_id=1, counter_rate=4, duration_seconds=3)
        self.assertEqual(result["status"], "success", result["diagnostics"])

    def render(self, *, fps=4, output=None):
        return render_palette_event_bundle(
            self.bundle_dir, output or self.output, fps=fps)

    def test_roundtrip_at_different_fps_replays_identical_source_without_archive(self):
        original_sha = sha256(self.archive.read_bytes()).hexdigest()
        original_bundle_sha = sha256(
            (self.bundle_dir / "timeline.json").read_bytes()).hexdigest()
        # Remove proprietary-resource fixture: only the saved bundle may be used.
        self.archive.unlink()
        self.assertFalse(self.archive.exists())
        results = []
        for fps in (2, 4, 8):
            target = self.root / f"render-{fps}"
            result = self.render(fps=fps, output=target)
            self.assertEqual(result["status"], "success", result["diagnostics"])
            self.assertEqual(result["frames_written"], fps * 3)
            self.assertTrue(result["provenance"]["rendered_from_saved_patches_only"])
            self.assertFalse(result["provenance"]["source_game_archive_reopened"])
            self.assertEqual(
                result["provenance"]["bundle_manifest_sha256"],
                original_bundle_sha)
            self.assertFalse(result["timing"]["engine_timer_values_observed"])
            self.assertEqual(len(result["files"]), fps * 3)
            images = []
            for i in range(result["frames_written"]):
                filename = f"room-001_event-frame-{i:04d}.png"
                data = (target / filename).read_bytes()
                width, height, pixels, pal = parse_indexed_png(data)
                self.assertEqual((width, height), (8, 8))
                self.assertEqual(pixels, bytes(([5, 6] * 4) * 8))
                self.assertEqual(
                    sha256(data).hexdigest(), result["files"][i]["sha256"])
                self.assertEqual(
                    sha256(pal).hexdigest(),
                    result["files"][i]["source_palette_sha256"])
                images.append(pal)
            self.assertNotEqual(images[0], images[fps])
            self.assertEqual(images[0], images[2 * fps])
            saved = json.loads((target / "render-manifest.json").read_text())
            self.assertEqual(saved["status"], "success")
            self.assertEqual(saved["frames_written"], 3 * fps)
            results.append(images)
        self.assertEqual(results[0][2], results[1][4])
        self.assertEqual(results[1][4], results[2][8])
        self.assertEqual(results[0][4], results[2][16])
        self.assertEqual(
            sha256((self.bundle_dir / "timeline.json").read_bytes()).hexdigest(),
            original_bundle_sha)

    def test_fps_sampling_does_not_hide_intermediate_states(self):
        # Counter rate 4, rotations at ticks 4 and 8; a one-fps
        # renderer samples only 0,4,8, so both states appear.
        result = self.render(fps=1)
        self.assertEqual(result["status"], "success", result["diagnostics"])
        self.assertEqual(result["sampling"]["event_states_not_sampled"], 0)
        self.assertEqual(result["frames_written"], 3)

    def test_missing_or_corrupted_source_sidecars_have_explicit_diagnostics(self):
        png = self.bundle_dir / "room-001_indexed.png"
        corrupt = bytearray(png.read_bytes())
        corrupt[-8] ^= 1
        png.write_bytes(corrupt)
        result = self.render()
        self.assertEqual(result["status"], "failed")
        self.assertIn("EVENT_BUNDLE_FILE_HASH_MISMATCH",
                      [d["code"] for d in result["diagnostics"]])
        self.assertFalse(self.output.exists())

    def test_original_palette_file_and_png_must_match(self):
        clut = self.bundle_dir / "room-001_initial-clut.rgb"
        clut.write_bytes(b"\x01" * 768)
        result = self.render()
        self.assertEqual(result["status"], "failed")
        self.assertIn("EVENT_BUNDLE_FILE_HASH_MISMATCH",
                      [d["code"] for d in result["diagnostics"]])

    def test_corrupted_event_patch_fails_before_any_raster_is_written(self):
        path = self.bundle_dir / "timeline.json"
        stored = json.loads(path.read_text())
        stored["timeline"]["events"][-1]["palette_patches"][0]["after_rgb_hex"] = "abcdef"
        path.write_text(json.dumps(stored))
        result = self.render(fps=1)
        self.assertEqual(result["status"], "failed")
        self.assertIn("EVENT_AFTER_HASH_MISMATCH",
                      [d["code"] for d in result["diagnostics"]])
        self.assertFalse(self.output.exists())

    def test_existing_destination_never_overwritten(self):
        self.output.mkdir()
        file = self.output / "room-001_event-frame-0002.png"
        file.write_text("PRESERVE")
        report = self.render(fps=4)
        self.assertEqual(report["status"], "failed")
        self.assertIn("OUTPUT_COLLISION",
                      [d["code"] for d in report["diagnostics"]])
        self.assertEqual(file.read_text(), "PRESERVE")
        self.assertEqual(len(list(self.output.iterdir())), 1)

    def test_manifest_status_must_be_successful(self):
        path = self.bundle_dir / "timeline.json"
        obj = json.loads(path.read_text())
        obj["status"] = "partial"
        path.write_text(json.dumps(obj))
        result = self.render()
        self.assertEqual(result["status"], "failed")
        self.assertIn("EVENT_BUNDLE_SCHEMA_UNSUPPORTED",
                      [d["code"] for d in result["diagnostics"]])

    def test_invalid_fps_and_zero_length_png_are_rejected(self):
        result = self.render(fps=0)
        self.assertEqual(result["status"], "failed")
        self.assertIn("EVENT_RENDER_FPS_INVALID",
                      [d["code"] for d in result["diagnostics"]])
        with self.assertRaises(SequenceError) as error:
            read_bundle_indexed_png(b"")
        self.assertEqual(error.exception.code, "EVENT_PNG_SIGNATURE_INVALID")

    def test_cli_prints_important_provenance_limitations(self):
        args = ["render-events", str(self.bundle_dir),
                "--fps", "4", "--output-dir", str(self.output)]
        out = StringIO()
        with contextlib.redirect_stdout(out):
            self.assertEqual(main(args), 0)
        self.assertIn("Frames: 12 at 4 fps", out.getvalue())
        self.assertIn("no original archive reopened", out.getvalue())
        self.assertIn("not an observed ScummVM engine clock", out.getvalue())
        with contextlib.redirect_stdout(StringIO()), contextlib.redirect_stderr(StringIO()):
            self.assertEqual(main(args), 2)

    def test_inherited_warnings_are_not_silenced(self):
        # Archive-wide and room-local warnings pass through the bundle to
        # the downstream renderer, not just the initial inspection.
        path = self.bundle_dir / "timeline.json"
        obj = json.loads(path.read_text())
        obj["diagnostics"].append({
            "severity": "warning", "code": "CYCLE_FLAGS_UNVERIFIED",
            "message": "Synthetic unknown bits", "source": "test source",
        })
        path.write_text(json.dumps(obj))
        report = self.render()
        self.assertEqual(report["status"], "success", report["diagnostics"])
        self.assertIn("CYCLE_FLAGS_UNVERIFIED",
                      [x["code"] for x in report["diagnostics"]])


class BundleFormatTest(unittest.TestCase):
    def test_native_png_parser_checks_crc_and_pixel_dimensions(self):
        from scummbucket.palette_sequence import encode_indexed_png
        payload = encode_indexed_png(
            2, 2, bytes([1, 2, 3, 4]), bytes(range(256)) * 3)
        self.assertEqual(
            read_bundle_indexed_png(payload),
            (2, 2, bytes([1, 2, 3, 4]), bytes(range(256)) * 3))
        corrupt = bytearray(payload)
        corrupt[32] ^= 1
        with self.assertRaises(SequenceError) as err:
            read_bundle_indexed_png(bytes(corrupt))
        self.assertEqual(err.exception.code, "EVENT_PNG_CRC_INVALID")


if __name__ == "__main__":
    unittest.main()
