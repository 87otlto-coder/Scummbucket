"""Event-bundle GIF regression tests; synthetic SCUMM fixtures only."""
from __future__ import annotations

import contextlib
from hashlib import sha256
from importlib.util import find_spec
from io import BytesIO, StringIO
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from scummbucket.cli import main
from scummbucket.palette_events import export_palette_events
from scummbucket.palette_event_gif import (
    build_event_gif_timeline, export_palette_event_gif,
)
from scummbucket.palette_bundle_render import read_palette_event_bundle
from test_inspector import index, make_zip
from test_palette_probe import fixture

PIL_AVAILABLE = find_spec("PIL") is not None


class EventGifTest(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.root = Path(tmp.name)
        self.archive = self.root / "fixture.zip"
        self.bundle = self.root / "original-bundle"
        self.output = self.root / "preview.gif"
        make_zip(self.archive, a=index(), b=fixture())
        result = export_palette_events(
            self.archive, self.bundle, room_id=1,
            counter_rate=4, duration_seconds=3)
        self.assertEqual(result["status"], "success", result["diagnostics"])

    def test_event_boundaries_collapse_only_consecutive_visual_repetitions(self):
        original = read_palette_event_bundle(self.bundle)
        model = build_event_gif_timeline(original)
        self.assertEqual(model["source_event_ticks"], 2)
        self.assertEqual(model["visible_event_boundaries"], 2)
        self.assertEqual(model["nonvisual_event_ticks"], 0)
        self.assertEqual(model["unique_visual_states"], 2)
        self.assertEqual([s["start_counter_tick"] for s in model["segments"]],
                         [0, 4, 8])
        self.assertEqual([s["duration_ms"] for s in model["segments"]],
                         [1000, 1000, 1000])
        self.assertEqual(model["duration_encoded_ms"], 3000)

    @unittest.skipUnless(PIL_AVAILABLE, "Pillow GIF extra not installed")
    def test_gif_roundtrip_from_saved_patches_without_original_archive(self):
        from PIL import Image
        original_bundle_hash = sha256((self.bundle / "timeline.json").read_bytes()).hexdigest()
        self.archive.unlink()
        report = export_palette_event_gif(self.bundle, self.output)
        self.assertEqual(report["status"], "success", report["diagnostics"])
        self.assertEqual(report["summary"]["gif_frames_written"], 3)
        self.assertEqual(report["summary"]["duration_encoded_ms"], 3000)
        self.assertTrue(report["provenance"]["rendered_from_saved_patches_only"])
        self.assertFalse(report["provenance"]["source_game_archive_reopened"])
        self.assertEqual(report["provenance"]["bundle_manifest_sha256"], original_bundle_hash)
        self.assertFalse(report["timing"]["real_engine_update_schedule_verified"])
        self.assertFalse(report["timing"]["gif_loops"])
        self.assertTrue(report["fidelity"]["rendered_rgb_roundtrip_verified"])
        self.assertEqual(sha256(self.output.read_bytes()).hexdigest(),
                         report["files"][0]["sha256"])
        with Image.open(self.output) as gif:
            self.assertEqual(gif.n_frames, 3)
            self.assertNotIn("loop", gif.info)
            durations = []
            for frame in range(gif.n_frames):
                gif.seek(frame)
                durations.append(gif.info["duration"])
            self.assertEqual(durations, [1000, 1000, 1000])
        saved = json.loads(self.output.with_suffix(".manifest.json").read_text())
        self.assertEqual(saved["status"], "success")
        self.assertEqual(len(saved["segments"]), 3)
        self.assertEqual(sha256((self.bundle / "timeline.json").read_bytes()).hexdigest(),
                         original_bundle_hash)

    @unittest.skipUnless(PIL_AVAILABLE, "Pillow GIF extra not installed")
    def test_short_lived_states_not_lost_to_one_fps_sampling(self):
        quicker = self.root / "quicker"
        source = export_palette_events(
            self.archive, quicker, room_id=1,
            counter_rate=8, duration_seconds=3)
        self.assertEqual(source["status"], "success")
        self.assertEqual(len(source["timeline"]["events"]), 5)
        report = export_palette_event_gif(quicker, self.output)
        self.assertEqual(report["status"], "success", report["diagnostics"])
        self.assertEqual(report["summary"]["original_event_ticks"], 5)
        self.assertEqual(report["summary"]["visible_event_boundaries"], 5)
        self.assertEqual(report["summary"]["gif_frames_written"], 6)
        self.assertEqual([s["duration_ms"] for s in report["segments"]],
                         [500] * 6)

    @unittest.skipUnless(PIL_AVAILABLE, "Pillow GIF extra not installed")
    def test_corrupted_saved_patch_fails_before_writing(self):
        path = self.bundle / "timeline.json"
        manifest = json.loads(path.read_text())
        manifest["timeline"]["events"][-1]["palette_patches"][0]["after_rgb_hex"] = "ffffff"
        path.write_text(json.dumps(manifest))
        report = export_palette_event_gif(self.bundle, self.output)
        self.assertEqual(report["status"], "failed")
        self.assertIn("EVENT_AFTER_HASH_MISMATCH",
                      [d["code"] for d in report["diagnostics"]])
        self.assertFalse(self.output.exists())

    def test_existing_output_or_manifest_is_never_overwritten(self):
        self.output.write_bytes(b"PRESERVE")
        report = export_palette_event_gif(self.bundle, self.output)
        self.assertEqual(report["status"], "failed")
        self.assertIn("OUTPUT_COLLISION", [d["code"] for d in report["diagnostics"]])
        self.assertEqual(self.output.read_bytes(), b"PRESERVE")
        self.output.unlink()
        sidecar = self.output.with_suffix(".manifest.json")
        sidecar.write_text("PRESERVE")
        report = export_palette_event_gif(self.bundle, self.output)
        self.assertEqual(report["status"], "failed")
        self.assertFalse(self.output.exists())
        self.assertEqual(sidecar.read_text(), "PRESERVE")

    @unittest.skipUnless(PIL_AVAILABLE, "Pillow GIF extra not installed")
    def test_source_warnings_are_preserved(self):
        path = self.bundle / "timeline.json"
        manifest = json.loads(path.read_text())
        manifest["diagnostics"].append({
            "severity": "warning", "code": "CYCLE_FLAGS_UNVERIFIED",
            "message": "synthetic warning", "source": "fixture",
        })
        path.write_text(json.dumps(manifest))
        report = export_palette_event_gif(self.bundle, self.output)
        self.assertEqual(report["status"], "success", report["diagnostics"])
        self.assertIn("CYCLE_FLAGS_UNVERIFIED",
                      [d["code"] for d in report["diagnostics"]])

    @unittest.skipUnless(PIL_AVAILABLE, "Pillow GIF extra not installed")
    def test_invalid_extension_and_corrupted_source_fail_without_writing(self):
        report = export_palette_event_gif(self.bundle, self.root / "invalid.png")
        self.assertEqual(report["status"], "failed")
        self.assertIn("EVENT_GIF_OUTPUT_EXTENSION",
                      [d["code"] for d in report["diagnostics"]])
        source = self.bundle / "room-001_indexed.png"
        data = bytearray(source.read_bytes())
        data[50] ^= 1
        source.write_bytes(data)
        report = export_palette_event_gif(self.bundle, self.output)
        self.assertEqual(report["status"], "failed")
        self.assertIn("EVENT_BUNDLE_FILE_HASH_MISMATCH",
                      [d["code"] for d in report["diagnostics"]])
        self.assertFalse(self.output.exists())

    @unittest.skipUnless(PIL_AVAILABLE, "Pillow GIF extra not installed")
    def test_cli_command_and_nonoverwriting_failure_exit(self):
        out = StringIO()
        with contextlib.redirect_stdout(out):
            self.assertEqual(main(["render-event-gif", str(self.bundle),
                                   "--output", str(self.output)]), 0)
        self.assertIn("synthetic", out.getvalue())
        self.assertIn("plays once", out.getvalue())
        with contextlib.redirect_stdout(StringIO()), contextlib.redirect_stderr(StringIO()):
            self.assertEqual(main(["render-event-gif", str(self.bundle),
                                   "--output", str(self.output)]), 2)


if __name__ == "__main__":
    unittest.main()
