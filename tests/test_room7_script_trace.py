"""Synthetic-only checks; never require or commit original game resources."""
import json
from pathlib import Path
import tempfile
import unittest

from tools.analyze_room7_script_trace import analyze, summarize


def tick(number, room, x, y, walkbox, scale, plane):
    draw = ("draw " + " ".join(map(str, [x, y, plane] + [0] * 20))) if plane is not None else ""
    return "\t".join(map(str, (
        number, room, room, x, y, walkbox, 160, 100, 0, 0, scale, scale, draw
    )))


class Room7ScriptTraceTests(unittest.TestCase):
    def test_executed_opcode_site_and_offset_evidence(self):
        detail = summarize([
            "DEBUG: runScript(203) from 14-7",
            "Script 203, offset 0xB: [A4] o5_loadRoomWithEgo()",
            "Script 203, offset 0xB: [A4] o5_loadRoomWithEgo()",
            "Script 201, offset 0xD: [01] o5_putActor()",
        ])
        self.assertEqual(detail["opcode_observations"], 3)
        self.assertEqual(len(detail["opcode_sites"]), 2)
        site, = (s for s in detail["opcode_sites"] if s["script_number"] == 203)
        self.assertEqual(site["offset_after_opcode"], 11)
        self.assertEqual(site["probable_opcode_start"], 10)
        self.assertEqual(site["executions"], 2)
        self.assertEqual(len(detail["potential_transition_opcode_events"]), 3)

    def _make_capture(self, path, *, valid=True):
        capture, report = path / "capture", path / "report"
        capture.mkdir()
        report.mkdir()
        (capture / "run.json").write_text(json.dumps(dict(
            capture_mode="doorway",
            script_trace="SCUMM SCRIPTS and OPCODES",
            exe_sha256="a" * 64,
        )), encoding="utf-8")
        (capture / "ticks.tsv").write_text("\n".join([
            tick(1, 7, 54, 54, 23, 150, 1),
            tick(2, 12, 259, 58, 14, 179, 2),
            tick(3, 7, 55, 55, 23, 150, 1),
        ]), encoding="utf-8")
        (capture / "console.log").write_text(
            ("Script 42, offset 0xD: [A4] o5_loadRoomWithEgo()\n"
             "Script 47, offset 0xA: [A4] o5_loadRoomWithEgo()\n") if valid
            else "No channel output\n",
            encoding="utf-8",
        )
        (capture / "runtime.log").write_text("Unrelated runtime messages\n", encoding="utf-8")
        dumps = capture / "dumps"
        dumps.mkdir()
        (dumps / "script-42.bin").write_bytes(b"synthetic-only")
        return capture, report

    def test_room_transition_reconciled_with_opcode_evidence(self):
        with tempfile.TemporaryDirectory() as tmp:
            capture, report = self._make_capture(Path(tmp))
            result = analyze(capture, report)
            self.assertEqual(result["status"], "opcode_trace_observed")
            self.assertEqual(result["tick_count"], 3)
            self.assertEqual([(r["room_before"], r["room_after"])
                              for r in result["room_changes"]], [(7, 12), (12, 7)])
            self.assertEqual(len(result["private_script_dumps"]), 1)
            self.assertEqual(result["selected_log"], "console.log")
            self.assertFalse(result["evidence"]["direct_opcode_to_tick_synchronization"])
            with self.assertRaises(FileExistsError):
                analyze(capture, report)

    def test_missing_debug_channel_remains_explicit(self):
        with tempfile.TemporaryDirectory() as tmp:
            capture, report = self._make_capture(Path(tmp), valid=False)
            result = analyze(capture, report)
            self.assertEqual(result["status"], "script_opcode_debug_channel_missing")

    def test_wrong_room_sequence_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            capture, report = self._make_capture(Path(tmp))
            (capture / "ticks.tsv").write_text("\n".join([
                tick(1, 7, 54, 54, 23, 150, 1),
                tick(2, 7, 55, 55, 23, 150, 1),
            ]), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "Expected Room 7"):
                analyze(capture, report)


if __name__ == "__main__":
    unittest.main()
