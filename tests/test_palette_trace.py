"""Synthetic external palette trace comparison tests (NOT runtime captures)."""
from __future__ import annotations

import contextlib
import hashlib
import io
import json
import tempfile
from pathlib import Path
import unittest

from scummbucket.cli import main
from scummbucket.inspector import XOR_KEY, inspect, _read_pair
from scummbucket.palette_probe import (
    advance_palette, decode_room_background_indexed, prepare_cycles,
)
from scummbucket.palette_trace import (
    TraceInvalid, compare_palette_samples, verify_palette_trace,
)
from test_inspector import index, make_zip
from test_palette_probe import fixture


class PaletteTraceTest(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.archive = self.root / "test-game.zip"
        make_zip(self.archive, a=index(), b=fixture())
        self.inspection = inspect(self.archive)
        self.assertEqual(self.inspection["status"], "success")
        _, original, _, _ = _read_pair(self.archive)
        self.original_sha = hashlib.sha256(original).hexdigest()
        decoded = bytes(value ^ XOR_KEY for value in original)
        room = self.inspection["resources"]["rooms"][0]
        self.bg = decode_room_background_indexed(
            decoded, room_offset=room["room_offset"], room_length=room["room_size"])
        self.records = room["palette_cycles"]
        self.palette = self.bg["initial_palette"]
        self.trace = self.make_trace()
        self.trace_path = self.root / "trace.json"
        self.save_trace()

    def make_trace(self):
        cycles, issues = prepare_cycles(self.records)
        self.assertEqual(issues, [])
        palette = bytearray(self.palette)
        pairs = ((2, 4), (4, 2), (0, 0), (5, 5))
        samples = []
        for seq, (timer, next_timer) in enumerate(pairs, 1):
            advance_palette(palette, cycles, delta=max(timer, next_timer))
            samples.append({
                "sequence": seq, "var_timer": timer,
                "var_timer_next": next_timer,
                "palette_rgb_hex": palette.hex(),
            })
        return {
            "schema_version": "0.1", "room_id": 1,
            "game_resource_sha256": self.original_sha,
            "capture_point": "after_cyclePalette_before_palManipulate",
            "engine_commit": "synthetic-2026",
            "capture_method": "synthetic unit test, NOT ScummVM",
            "initial_palette_rgb_hex": self.palette.hex(),
            "samples": samples,
        }

    def save_trace(self):
        self.trace_path.write_text(json.dumps(self.trace, indent=2), encoding="utf-8")

    def test_all_matching_palettes_success_but_not_authenticated(self):
        outcome = compare_palette_samples(
            self.palette, self.records, self.trace, room_id=1,
            source_sha=self.original_sha)
        self.assertEqual(outcome["status"], "success")
        self.assertEqual(outcome["samples_checked"], 4)
        self.assertEqual(outcome["samples_matched"], 4)
        self.assertEqual(outcome["samples_mismatched"], 0)
        self.assertEqual(outcome["first_mismatch_sequence"], None)
        self.assertFalse(outcome["trace_authenticated"])
        self.assertFalse(outcome["gameplay_execution_verified"])
        self.assertEqual([s["counter_delta"] for s in outcome["samples"]],
                         [4, 4, 0, 5])
        self.assertEqual([len(s["rotation_events"]) for s in outcome["samples"]],
                         [1, 1, 0, 1])

    def test_mid_wait_scheduler_override_uses_greater_palette_delta(self):
        """A game-loop delta latched at 6 can coexist with next timer 60.

        SCUMM reads VAR_TIMER_NEXT before waiting, but palette cycling later
        advances using max(VAR_TIMER, VAR_TIMER_NEXT). This synthetic trace
        reproduces that transition without claiming any engine capture.
        """
        cycles, issues = prepare_cycles(self.records)
        self.assertEqual(issues, [])
        palette = bytearray(self.palette)
        samples = []
        for seq, (timer, next_timer) in enumerate(((6, 60), (60, 60)), 1):
            advance_palette(palette, cycles, delta=max(timer, next_timer))
            samples.append({
                "sequence": seq,
                "var_timer": timer,
                "var_timer_next": next_timer,
                "palette_rgb_hex": palette.hex(),
            })
        self.trace["samples"] = samples
        outcome = compare_palette_samples(
            self.palette, self.records, self.trace,
            room_id=1, source_sha=self.original_sha)
        self.assertEqual(outcome["status"], "success")
        self.assertEqual(outcome["samples_matched"], 2)
        self.assertEqual([s["timer"] for s in outcome["samples"]], [6, 60])
        self.assertEqual([s["counter_delta"] for s in outcome["samples"]],
                         [60, 60])
        # These two callbacks would advance VAR_TIMER_TOTAL by only
        # 6 + 60, *not* by the modeled palette counter total of 120.
        self.assertEqual(6 + 60, 66)
        self.assertFalse(outcome["trace_authenticated"])

    def test_first_palette_mismatch_reports_differing_indices(self):
        # Sequence 2 rotates back to the original palette. Deliberately
        # change one color to demonstrate an exact, observable mismatch.
        changed = bytearray(self.palette)
        changed[5 * 3] ^= 1
        self.trace["samples"][1]["palette_rgb_hex"] = changed.hex()
        outcome = compare_palette_samples(
            self.palette, self.records, self.trace, room_id=1,
            source_sha=self.original_sha)
        self.assertEqual(outcome["first_mismatch_sequence"], 2)
        self.assertEqual(outcome["samples"][1]["first_differing_palette_indices"], [5])

    def test_initial_palette_divergence_is_explicit(self):
        wrong = bytearray(self.palette)
        wrong[3] ^= 1
        self.trace["initial_palette_rgb_hex"] = wrong.hex()
        with self.assertRaises(TraceInvalid) as caught:
            compare_palette_samples(
                self.palette, self.records, self.trace, room_id=1,
                source_sha=self.original_sha)
        self.assertEqual(caught.exception.code, "TRACE_INITIAL_PALETTE_MISMATCH")

    def test_corrupt_provenance_and_sequence_rejected(self):
        original = self.trace["game_resource_sha256"]
        self.trace["game_resource_sha256"] = "a" * 64
        with self.assertRaises(TraceInvalid) as caught:
            compare_palette_samples(self.palette, self.records, self.trace,
                                    room_id=1, source_sha=original)
        self.assertEqual(caught.exception.code, "TRACE_SOURCE_MISMATCH")
        self.trace["game_resource_sha256"] = original
        self.trace["samples"][0]["sequence"] = 2
        with self.assertRaises(TraceInvalid) as caught:
            compare_palette_samples(self.palette, self.records, self.trace,
                                    room_id=1, source_sha=original)
        self.assertEqual(caught.exception.code, "TRACE_SEQUENCE_INVALID")

    def test_rejects_bad_capture_point_bad_rgb_and_bool_timers(self):
        self.trace["capture_point"] = "after_palManipulate"
        with self.assertRaises(TraceInvalid) as caught:
            compare_palette_samples(self.palette, self.records, self.trace,
                                    room_id=1, source_sha=self.original_sha)
        self.assertEqual(caught.exception.code, "TRACE_CAPTURE_POINT_INVALID")
        self.trace["capture_point"] = "after_cyclePalette_before_palManipulate"
        self.trace["samples"][0]["palette_rgb_hex"] = "GG"
        with self.assertRaises(TraceInvalid) as caught:
            compare_palette_samples(self.palette, self.records, self.trace,
                                    room_id=1, source_sha=self.original_sha)
        self.assertEqual(caught.exception.code, "TRACE_PALETTE_INVALID")
        self.trace["samples"][0]["palette_rgb_hex"] = self.palette.hex()
        self.trace["samples"][0]["var_timer"] = True
        with self.assertRaises(TraceInvalid) as caught:
            compare_palette_samples(self.palette, self.records, self.trace,
                                    room_id=1, source_sha=self.original_sha)
        self.assertEqual(caught.exception.code, "TRACE_TIMER_INVALID")

    def test_input_result_source_unchanged(self):
        before = self.archive.read_bytes()
        result = verify_palette_trace(self.archive, self.trace_path, room_id=1)
        self.assertEqual(result["status"], "success", result["diagnostics"])
        self.assertEqual(result["result"]["samples_checked"], 4)
        self.assertEqual(self.archive.read_bytes(), before)
        self.assertEqual(result["source"]["resource_sha256"], self.original_sha)
        self.assertEqual(result["trace_sha256"],
                         hashlib.sha256(self.trace_path.read_bytes()).hexdigest())

    def test_incorrect_room_and_missing_trace_report_errors(self):
        report = verify_palette_trace(self.archive, self.trace_path, room_id=2)
        self.assertEqual(report["status"], "failed")
        self.assertIn("TRACE_ROOM_NOT_FOUND", [e["code"] for e in report["diagnostics"]])
        report = verify_palette_trace(self.archive, self.root / "not-found.json", room_id=1)
        self.assertEqual(report["status"], "failed")
        self.assertIn("TRACE_INPUT_ERROR", [e["code"] for e in report["diagnostics"]])

    def test_invalid_json_and_oversized_trace_are_failures(self):
        self.trace_path.write_text("{invalid", encoding="utf-8")
        result = verify_palette_trace(self.archive, self.trace_path, room_id=1)
        self.assertEqual(result["status"], "failed")
        self.assertIn("TRACE_INPUT_ERROR", [e["code"] for e in result["diagnostics"]])
        self.trace_path.write_bytes(b"0" * (1024 * 1024 + 1))
        result = verify_palette_trace(self.archive, self.trace_path, room_id=1)
        self.assertEqual(result["status"], "failed")
        self.assertIn("TRACE_SIZE_INVALID", [e["code"] for e in result["diagnostics"]])

    def test_full_verifier_exposes_mismatch_diagnostic(self):
        changed = bytearray(self.palette)
        changed[5 * 3] ^= 1
        self.trace["samples"][2]["palette_rgb_hex"] = changed.hex()
        self.save_trace()
        result = verify_palette_trace(self.archive, self.trace_path, room_id=1)
        self.assertEqual(result["status"], "failed")
        self.assertEqual(result["result"]["first_mismatch_sequence"], 3)
        self.assertIn("RUNTIME_PALETTE_MISMATCH",
                      [d["code"] for d in result["diagnostics"]])

    def test_cli_json_and_never_overwrite_report(self):
        report_path = self.root / "result.json"
        stdout = io.StringIO()
        argv = ["verify-palette-trace", str(self.archive), "--room", "1",
                "--trace", str(self.trace_path), "--output", str(report_path),
                "--json"]
        with contextlib.redirect_stdout(stdout):
            self.assertEqual(main(argv), 0)
        self.assertEqual(json.loads(stdout.getvalue())["status"], "success")
        self.assertEqual(json.loads(report_path.read_text())["status"], "success")
        old = report_path.read_bytes()
        with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
            self.assertEqual(main(argv), 2)
        self.assertEqual(report_path.read_bytes(), old)


if __name__ == "__main__":
    unittest.main()
