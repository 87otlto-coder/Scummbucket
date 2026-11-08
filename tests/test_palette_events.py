"""Counter-unit palette timeline tests using synthetic room data only.

The model is deliberately separate from PNG/GIF sampling and from real
ScummVM engine timing. No game assets are embedded in the repository.
"""
from __future__ import annotations

import contextlib
from hashlib import sha256
from io import StringIO
import json
from pathlib import Path
import tempfile
import unittest
from copy import deepcopy

from scummbucket.cli import main
from scummbucket.palette_events import (
    build_counter_event_timeline, replay_event_palettes, export_palette_events,
)
from scummbucket.palette_sequence import SequenceError
from scummbucket.palette_probe import PaletteProbeError
from test_inspector import index, make_zip
from test_palette_probe import fixture
from test_palette_sequence import parse_indexed_png


def source():
    palette = bytearray(768)
    palette[5 * 3:5 * 3 + 3] = b"\xff\x00\x00"
    palette[6 * 3:6 * 3 + 3] = b"\x00\x00\xff"
    palette[7 * 3:7 * 3 + 3] = b"\x00\xff\x00"
    palette[8 * 3:8 * 3 + 3] = b"\xff\xff\x00"
    indices = bytes([5, 6] * 32)
    cycle = {"id": 1, "rate_raw": 4096, "flags": 0,
             "start_color": 5, "end_color": 6, "offset": 29}
    return indices, bytes(palette), [cycle]


class CounterTimelineTest(unittest.TestCase):
    def test_events_independent_of_output_fps(self):
        pixels, palette, cycles = source()
        timeline = build_counter_event_timeline(
            pixels, palette, cycles,
            width=8, height=8, counter_rate=4, duration_seconds=3)
        self.assertEqual(timeline["model"],
                         "synthetic_one_cycle_update_per_counter_unit")
        self.assertFalse(timeline["source_fps_dependency"])
        self.assertEqual(timeline["end_counter_tick_exclusive"], 12)
        self.assertEqual(timeline["modeled_palette_updates"], 11)
        self.assertEqual(timeline["summary"]["event_ticks"], 2)
        self.assertEqual(timeline["summary"]["modeled_cycle_rotations"], 2)
        self.assertEqual(timeline["summary"]["background_pixels_in_cycled_index_ranges"], 64)
        self.assertEqual(timeline["summary"]["unique_full_palette_states_at_events"], 2)
        self.assertEqual([x["counter_tick"] for x in timeline["events"]], [4, 8])
        self.assertEqual([x["visible_source_pixel_positions_changed"]
                          for x in timeline["events"]], [64, 64])
        self.assertEqual(
            [len(x["palette_patches"]) for x in timeline["events"]], [2, 2])
        self.assertFalse(timeline["engine_timer_values_observed"])

        samples_15 = replay_event_palettes(
            palette, timeline["events"], counter_rate=4,
            duration_seconds=3, fps=15)
        samples_30 = replay_event_palettes(
            palette, timeline["events"], counter_rate=4,
            duration_seconds=3, fps=30)
        samples_60 = replay_event_palettes(
            palette, timeline["events"], counter_rate=4,
            duration_seconds=3, fps=60)
        self.assertEqual([len(samples_15), len(samples_30), len(samples_60)],
                         [45, 90, 180])
        self.assertEqual(
            samples_15[15]["palette_sha256"],
            samples_30[30]["palette_sha256"])
        self.assertEqual(
            samples_15[15]["palette_sha256"],
            samples_60[60]["palette_sha256"])
        self.assertEqual(
            samples_15[30]["palette_sha256"],
            samples_30[60]["palette_sha256"])
        self.assertEqual(samples_15[0]["palette_sha256"],
                         samples_15[30]["palette_sha256"])
        self.assertNotEqual(samples_15[0]["palette_sha256"],
                            samples_15[15]["palette_sha256"])

    def test_replay_rejects_corruption_and_out_of_order_events(self):
        pixels, palette, cycles = source()
        timeline = build_counter_event_timeline(
            pixels, palette, cycles,
            width=8, height=8, counter_rate=4, duration_seconds=3)
        events = deepcopy(timeline["events"])
        events[0]["palette_patches"][0]["after_rgb_hex"] = "abcdef"
        with self.assertRaises(SequenceError) as err:
            replay_event_palettes(
                palette, events, counter_rate=4, duration_seconds=3, fps=30)
        self.assertEqual(err.exception.code, "EVENT_AFTER_HASH_MISMATCH")

        events = deepcopy(timeline["events"])
        events[0]["palette_patches"][0]["before_rgb_hex"] = "000000"
        with self.assertRaises(SequenceError) as err:
            replay_event_palettes(
                palette, events, counter_rate=4, duration_seconds=3, fps=30)
        self.assertEqual(err.exception.code, "EVENT_PATCH_BEFORE_MISMATCH")

        events = deepcopy(timeline["events"])
        events[1]["counter_tick"] = 4
        with self.assertRaises(SequenceError) as err:
            replay_event_palettes(
                palette, events, counter_rate=4, duration_seconds=3, fps=30)
        self.assertEqual(err.exception.code, "EVENT_SEQUENCE_INVALID")

    def test_trailing_events_are_validated_even_when_fps_is_low(self):
        pixels, palette, cycles = source()
        timeline = build_counter_event_timeline(
            pixels, palette, cycles, width=8, height=8,
            counter_rate=4, duration_seconds=3)
        corrupt = deepcopy(timeline["events"])
        corrupt[-1]["palette_patches"][0]["after_rgb_hex"] = "abcdef"
        # One output sample at t=0 would not visit the second event at t=2.
        # Replay still verifies the entire exported event record.
        with self.assertRaises(SequenceError) as err:
            replay_event_palettes(
                palette, corrupt, counter_rate=4, duration_seconds=3, fps=1)
        self.assertEqual(err.exception.code, "EVENT_AFTER_HASH_MISMATCH")

    def test_unused_color_range_rotates_but_is_not_visible(self):
        pixels, palette, _ = source()
        records = [{"id": 1, "rate_raw": 4096, "flags": 0,
                    "start_color": 7, "end_color": 8, "offset": 7}]
        result = build_counter_event_timeline(
            pixels, palette, records, width=8, height=8,
            counter_rate=4, duration_seconds=2)
        self.assertEqual(result["summary"]["modeled_cycle_rotations"], 1)
        self.assertEqual(result["summary"]["event_ticks_with_visible_rgb_changes"], 0)
        self.assertEqual(result["summary"]["background_pixels_in_cycled_index_ranges"], 0)
        self.assertEqual(result["events"][0]["visible_source_pixel_positions_changed"], 0)
        self.assertEqual(len(result["events"][0]["palette_patches"]), 2)

    def test_duplicate_or_bad_cycle_is_not_silenced(self):
        pixels, palette, cycles = source()
        for record_set in ([cycles[0], cycles[0]], []):
            with self.subTest(record_count=len(record_set)):
                with self.assertRaises((SequenceError, PaletteProbeError)) as caught:
                    build_counter_event_timeline(
                        pixels, palette, record_set,
                        width=8, height=8, counter_rate=4, duration_seconds=2)
                self.assertIn(caught.exception.code,
                              ("EVENT_NO_CYCLES", "CYCLE_ID_INVALID"))

    def test_bad_parameters_report_distinct_errors(self):
        pixels, palette, cycles = source()
        for change, code in (
            ({"width": 1}, "EVENT_IMAGE_DIMENSIONS_INVALID"),
            ({"counter_rate": 0}, "EVENT_COUNTER_RATE_INVALID"),
            ({"duration_seconds": 0}, "EVENT_DURATION_INVALID"),
            ({"counter_rate": 601}, "EVENT_COUNTER_RATE_INVALID"),
        ):
            with self.subTest(code=code):
                args = dict(width=8, height=8, counter_rate=4, duration_seconds=2)
                args.update(change)
                with self.assertRaises(SequenceError) as caught:
                    build_counter_event_timeline(pixels, palette, cycles, **args)
                self.assertEqual(caught.exception.code, code)


class EventExporterTest(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.root = Path(tmp.name)
        self.archive = self.root / "fixture.zip"
        self.dest = self.root / "events"
        make_zip(self.archive, a=index(), b=fixture())

    def export(self, **kwargs):
        opts = {"room_id": 1, "counter_rate": 4, "duration_seconds": 3}
        opts.update(kwargs)
        return export_palette_events(self.archive, self.dest, **opts)

    def test_exports_replayable_source_bundle_with_provenance(self):
        original = sha256(self.archive.read_bytes()).hexdigest()
        result = self.export()
        self.assertEqual(result["status"], "success", result["diagnostics"])
        self.assertTrue(result["fidelity"]["source_indexed_pixels_preserved"])
        self.assertTrue(result["fidelity"]["initial_source_CLUT_preserved"])
        self.assertFalse(result["timing"]["actual_engine_schedule_observed"])
        self.assertTrue(result["timing"]["rendering_fps_independent"])
        self.assertEqual(result["timeline"]["summary"]["modeled_cycle_rotations"], 2)
        self.assertEqual(result["timeline"]["summary"]["event_ticks"], 2)
        self.assertEqual(result["timeline"]["summary"]["background_pixels_in_cycled_index_ranges"], 64)
        self.assertEqual(len(result["files"]), 2)
        image = (self.dest / "room-001_indexed.png").read_bytes()
        width, height, indices, clut = parse_indexed_png(image)
        self.assertEqual((width, height), (8, 8))
        self.assertEqual(indices, bytes(([5, 6] * 4) * 8))
        self.assertEqual(
            clut, (self.dest / "room-001_initial-clut.rgb").read_bytes())
        for entry in result["files"]:
            self.assertEqual(
                sha256((self.dest / entry["filename"]).read_bytes()).hexdigest(),
                entry["sha256"])
        report = json.loads((self.dest / "timeline.json").read_text())
        self.assertEqual(report["status"], "success")
        self.assertEqual(report["source"]["initial_palette_sha256"], sha256(clut).hexdigest())
        self.assertEqual(report["source"]["indexed_pixels_sha256"], sha256(indices).hexdigest())
        self.assertEqual(len(report["replay_checks"]), 3)
        self.assertTrue(all(x["state_patch_hashes_verified"] for x in report["replay_checks"]))
        self.assertEqual(sha256(self.archive.read_bytes()).hexdigest(), original)

    def test_existing_output_name_preserved(self):
        self.dest.mkdir()
        outfile = self.dest / "timeline.json"
        outfile.write_text("KEEP")
        result = self.export()
        self.assertEqual(result["status"], "failed")
        self.assertIn("OUTPUT_COLLISION", [x["code"] for x in result["diagnostics"]])
        self.assertEqual(outfile.read_text(), "KEEP")
        self.assertEqual(len(list(self.dest.iterdir())), 1)

    def test_unsupported_codec_missing_room_and_input_limits_fail(self):
        make_zip(self.archive, a=index(), b=fixture(image_code=251))
        report = self.export()
        self.assertEqual(report["status"], "failed")
        self.assertIn("STRIP_CODEC_UNSUPPORTED",
                      [x["code"] for x in report["diagnostics"]])
        report = self.export(room_id=99)
        self.assertEqual(report["status"], "failed")
        self.assertIn("EVENT_ROOM_NOT_FOUND",
                      [x["code"] for x in report["diagnostics"]])
        report = self.export(counter_rate=0)
        self.assertEqual(report["status"], "failed")
        self.assertIn("EVENT_COUNTER_RATE_INVALID",
                      [x["code"] for x in report["diagnostics"]])

    def test_cli_success_and_collision_exit_nonzero(self):
        argv = ["palette-events", str(self.archive), "--room", "1",
                "--counter-rate", "4", "--duration-seconds", "3",
                "--output-dir", str(self.dest)]
        output = StringIO()
        with contextlib.redirect_stdout(output):
            self.assertEqual(main(argv), 0)
        self.assertIn("Palette event bundle: success", output.getvalue())
        self.assertIn("2 model event ticks, 2 rotations", output.getvalue())
        with contextlib.redirect_stdout(StringIO()), contextlib.redirect_stderr(StringIO()):
            self.assertEqual(main(argv), 2)


if __name__ == "__main__":
    unittest.main()
