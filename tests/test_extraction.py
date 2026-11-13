"""Synthetic-only raw chunk extraction tests; no commercial game bytes."""
import hashlib
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from scummbucket.extraction import extract
from scummbucket.inspector import _read_pair
from scummbucket.cli import main
from test_inspector import index, resource, make_zip, encoded


class ExtractionTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.zip_path = self.root / "fake-game.zip"
        self.output = self.root / "exports"
        self.res = resource(multiple_states=True)
        make_zip(self.zip_path, a=index(), b=self.res)

    def test_decoded_chunk_matches_original_bytes(self):
        r = extract(self.zip_path, self.output, room_id=1, tag="CYCL")
        self.assertEqual(r["status"], "success", r["diagnostics"])
        self.assertEqual(r["summary"]["success"], 1)
        self.assertEqual(r["summary"]["failed"], 0)
        item = r["items"][0]
        self.assertEqual(item["representation"], "decoded")
        blob = (self.output / item["file"]).read_bytes()
        self.assertTrue(blob.startswith(b"CYCL"))
        self.assertEqual(blob, self.res[item["source_offset"]: item["source_offset"] + item["byte_length"]])
        self.assertEqual(item["sha256"], hashlib.sha256(blob).hexdigest())
        self.assertEqual(json.loads((self.output / "manifest.json").read_text())["items"], r["items"])
        self.assertEqual(item["source_sha256"], hashlib.sha256(encoded(self.res)).hexdigest())

    def test_stored_representation_reproduces_container_slice(self):
        r = extract(self.zip_path, self.output, room_id=1, tag="CYCL", representation="stored")
        self.assertEqual(r["status"], "success", r["diagnostics"])
        item = r["items"][0]
        self.assertEqual((self.output / item["file"]).read_bytes(),
                         encoded(self.res)[item["source_offset"]: item["source_offset"] + item["byte_length"]])
        self.assertEqual(item["source_slice_sha256"], item["sha256"])
        self.assertNotEqual(item["decoded_chunk_sha256"], item["sha256"])

    def test_multi_resource_export(self):
        r = extract(self.zip_path, self.output, room_id=1)
        self.assertEqual(r["status"], "success")
        self.assertEqual(r["summary"]["success"], 4)
        self.assertEqual(len(set(i["file"] for i in r["items"])), 4)

    def test_existing_chunk_reports_partial_and_continues(self):
        first = extract(self.zip_path, self.output, room_id=1, tag="CYCL")
        self.assertEqual(first["status"], "success")
        (self.output / "manifest.json").unlink()  # Simulate resume after a previous run
        prior_file = self.output / first["items"][0]["file"]
        prior = prior_file.read_bytes()
        later = extract(self.zip_path, self.output, room_id=1)
        self.assertEqual(later["status"], "partial")
        self.assertEqual(later["summary"]["success"], 3)
        self.assertEqual(later["summary"]["failed"], 1)
        self.assertIn("EXTRACT_WRITE_FAILED", [x["code"] for x in later["diagnostics"]])
        self.assertEqual(prior_file.read_bytes(), prior)
        self.assertEqual(json.loads((self.output / "manifest.json").read_text())["status"], "partial")

    def test_manifest_collision_blocks_all_exports(self):
        self.output.mkdir()
        (self.output / "manifest.json").write_text("keep this")
        r = extract(self.zip_path, self.output, room_id=1)
        self.assertEqual(r["status"], "failed")
        self.assertIn("MANIFEST_EXISTS", [d["code"] for d in r["diagnostics"]])
        self.assertEqual((self.output / "manifest.json").read_text(), "keep this")
        self.assertEqual(len(list(self.output.iterdir())), 1)

    def test_nonexistent_room_is_error(self):
        r = extract(self.zip_path, self.output, room_id=99)
        self.assertEqual(r["status"], "failed")
        self.assertIn("EXTRACT_NO_MATCHES", [d["code"] for d in r["diagnostics"]])

    def test_malformed_archive_cannot_export(self):
        make_zip(self.zip_path, a=index(), b=resource(bad_length=True))
        r = extract(self.zip_path, self.output, room_id=1)
        self.assertEqual(r["status"], "failed")
        self.assertIn("EXTRACT_INSPECTION_FAILED", [d["code"] for d in r["diagnostics"]])
        self.assertFalse(self.output.exists())

    def test_changed_reopened_index_or_resource_fails_without_export(self):
        # Simulate an archive being replaced between inspect() and reopen.
        # Neither test edits the actual synthetic ZIP.
        first, second, first_label, second_label = _read_pair(self.zip_path)
        original_zip_hash = hashlib.sha256(self.zip_path.read_bytes()).hexdigest()
        for kind, data, diagnostic_fragment in (
            ("index", (bytes([first[0] ^ 1]) + first[1:], second, first_label, second_label), "Index file changed"),
            ("resource", (first, bytes([second[0] ^ 1]) + second[1:], first_label, second_label), "Resource file changed"),
        ):
            with self.subTest(kind=kind):
                destination = self.root / ("reopen-" + kind)
                with patch("scummbucket.extraction._read_pair", return_value=data):
                    report = extract(self.zip_path, destination, room_id=1, tag="CYCL")
                self.assertEqual(report["status"], "failed")
                self.assertIn("EXTRACT_INPUT_CHANGED", [d["code"] for d in report["diagnostics"]])
                self.assertTrue(any(diagnostic_fragment in d["message"] for d in report["diagnostics"]))
                self.assertFalse(any(destination.iterdir()), "No raw chunk or manifest may be written")
        self.assertEqual(hashlib.sha256(self.zip_path.read_bytes()).hexdigest(), original_zip_hash)

    def test_input_is_unchanged(self):
        original = self.zip_path.read_bytes()
        extract(self.zip_path, self.output, room_id=1, tag="CYCL")
        self.assertEqual(self.zip_path.read_bytes(), original)

    def test_invalid_selection(self):
        r = extract(self.zip_path, self.output, room_id=256)
        self.assertIn("SELECTION_ROOM_INVALID", [d["code"] for d in r["diagnostics"]])
        r = extract(self.zip_path, self.output, room_id=1, tag="bad!")
        self.assertIn("SELECTION_TAG_INVALID", [d["code"] for d in r["diagnostics"]])
        r = extract(self.zip_path, self.output, room_id=1, representation="unknown")
        self.assertIn("REPRESENTATION_UNSUPPORTED", [d["code"] for d in r["diagnostics"]])

    def test_cli_extract_summary_exit_codes(self):
        self.assertEqual(main(["extract", str(self.zip_path), "--room", "1", "--tag", "CYCL",
                               "--output-dir", str(self.output)]), 0)
        self.assertEqual(main(["extract", str(self.zip_path), "--room", "1", "--tag", "CYCL",
                               "--output-dir", str(self.output)]), 2)

    def test_symlink_destination_is_blocked(self):
        destination = self.root / "out-link"
        try:
            destination.symlink_to(self.root, target_is_directory=True)
        except (NotImplementedError, OSError):
            self.skipTest("Symlink not available on this platform")
        r = extract(self.zip_path, destination, room_id=1)
        self.assertEqual(r["status"], "failed")
        self.assertIn("OUTPUT_DIRECTORY_SYMLINK", [d["code"] for d in r["diagnostics"]])


if __name__ == "__main__":
    unittest.main()
