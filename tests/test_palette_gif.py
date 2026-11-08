"""GIF-preview timeline, encoding, and error regressions using synthetic SCUMM data."""
from __future__ import annotations

import contextlib
from hashlib import sha256
from importlib.util import find_spec
from io import StringIO, BytesIO
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from scummbucket.cli import main
from scummbucket.palette_gif import (
    SequenceError, build_gif_timeline, encode_gif_verified, export_palette_gif
)
from test_inspector import index, make_zip
from test_palette_probe import fixture

PIL_AVAILABLE = find_spec("PIL") is not None


def sample_values():
    palette = bytearray(768)
    palette[5 * 3:5 * 3 + 3] = b"\xff\x00\x00"
    palette[6 * 3:6 * 3 + 3] = b"\x00\x00\xff"
    palette[7 * 3:7 * 3 + 3] = b"\x00\xff\x00"
    palette[8 * 3:8 * 3 + 3] = b"\xff\xff\x00"
    indices = bytes([5, 6] * 32)
    records = [{"id": 1, "rate_raw": 4096, "flags": 0,
                "start_color": 5, "end_color": 6, "offset": 0}]
    return indices, bytes(palette), records


class GifTimelineTest(unittest.TestCase):
    def test_collapse_consecutive_not_all_unique_states(self):
        indices, palette, cycles = sample_values()
        result = build_gif_timeline(
            indices, palette, cycles, width=8, height=8,
            fps=4, frames=12, counter_rate=4)
        self.assertEqual(result["source_frames"], 12)
        self.assertEqual(result["unique_visual_states"], 2)
        self.assertEqual(result["modeled_rotation_count"], 2)
        self.assertEqual(len(result["segments"]), 3)  # A -> B -> A
        self.assertEqual([(s["start_source_frame"],
                           s["end_source_frame_exclusive"])
                          for s in result["segments"]], [(0, 4), (4, 8), (8, 12)])
        self.assertEqual([s["duration_ms"] for s in result["segments"]],
                         [1000, 1000, 1000])
        self.assertEqual(result["duration_encoded_ms"], 3000)
        self.assertEqual([e["sample_frame"] for e in result["palette_events"]], [4, 8])
        self.assertTrue(all(not e["observed_engine_event"]
                            for e in result["palette_events"]))

    def test_unused_palette_rotation_is_kept_as_event_not_gif_frame(self):
        indices, palette, _ = sample_values()
        unused = [{"id": 2, "rate_raw": 4096, "flags": 0,
                   "start_color": 7, "end_color": 8, "offset": 0}]
        result = build_gif_timeline(
            indices, palette, unused, width=8, height=8,
            fps=4, frames=8, counter_rate=4)
        self.assertEqual(result["unique_visual_states"], 1)
        self.assertEqual(len(result["segments"]), 1)
        self.assertEqual(result["segments"][0]["duration_ms"], 2000)
        self.assertEqual(result["modeled_rotation_count"], 1)
        self.assertEqual(result["palette_events"][0]["affected_indexed_pixel_positions"], 0)

    def test_short_30fps_segments_quantize_without_accumulated_drift(self):
        indices, palette, _ = sample_values()
        fast = [{"id": 1, "rate_raw": 16384, "flags": 0,
                 "start_color": 5, "end_color": 6, "offset": 0}]
        result = build_gif_timeline(
            indices, palette, fast, width=8, height=8,
            fps=30, frames=9, counter_rate=30)
        self.assertEqual(len(result["segments"]), 9)
        self.assertEqual(result["duration_encoded_ms"], 300)
        self.assertEqual([s["duration_ms"] for s in result["segments"]][:3],
                         [30, 40, 30])
        self.assertFalse(result["short_delay_warning"])

    def test_60fps_fast_segments_warn_about_player_delay_clamping(self):
        indices, palette, _ = sample_values()
        fast = [{"id": 1, "rate_raw": 16384, "flags": 0,
                 "start_color": 5, "end_color": 6, "offset": 0}]
        result = build_gif_timeline(
            indices, palette, fast, width=8, height=8,
            fps=60, frames=12, counter_rate=60)
        self.assertTrue(result["short_delay_warning"])
        self.assertEqual(result["duration_encoded_ms"], 200)

    def test_limits_reject_invalid_frames_dimensions_and_clock(self):
        indices, palette, cycles = sample_values()
        for width, height, fps, frames, rate, code in [
            (1, 8, 4, 8, 4, "GIF_DIMENSIONS_INVALID"),
            (8, 8, 0, 8, 4, "GIF_FPS_INVALID"),
            (8, 8, 4, 0, 4, "GIF_FRAME_COUNT_INVALID"),
            (8, 8, 4, 241, 4, "GIF_FRAME_COUNT_INVALID"),
            (8, 8, 4, 8, 0, "GIF_COUNTER_RATE_INVALID"),
        ]:
            with self.subTest(code=code):
                with self.assertRaises(SequenceError) as error:
                    build_gif_timeline(
                        indices, palette, cycles, width=width, height=height,
                        fps=fps, frames=frames, counter_rate=rate)
                self.assertEqual(error.exception.code, code)


@unittest.skipUnless(PIL_AVAILABLE, "GIF tests require optional Pillow")
class GifPillowTest(unittest.TestCase):
    def test_encode_and_roundtrip_multiple_palette_frames(self):
        from PIL import Image
        indices, palette, cycles = sample_values()
        timeline = build_gif_timeline(
            indices, palette, cycles, width=8, height=8,
            fps=4, frames=12, counter_rate=4)
        gif = encode_gif_verified(
            indices, width=8, height=8, segments=timeline["segments"])
        self.assertTrue(gif.startswith(b"GIF89a"))
        with Image.open(BytesIO(gif)) as image:
            self.assertEqual(image.n_frames, 3)
            self.assertNotIn("loop", image.info)
            durations = []
            colors = []
            for i in range(image.n_frames):
                image.seek(i)
                durations.append(image.info.get("duration"))
                colors.append(image.convert("RGB").getpixel((0, 0)))
            self.assertEqual(durations, [1000, 1000, 1000])
            self.assertEqual(colors, [(255, 0, 0), (0, 0, 255), (255, 0, 0)])

    def test_one_segment_still_creates_valid_nonlooping_static_gif(self):
        from PIL import Image
        indices, palette, _ = sample_values()
        unused = [{"id": 2, "rate_raw": 4096, "flags": 0,
                   "start_color": 7, "end_color": 8, "offset": 0}]
        timeline = build_gif_timeline(
            indices, palette, unused, width=8, height=8,
            fps=4, frames=8, counter_rate=4)
        gif = encode_gif_verified(
            indices, width=8, height=8, segments=timeline["segments"])
        with Image.open(BytesIO(gif)) as image:
            self.assertEqual(image.n_frames, 1)
            self.assertEqual(image.info["duration"], 2000)

    def test_encoder_rejects_incomplete_palette(self):
        indices, palette, cycles = sample_values()
        timeline = build_gif_timeline(
            indices, palette, cycles, width=8, height=8,
            fps=4, frames=8, counter_rate=4)
        timeline["segments"][1]["_palette"] = b"\x01"
        with self.assertRaises(SequenceError) as error:
            encode_gif_verified(indices, width=8, height=8,
                                segments=timeline["segments"])
        self.assertEqual(error.exception.code, "GIF_PALETTE_INVALID")


@unittest.skipUnless(PIL_AVAILABLE, "GIF tests require optional Pillow")
class GifExporterTest(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.root = Path(temp.name)
        self.archive = self.root / "game.zip"
        self.gif = self.root / "previews" / "room1.gif"
        make_zip(self.archive, a=index(), b=fixture())

    def export(self, **kwargs):
        return export_palette_gif(
            self.archive, self.gif,
            room_id=1, fps=4, duration_seconds=3, counter_rate=4, **kwargs)

    def test_real_gif_preview_manifest_and_source_read_only(self):
        from PIL import Image
        source_sha = sha256(self.archive.read_bytes()).hexdigest()
        report = self.export()
        self.assertEqual(report["status"], "success", report["diagnostics"])
        self.assertEqual(report["summary"]["source_frames_sampled"], 12)
        self.assertEqual(report["summary"]["gif_frames_written"], 3)
        self.assertEqual(report["summary"]["unique_visual_states"], 2)
        self.assertEqual(report["summary"]["palette_rotation_events"], 2)
        self.assertEqual(report["summary"]["cycle_definitions"], 1)
        self.assertEqual(report["summary"]["unique_source_cycle_pixels"], 64)
        self.assertEqual(report["timing"]["gif_duration_ms"], 3000)
        self.assertFalse(report["timing"]["gif_loops"])
        self.assertFalse(report["timing"]["engine_timer_values_observed"])
        self.assertTrue(report["fidelity"]["rendered_rgb_roundtrip_verified"])
        self.assertEqual(len(report["segments"]), 3)
        self.assertEqual(len(report["palette_events"]), 2)
        self.assertTrue(all("_palette" not in segment for segment in report["segments"]))
        self.assertEqual(source_sha, sha256(self.archive.read_bytes()).hexdigest())
        gif = self.gif.read_bytes()
        self.assertEqual(sha256(gif).hexdigest(), report["files"][0]["sha256"])
        with Image.open(self.gif) as image:
            self.assertEqual(image.n_frames, 3)
            self.assertNotIn("loop", image.info)
        stored = json.loads(self.gif.with_suffix(".manifest.json").read_text())
        self.assertEqual(stored["status"], "success")
        self.assertEqual(stored["files"][0]["sha256"], sha256(gif).hexdigest())

    def test_existing_gif_or_manifest_refused_without_overwrite(self):
        self.gif.parent.mkdir()
        self.gif.write_bytes(b"KEEP")
        result = self.export()
        self.assertEqual(result["status"], "failed")
        self.assertEqual(self.gif.read_bytes(), b"KEEP")
        self.assertIn("OUTPUT_COLLISION", [d["code"] for d in result["diagnostics"]])
        self.gif.unlink()
        self.gif.with_suffix(".manifest.json").write_text("KEEP")
        result = self.export()
        self.assertEqual(result["status"], "failed")
        self.assertEqual(self.gif.with_suffix(".manifest.json").read_text(), "KEEP")
        self.assertFalse(self.gif.exists())

    def test_missing_optional_encoder_reports_actionable_error(self):
        with patch("scummbucket.palette_gif._pillow_image",
                   side_effect=SequenceError("GIF_DEPENDENCY_MISSING", "Install Pillow")):
            report = self.export()
        self.assertEqual(report["status"], "failed")
        self.assertIn("GIF_DEPENDENCY_MISSING",
                      [d["code"] for d in report["diagnostics"]])
        self.assertFalse(self.gif.exists())

    def test_no_visible_cycle_pixels_retains_warning_and_event_log(self):
        # Fixture's source bitmap uses colors 5 and 6 only.
        # A very short sample with no updates is explicitly reported.
        result = export_palette_gif(
            self.archive, self.gif, room_id=1,
            fps=1, duration_seconds=1, counter_rate=1)
        self.assertEqual(result["status"], "success")
        codes = [d["code"] for d in result["diagnostics"]]
        self.assertIn("GIF_SINGLE_VISUAL_FRAME", codes)
        self.assertIn("GIF_NO_ROTATIONS", codes)
        self.assertEqual(result["summary"]["gif_frames_written"], 1)

    def test_invalid_params_fail_before_creating_output(self):
        for kwargs, code in [
            ({"room_id": -1}, "ROOM_ID_INVALID"),
            ({"fps": 0}, "GIF_FPS_INVALID"),
            ({"duration_seconds": 0}, "GIF_DURATION_INVALID"),
            ({"counter_rate": 0}, "GIF_COUNTER_RATE_INVALID"),
            ({"fps": 60, "duration_seconds": 5}, "GIF_FRAME_LIMIT"),
        ]:
            with self.subTest(code=code):
                result = export_palette_gif(
                    self.archive, self.gif,
                    **({"room_id": 1} | kwargs))
                self.assertEqual(result["status"], "failed")
                self.assertIn(code, [d["code"] for d in result["diagnostics"]])
                self.assertFalse(self.gif.exists())

    def test_unsupported_codec_and_missing_room_are_diagnostic(self):
        make_zip(self.archive, a=index(), b=fixture(image_code=251))
        result = self.export()
        self.assertEqual(result["status"], "failed")
        self.assertIn("STRIP_CODEC_UNSUPPORTED",
                      [d["code"] for d in result["diagnostics"]])
        result = export_palette_gif(
            self.archive, self.gif, room_id=99,
            fps=4, duration_seconds=3, counter_rate=4)
        self.assertEqual(result["status"], "failed")
        self.assertIn("GIF_ROOM_NOT_FOUND",
                      [d["code"] for d in result["diagnostics"]])

    def test_cli_file_output_and_failure_exit_code(self):
        argv = ["palette-gif", str(self.archive), "--room", "1",
                "--fps", "4", "--duration-seconds", "3", "--counter-rate", "4",
                "--output", str(self.gif)]
        text = StringIO()
        with contextlib.redirect_stdout(text):
            self.assertEqual(main(argv), 0)
        self.assertIn("3 GIF frames from 12 sampled", text.getvalue())
        self.assertIn("GIF plays once", text.getvalue())
        with contextlib.redirect_stdout(StringIO()), contextlib.redirect_stderr(StringIO()):
            self.assertEqual(main(argv), 2)


if __name__ == "__main__":
    unittest.main()
