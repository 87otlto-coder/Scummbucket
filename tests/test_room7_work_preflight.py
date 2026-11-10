"""Fixture-free tests for the read-only Room 7 Work preflight."""
import hashlib
import tempfile
import unittest
from pathlib import Path

from tools.room7_work_preflight import EXPECTED, file_digest, inspect, summarize_report


def sweep(n=3):
    return {
        "schema": "room7-sweep/1",
        "run": {"room": 7, "archives": EXPECTED, "debugger_equivalent_entry": True},
        "frames": [
            {
                "id": i + 1,
                "viewport_xy": [8 * i, 0],
                "scheduler_matches": True,
                "background": {"pixels": 0},
                "mask": {"pixels": 0},
                "front_vs_backend": {"pixels": 0},
                "front_vs_background": {"pixels": i + 1},
                "engine_sha256": "a" * 64,
            }
            for i in range(n)
        ],
    }


class ReportSummaryTests(unittest.TestCase):
    def test_report_summary_uses_explicit_scope(self):
        info = summarize_report(sweep(), expected_frames=3)
        self.assertEqual(info["frames"], 3)
        self.assertEqual(info["camera_min_x"], 0)
        self.assertEqual(info["camera_max_x"], 16)
        self.assertEqual(info["camera_distinct_x"], 3)
        self.assertEqual(info["palette_replay_matches"], 3)
        self.assertEqual(info["front_vs_background_observations"], 6)
        self.assertEqual(info["mismatch_counts"], {
            "background": 0, "mask": 0, "front_vs_backend": 0
        })
        self.assertTrue(info["debugger_equivalent_entry"])

    def test_rejects_missing_or_duplicate_frames(self):
        example = sweep()
        example["frames"][1]["id"] = 1
        with self.assertRaisesRegex(ValueError, "consecutive"):
            summarize_report(example, expected_frames=3)
        with self.assertRaisesRegex(ValueError, "expected 4"):
            summarize_report(sweep(), expected_frames=4)

    def test_rejects_non_room7_or_different_archive(self):
        for field, value in (
            ("schema", "room23-walk/1"),
            ("run.room", 23),
            ("run.archives", {}),
        ):
            with self.subTest(field=field):
                example = sweep()
                if field.startswith("run."):
                    example["run"][field.partition(".")[2]] = value
                else:
                    example[field] = value
                with self.assertRaises(ValueError):
                    summarize_report(example, expected_frames=3)

    def test_rejects_missing_viewport_coordinates(self):
        example = sweep()
        del example["frames"][0]["viewport_xy"]
        with self.assertRaisesRegex(ValueError, "viewport"):
            summarize_report(example, expected_frames=3)


class PreflightFilesystemTests(unittest.TestCase):
    def test_hashes_bytes_exactly(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "sample"
            path.write_bytes(b"verified input bytes")
            self.assertEqual(file_digest(path),
                             hashlib.sha256(b"verified input bytes").hexdigest())

    def test_missing_machine_fixture_does_not_raise_or_claim_ready(self):
        with tempfile.TemporaryDirectory() as tmp:
            result = inspect(Path(tmp))
            self.assertEqual(result["status"], "blocked")
            codes = {item["code"] for item in result["checks"]}
            self.assertIn("LAYOUT_MISSING", codes)
            self.assertIn("GIT_MISSING", codes)
            self.assertIn("ARCHIVE_MISSING", codes)

    def test_extra_top_level_folder_is_reported_not_modified(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            for name in ("SOURCE", "TOOLS", "FIXTURE", "EXTRA"):
                (root / name).mkdir()
            result = inspect(root)
            self.assertIn("LAYOUT_EXTRA", {x["code"] for x in result["checks"]})
            self.assertTrue((root / "EXTRA").is_dir())


if __name__ == "__main__":
    unittest.main()
