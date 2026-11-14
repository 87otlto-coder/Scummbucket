"""Synthetic-only tests for external descumm offset verification.

These tests MOCK descumm output and do not assert that the genuine binary has
ever run in GitHub Actions. Full original-game disassembly remains an opt-in
local integration task.
"""
from __future__ import annotations

import contextlib
import io
import json
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch

from scummbucket.cli import main
from scummbucket.descumm_verification import verify_descumm, _parse_instruction_starts
from test_inspector import index, make_zip
from test_script_candidates import with_local_script


BODY = (b"\x05\x63\x00\x02\x01\x00"
        b"\x07\x63\x00\x00")
OUTPUT_BOTH = "Script# 201\n[0000] (05) drawObject(...);\n[0006] (07) setState(...);\nEND\n"


class ExternalDescummVerificationTest(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.root = Path(tmp.name)
        self.archive = self.root / "mi2-synthetic.zip"
        make_zip(self.archive, a=index(), b=with_local_script(BODY, script_id=201))

    def verify(self, text=OUTPUT_BOTH, *, returncode=0):
        def run_fake(argv, **kwargs):
            self.assertEqual(argv[:4], ["mock-descumm", "-5", "-o", "-h"])
            path = Path(argv[-1])
            raw = path.read_bytes()
            self.assertTrue(raw.startswith(b"LSCR"))
            self.assertEqual(raw[8], 201)
            self.assertEqual(raw[9:], BODY)
            self.assertFalse(kwargs["check"])
            self.assertGreater(kwargs["timeout"], 0)
            return subprocess.CompletedProcess(argv, returncode, stdout=text, stderr="")
        with patch("scummbucket.descumm_verification.shutil.which", return_value="mock-descumm"):
            with patch("scummbucket.descumm_verification.subprocess.run", side_effect=run_fake):
                return verify_descumm(self.archive, room_id=1, script_id=201,
                                      object_id=99, descumm="mock-descumm")

    def test_confirmed_boundaries_are_not_runtime_execution(self):
        report = self.verify()
        self.assertEqual(report["status"], "success", report["diagnostics"])
        self.assertEqual(report["summary"], {
            "candidates": 2, "confirmed_opcode_starts": 2,
            "not_emitted": 0, "opcode_conflicts": 0})
        for item in report["candidates"]:
            self.assertTrue(item["instruction_alignment_verified"])
            self.assertEqual(item["disassembly_status"], "confirmed_opcode_start")
            self.assertFalse(item["runtime_execution_verified"])
            self.assertFalse(item["script_control_verified"])
        self.assertEqual(report["disassembler"]["instruction_starts_emitted"], 2)
        self.assertEqual(report["source"]["script_length"], len(BODY) + 9)

    def test_missing_disassembler_line_is_not_claimed_as_false_positive(self):
        report = self.verify("Script# 201\n[0000] (05) drawObject(...);\nEND\n")
        self.assertEqual(report["status"], "partial")
        self.assertEqual(report["summary"]["confirmed_opcode_starts"], 1)
        self.assertEqual(report["summary"]["not_emitted"], 1)
        self.assertEqual(report["candidates"][1]["disassembly_status"], "not_emitted")
        self.assertFalse(report["candidates"][1]["instruction_alignment_verified"])

    def test_conflicting_opcode_is_error(self):
        report = self.verify("Script# 201\n[0000] (07) setState(...);\n[0006] (07) setState(...);\nEND\n")
        self.assertEqual(report["status"], "failed")
        self.assertEqual(report["summary"]["opcode_conflicts"], 1)
        self.assertIn("DESCUMM_OPCODE_CONFLICT", [d["code"] for d in report["diagnostics"]])

    def test_external_tool_failure_remains_visible(self):
        report = self.verify("descumm error", returncode=2)
        self.assertEqual(report["status"], "failed")
        self.assertIn("DESCUMM_NONZERO_EXIT", [d["code"] for d in report["diagnostics"]])
        self.assertTrue(all(not x["instruction_alignment_verified"]
                            for x in report["candidates"]))

    def test_missing_end_marker_rejected(self):
        report = self.verify("Script# 201\n[0000] (05) drawObject(...);\n")
        self.assertEqual(report["status"], "failed")
        self.assertIn("DESCUMM_OUTPUT_INCOMPLETE", [d["code"] for d in report["diagnostics"]])

    def test_duplicate_instruction_offsets_are_rejected(self):
        report = self.verify(
            "Script# 201\n[0000] (05) drawObject(...);\n[0000] (05) repeated\nEND\n")
        self.assertEqual(report["status"], "failed")
        self.assertIn("DESCUMM_OFFSET_DUPLICATE", [d["code"] for d in report["diagnostics"]])

    def test_disassembler_timeout_is_explicit(self):
        with patch("scummbucket.descumm_verification.shutil.which", return_value="mock-descumm"):
            with patch("scummbucket.descumm_verification.subprocess.run",
                       side_effect=subprocess.TimeoutExpired(cmd=["mock-descumm"], timeout=25)):
                report = verify_descumm(self.archive, room_id=1, script_id=201,
                                        object_id=99, descumm="mock-descumm")
        self.assertEqual(report["status"], "failed")
        self.assertIn("DESCUMM_TIMEOUT", [d["code"] for d in report["diagnostics"]])

    def test_missing_disassembler_is_explicit(self):
        with patch("scummbucket.descumm_verification.shutil.which", return_value=None):
            report = verify_descumm(self.archive, room_id=1, script_id=201, object_id=99)
        self.assertEqual(report["status"], "failed")
        self.assertIn("DESCUMM_NOT_FOUND", [d["code"] for d in report["diagnostics"]])

    def test_unknown_room_object_and_script_report_errors(self):
        cases = [
            ({"room_id": 3, "script_id": 201, "object_id": 99}, "VERIFY_ROOM_NOT_FOUND"),
            ({"room_id": 1, "script_id": 201, "object_id": 123}, "VERIFY_OBJECT_NOT_FOUND"),
            ({"room_id": 1, "script_id": 202, "object_id": 99}, "VERIFY_SCRIPT_MISSING"),
        ]
        for kwargs, expected in cases:
            with self.subTest(expected=expected):
                report = verify_descumm(self.archive, **kwargs)
                self.assertEqual(report["status"], "failed")
                self.assertIn(expected, [d["code"] for d in report["diagnostics"]])

    def test_cli_json_report_can_be_verified_without_side_effects(self):
        initial = self.archive.read_bytes()
        stdout = io.StringIO()
        with patch("scummbucket.descumm_verification.shutil.which", return_value="mock-descumm"):
            with patch("scummbucket.descumm_verification.subprocess.run", return_value=
                       subprocess.CompletedProcess([], 0, stdout=OUTPUT_BOTH, stderr="")):
                with contextlib.redirect_stdout(stdout):
                    code = main(["verify-descumm", str(self.archive), "--room", "1",
                                 "--script", "201", "--object", "99",
                                 "--descumm", "mock-descumm", "--json"])
        self.assertEqual(code, 0)
        self.assertEqual(json.loads(stdout.getvalue())["summary"]["confirmed_opcode_starts"], 2)
        self.assertEqual(self.archive.read_bytes(), initial)

    def test_cli_does_not_overwrite_existing_report(self):
        dest = self.root / "report.json"
        dest.write_text("PRESERVE")
        stderr = io.StringIO()
        with patch("scummbucket.descumm_verification.shutil.which", return_value="mock-descumm"):
            with patch("scummbucket.descumm_verification.subprocess.run", return_value=
                       subprocess.CompletedProcess([], 0, stdout=OUTPUT_BOTH, stderr="")):
                with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(stderr):
                    code = main(["verify-descumm", str(self.archive), "--room", "1",
                                 "--script", "201", "--object", "99",
                                 "--descumm", "mock-descumm", "--output", str(dest)])
        self.assertEqual(code, 2)
        self.assertIn("OUTPUT_WRITE_FAILED", stderr.getvalue())
        self.assertEqual(dest.read_text(), "PRESERVE")

    def test_parser_ignores_unanchored_hex_strings(self):
        lines, diagnostics = _parse_instruction_starts(
            'raw text [0000] (05)\n[0000] (05) legitimate\n[0006] (07) legitimate\n')
        self.assertEqual(lines, {0: 5, 6: 7})
        self.assertEqual(diagnostics, [])


if __name__ == "__main__":
    unittest.main()
