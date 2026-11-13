"""Synthetic source-free regression for saved-game Room 7 capture gate."""
import hashlib
import json
from pathlib import Path
import tempfile
import unittest

from tools.run_room23_frames import ARCHIVES
from tools.verify_room7_saved_entry import validate, METHOD


class Room7SavedEntryTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.capture = self.root / "FIXTURE/CAPTURES/Room7/save-probe"
        self.capture.mkdir(parents=True)
        save = b"SCVM synthetic-only-private-save-placeholder"
        (self.capture / "saves").mkdir()
        (self.capture / "saves/monkey2.s01").write_bytes(save)
        self.save = self.root / "source-save.s01"
        self.save.write_bytes(save)
        self.run = {
            "room": 7, "archives": dict(ARCHIVES),
            "debugger_equivalent_entry": False,
            "exe_sha256": "a" * 64,
            "save_sha256": hashlib.sha256(save).hexdigest(),
            "entry_provenance": {
                "method": METHOD, "save_origin_verified": False,
                "natural_gameplay_entry_verified": False,
            },
        }
        (self.capture / "capture.enabled").touch()
        self.palette = bytes(768)
        self._write_run()
        self._write_frames()
        self._write_log()

    def _write_run(self):
        (self.capture / "run.json").write_text(json.dumps(self.run), encoding="utf8")

    def _write_frames(self):
        for n, x in ((1, 0), (2, 8)):
            header = (f"R23E1 {n} {1000+n*100} 6 6 0 2 1 1 1\n"
                      f"ScummVM synthetic test\ncamera 0 0 {x} 0 320 144 784 144\n"
                      "actor 11 590 144\nDATA\n").encode()
            # 4 palette stages; back, front, two packed masks, backend screen.
            payload = bytes(3072 + 2*46080 + 2*5760 + 64000)
            (self.capture / f"engine-{n:03}.bin").write_bytes(header + payload)
            display = (f"R23D1 {n} {1000+n*100} 320 200 surface\n").encode()
            (self.capture / f"present-{n:03}.bin").write_bytes(display + bytes(320*200*3))

    def _write_log(self):
        lines = ["SBP4|BEGIN|7|1000|" + self.palette.hex()]
        lines.extend(f"SBP4|SAMPLE|{n}|6|6|{1000+n*100}|{self.palette.hex()}"
                     for n in (1, 2))
        (self.capture / "scummbucket-p4-room7.raw.log").write_text(
            "\n".join(lines) + "\n", encoding="utf8")

    def check(self):
        return validate(self.capture, original_save=self.save, expected_frames=2)

    def test_valid_saved_entry_capture_has_explicit_scope(self):
        result = self.check()
        self.assertEqual(result["status"], "capture_structure_verified")
        self.assertEqual(result["summary"]["frames_checked"], 2)
        self.assertEqual(result["summary"]["camera_max_x"], 8)
        self.assertEqual(result["summary"]["actor11_state_records"], 2)
        self.assertFalse(result["natural_gameplay_route_verified"])
        self.assertFalse(result["independent_scene_reconstruction_verified"])
        self.assertTrue(result["summary"]["original_save_matched"])

    def test_debugger_entry_or_walk_metadata_is_rejected(self):
        for key, value in (("debugger_equivalent_entry", True), ("walk", "normal")):
            with self.subTest(key=key):
                self.run[key] = value
                self._write_run()
                with self.assertRaisesRegex(ValueError, "Debugger jump or injected walk"):
                    self.check()
                if key == "walk":
                    del self.run["walk"]
                else:
                    self.run[key] = False
                self._write_run()

    def test_injection_marker_is_rejected(self):
        marker = self.capture / "enter-room7.enabled"
        marker.touch()
        with self.assertRaisesRegex(ValueError, "marker unexpectedly present"):
            self.check()

    def test_missing_provenance_or_natural_route_claim_rejected(self):
        self.run["entry_provenance"]["natural_gameplay_entry_verified"] = True
        self._write_run()
        with self.assertRaisesRegex(ValueError, "Unsupported claim"):
            self.check()
        self.run["entry_provenance"]["natural_gameplay_entry_verified"] = False
        self.run["entry_provenance"]["method"] = "debugger_save"
        self._write_run()
        with self.assertRaisesRegex(ValueError, "Missing explicit"):
            self.check()

    def test_original_dos_save_rejected_even_when_hash_matches(self):
        raw = b"123" + bytes(37) + b"synthetic DOS save"
        (self.capture / "saves/monkey2.s01").write_bytes(raw)
        self.save.write_bytes(raw)
        self.run["save_sha256"] = hashlib.sha256(raw).hexdigest()
        self._write_run()
        with self.assertRaisesRegex(ValueError, "not a ScummVM SCVM"):
            self.check()

    def test_changed_save_is_rejected(self):
        self.save.write_bytes(b"changed-source-save")
        with self.assertRaisesRegex(ValueError, "Original source save differs"):
            self.check()
        self.save.write_bytes(b"SCVM synthetic-only-private-save-placeholder")
        (self.capture / "saves/monkey2.s01").write_bytes(b"changed-copy")
        with self.assertRaisesRegex(ValueError, "Copied save does not match"):
            self.check()

    def test_missing_frame_and_changed_palette_are_rejected(self):
        (self.capture / "engine-002.bin").unlink()
        with self.assertRaisesRegex(ValueError, "frame inventory mismatch"):
            self.check()
        self._write_frames()
        path = self.capture / "scummbucket-p4-room7.raw.log"
        raw = path.read_text(encoding="utf8")
        path.write_text(raw.replace("|6|6|1100|", "|60|6|1100|"), encoding="utf8")
        with self.assertRaisesRegex(ValueError, "Trace timer or palette mismatch"):
            self.check()

    def test_bad_viewport_and_corrupt_payload_are_rejected(self):
        path = self.capture / "engine-002.bin"
        raw = path.read_bytes()
        path.write_bytes(raw.replace(b"320 144 784 144", b"320 144 800 144"))
        with self.assertRaisesRegex(ValueError, "Unexpected Room 7 viewport"):
            self.check()
        path.write_bytes(raw[:-10])
        with self.assertRaisesRegex(ValueError, "incomplete engine payload"):
            self.check()

    def test_unexpected_edition_and_missing_begin_fail(self):
        self.run["archives"]["MONKEY2.000"] = "bad"
        self._write_run()
        with self.assertRaisesRegex(ValueError, "Unexpected game edition"):
            self.check()
        self.run["archives"] = dict(ARCHIVES)
        self._write_run()
        log = self.capture / "scummbucket-p4-room7.raw.log"
        log.write_text(log.read_text(encoding="utf8").replace(
            "SBP4|BEGIN|7|", "SBP4|BEGIN|23|"), encoding="utf8")
        with self.assertRaisesRegex(ValueError, "trace beginning"):
            self.check()


if __name__ == "__main__":
    unittest.main()
