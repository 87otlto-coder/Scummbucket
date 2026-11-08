"""Palette trace bridge tests use synthetic engine logs, never proprietary data."""
from __future__ import annotations

from hashlib import sha256
import importlib.util
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scummbucket.engine_trace_import import (
    EngineTraceError, import_scummvm_palette_log, parse_scummvm_palette_log,
)

spec = importlib.util.spec_from_file_location("patcher", ROOT / "tools/instrument_scummvm_palette.py")
patcher = importlib.util.module_from_spec(spec)
spec.loader.exec_module(patcher)

COMMIT = "ab" * 20
RESOURCE = b"SYNTHETIC MONKEY2.001 TEST DATA -- NOT A GAME"
SHA = sha256(RESOURCE).hexdigest()
INITIAL = (bytes(range(256)) * 3).hex()
CHANGED = (bytes((i ^ 3) for i in range(256)) * 3).hex()


def raw_log(*, samples=2, stop_reason="room_exit"):
    lines = [f"SBP4|BEGIN|23|1000|{INITIAL}"]
    for seq in range(1, samples + 1):
        lines.append(f"SBP4|SAMPLE|{seq}|4|4|{1000 + seq * 67}|"
                     f"{CHANGED if seq % 2 else INITIAL}")
    lines.append(f"SBP4|END|{samples}|{stop_reason}")
    return ("\n".join(lines) + "\n").encode()


class EngineLogParsingTest(unittest.TestCase):
    def test_exact_contract_and_observed_wallclock(self):
        trace = parse_scummvm_palette_log(raw_log(), engine_commit=COMMIT,
                                          game_resource_sha256=SHA)
        self.assertEqual(trace["capture_point"], "after_cyclePalette_before_palManipulate")
        self.assertEqual(trace["game_resource_sha256"], SHA)
        self.assertEqual(trace["engine_commit"], COMMIT)
        self.assertEqual(trace["initial_palette_rgb_hex"], INITIAL)
        self.assertEqual([v["sequence"] for v in trace["samples"]], [1, 2])
        self.assertEqual([v["elapsed_ms"] for v in trace["samples"]], [67, 134])
        self.assertTrue(trace["clock_observation"]["is_monotonic_wallclock_not_engine_counter"])
        self.assertEqual(trace["clock_observation"]["stop_reason"], "room_exit")
        self.assertFalse(trace["limitations"]["runtime_trace_authenticated"])

    def test_rejects_missing_end_and_missing_newline(self):
        for bad in [raw_log().rsplit(b"SBP4|END", 1)[0], raw_log()[:-1]]:
            with self.assertRaises(EngineTraceError) as exc:
                parse_scummvm_palette_log(bad, engine_commit=COMMIT,
                                          game_resource_sha256=SHA)
            self.assertIn(exc.exception.code,
                          ("ENGINE_LOG_INCOMPLETE", "ENGINE_LOG_END_INVALID"))

    def test_rejects_sequence_timer_clock_and_palette_corruption(self):
        valid = raw_log()
        substitutions = [
            (b"SBP4|SAMPLE|2|", b"SBP4|SAMPLE|3|", "ENGINE_LOG_SEQUENCE_INVALID"),
            (b"|4|4|1067|", b"|65536|4|1067|", "ENGINE_LOG_INTEGER_INVALID"),
            (b"|4|4|1134|", b"|4|4|1001|", "ENGINE_LOG_CLOCK_INVALID"),
            (CHANGED.encode(), b"z" + CHANGED.encode()[1:], "ENGINE_LOG_PALETTE_INVALID"),
            (b"SBP4|END|2|", b"SBP4|END|1|", "ENGINE_LOG_END_MISMATCH"),
        ]
        for old, new, code in substitutions:
            with self.subTest(code=code):
                with self.assertRaises(EngineTraceError) as exc:
                    parse_scummvm_palette_log(valid.replace(old, new, 1),
                                              engine_commit=COMMIT,
                                              game_resource_sha256=SHA)
                self.assertEqual(exc.exception.code, code)

    def test_256_sample_limit_must_match_termination(self):
        trace = parse_scummvm_palette_log(raw_log(samples=256, stop_reason="limit"),
                                          engine_commit=COMMIT,
                                          game_resource_sha256=SHA)
        self.assertEqual(len(trace["samples"]), 256)
        with self.assertRaises(EngineTraceError) as exc:
            parse_scummvm_palette_log(raw_log(samples=2, stop_reason="limit"),
                                      engine_commit=COMMIT, game_resource_sha256=SHA)
        self.assertEqual(exc.exception.code, "ENGINE_LOG_END_MISMATCH")

    def test_bad_claimed_engine_commit_not_accepted(self):
        with self.assertRaises(EngineTraceError) as exc:
            parse_scummvm_palette_log(raw_log(), engine_commit="v2026.4.0",
                                      game_resource_sha256=SHA)
        self.assertEqual(exc.exception.code, "ENGINE_COMMIT_INVALID")


class EngineImportTest(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.root = Path(temp.name)
        self.raw = self.root / "raw.log"
        self.resource = self.root / "MONKEY2.001"
        self.output = self.root / "room23-observed.json"
        self.raw.write_bytes(raw_log())
        self.resource.write_bytes(RESOURCE)

    def import_log(self, **kwargs):
        return import_scummvm_palette_log(
            self.raw, self.resource, self.output,
            engine_commit=COMMIT, **kwargs)

    def test_original_resource_hashed_and_trace_written(self):
        report = self.import_log(expected_source_sha256=SHA)
        self.assertEqual(report["status"], "success", report["diagnostics"])
        self.assertEqual(report["samples"], 2)
        self.assertEqual(report["resource_sha256"], SHA)
        self.assertEqual(report["trace_sha256"], sha256(self.output.read_bytes()).hexdigest())
        trace = json.loads(self.output.read_text())
        self.assertEqual(len(trace["samples"]), 2)
        self.assertEqual(trace["game_resource_sha256"], SHA)
        self.assertEqual(trace["raw_hook_log_sha256"], sha256(self.raw.read_bytes()).hexdigest())
        self.assertTrue(trace["import_provenance"]["local_source_file_opened_for_hashing"])
        self.assertFalse(trace["import_provenance"]["original_resource_decoded_by_importer"])
        self.assertEqual(len(trace["initial_palette_rgb_hex"]), 1536)

    def test_mismatched_proprietary_source_does_not_create_trace(self):
        report = self.import_log(expected_source_sha256="0" * 64)
        self.assertEqual(report["status"], "failed")
        self.assertFalse(self.output.exists())
        self.assertIn("ENGINE_SOURCE_MISMATCH", [d["code"] for d in report["diagnostics"]])

    def test_never_overwrites_existing_output(self):
        self.output.write_text("KEEP")
        report = self.import_log()
        self.assertEqual(report["status"], "failed")
        self.assertEqual(self.output.read_text(), "KEEP")
        self.assertIn("OUTPUT_COLLISION", [d["code"] for d in report["diagnostics"]])

    def test_corrupted_log_is_visible_failure(self):
        self.raw.write_text("ERROR\n")
        report = self.import_log()
        self.assertEqual(report["status"], "failed")
        self.assertFalse(self.output.exists())
        self.assertIn("ENGINE_LOG_INCOMPLETE", [d["code"] for d in report["diagnostics"]])


class PinnedPatcherTest(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.root = Path(temp.name)
        self.file = self.root / "engines/scumm/scumm.cpp"
        self.file.parent.mkdir(parents=True)
        self.fixture = (patcher.INCLUDE_ANCHOR + "// synthetic test\n" +
                        patcher.ANCHOR + "\tif (_doEffect) {}\n}\n").encode()
        self.file.write_bytes(self.fixture)
        self.blob = patcher.git_blob_sha(self.fixture)

    def test_no_write_on_check_and_restore_exact_original(self):
        with patch.object(patcher, "PINNED_CPP_BLOB", self.blob):
            self.assertIn("PATCH_APPLICABLE", patcher.apply_patch(self.root, check=True))
            self.assertEqual(self.file.read_bytes(), self.fixture)
            self.assertIn("PATCH_APPLIED", patcher.apply_patch(self.root))
            patched = self.file.read_bytes()
            self.assertIn(patcher.MARKER.encode(), patched)
            self.assertEqual(patched.count(b"cyclePalette();"), 1)
            self.assertEqual(patched.count(b"palManipulate();"), 1)
            self.assertIn(b"sbP4Trace", patched)
            self.assertIn("RESTORED", patcher.apply_patch(self.root, restore=True))
            self.assertEqual(self.file.read_bytes(), self.fixture)

    def test_unpinned_source_refused_without_touching_file(self):
        with self.assertRaises(patcher.PatchError) as exc:
            patcher.apply_patch(self.root)
        self.assertIn("SOURCE_VERSION_MISMATCH", str(exc.exception))
        self.assertEqual(self.file.read_bytes(), self.fixture)

    def test_idempotent_safety_and_backup_collision(self):
        with patch.object(patcher, "PINNED_CPP_BLOB", self.blob):
            patcher.apply_patch(self.root)
            with self.assertRaises(patcher.PatchError) as exc:
                patcher.apply_patch(self.root)
            self.assertIn("ALREADY_INSTRUMENTED", str(exc.exception))

    def test_crlf_source_retained(self):
        crlf = self.fixture.replace(b"\n", b"\r\n")
        self.file.write_bytes(crlf)
        with patch.object(patcher, "PINNED_CPP_BLOB", self.blob):
            patched = patcher.patch_source(crlf)
            self.assertIn(b"\r\n", patched)
            self.assertEqual(patched.replace(b"\r\n", b"\n").count(b"cyclePalette();"), 1)


if __name__ == "__main__":
    unittest.main()
