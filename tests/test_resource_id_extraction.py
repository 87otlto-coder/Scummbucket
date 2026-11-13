"""Synthetic-only tests for precise SCUMM directory-ID raw extraction."""
import hashlib
import json
import struct
import tempfile
import unittest
from pathlib import Path

from scummbucket.cli import main
from scummbucket.extraction import extract
from scummbucket.inspector import chunks, inspect
from test_inspector import chunk, index, resource, make_zip, encoded


def indexed_pair():
    """Two different SCRP chunks in one room, each with a distinct directory ID."""
    base = resource()
    room = base[30:]
    first = chunk("SCRP", b"synthetic-script-one")
    second = chunk("SCRP", b"synthetic-script-two")
    # An unchanged LOFF followed by an expanded LFLF; ROOM begins at byte 30.
    container = chunk("LECF", base[8:22] + chunk("LFLF", room + first + second))
    # DSCR slot 0 is empty; slot 1 and 2 live in the same ROOM bundle.
    directory = chunk("DSCR", struct.pack("<H", 3) + b"\x00\x01\x01" +
                      struct.pack("<III", 0, len(room), len(room) + len(first)))
    original = index()
    parts = chunks(original, 0, len(original), "synthetic")
    idx = b"".join(directory if p.tag == "DSCR" else original[p.offset:p.end] for p in parts)
    return idx, container, first, second


class ResourceIdExtractionTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.source = self.root / "sample.zip"
        self.destination = self.root / "selected"
        self.idx, self.container, self.first, self.second = indexed_pair()
        make_zip(self.source, a=self.idx, b=self.container)

    def test_both_ids_link_to_different_chunks(self):
        report = inspect(self.source)
        self.assertEqual(report["status"], "success", report["diagnostics"])
        links = [e for e in report["directory_links"]["entries"] if e["directory"] == "DSCR"]
        self.assertEqual([e["status"] for e in links], ["unused", "linked", "linked"])
        self.assertNotEqual(links[1]["source_offset"], links[2]["source_offset"])
        self.assertEqual(report["directory_links"]["summary"]["failed"], 0)

    def test_select_only_first_id_not_all_scripts_in_room(self):
        report = extract(self.source, self.destination, directory="DSCR", resource_id=1)
        self.assertEqual(report["status"], "success", report["diagnostics"])
        self.assertEqual(report["summary"]["success"], 1)
        self.assertEqual(len(report["items"]), 1)
        item = report["items"][0]
        self.assertEqual(item["directory"], "DSCR")
        self.assertEqual(item["resource_id"], 1)
        self.assertEqual(item["tag"], "SCRP")
        self.assertEqual(item["scope"], "indexed")
        self.assertEqual(item["room_id"], 1)
        self.assertEqual((self.destination / item["file"]).read_bytes(), self.first)
        self.assertEqual(item["sha256"], hashlib.sha256(self.first).hexdigest())
        self.assertEqual(json.loads((self.destination / "manifest.json").read_text())["items"][0], item)

    def test_second_id_stored_form_matches_original_bytes(self):
        report = extract(self.source, self.destination, directory="DSCR", resource_id=2,
                         representation="stored")
        self.assertEqual(report["status"], "success", report["diagnostics"])
        item = report["items"][0]
        self.assertEqual(item["byte_length"], len(self.second))
        self.assertEqual((self.destination / item["file"]).read_bytes(),
                         encoded(self.container)[item["source_offset"]:item["source_offset"] + len(self.second)])
        self.assertEqual(item["source_slice_sha256"], item["sha256"])
        self.assertEqual(item["decoded_chunk_sha256"], hashlib.sha256(self.second).hexdigest())

    def test_room_directory_id_can_export_full_room_chunk(self):
        report = extract(self.source, self.destination, directory="DROO", resource_id=1)
        self.assertEqual(report["status"], "success", report["diagnostics"])
        item = report["items"][0]
        self.assertEqual(item["tag"], "ROOM")
        self.assertEqual((self.destination / item["file"]).read_bytes(), self.container[30:30 + len(resource()) - 30])

    def test_unused_slot_reports_skip_not_success(self):
        report = extract(self.source, self.destination, directory="DSCR", resource_id=0)
        self.assertEqual(report["status"], "failed")
        self.assertEqual(report["summary"]["skipped"], 1)
        self.assertIn("RESOURCE_SLOT_UNUSED", [d["code"] for d in report["diagnostics"]])
        self.assertFalse(self.destination.exists())

    def test_out_of_range_and_negative_id_are_explicit(self):
        report = extract(self.source, self.destination, directory="DSCR", resource_id=3)
        self.assertIn("RESOURCE_ID_OUT_OF_RANGE", [d["code"] for d in report["diagnostics"]])
        report = extract(self.source, self.destination, directory="DSCR", resource_id=-1)
        self.assertIn("RESOURCE_ID_INVALID", [d["code"] for d in report["diagnostics"]])

    def test_type_mismatch_and_mixed_selection_rejected(self):
        report = extract(self.source, self.destination, directory="MISC", resource_id=1)
        self.assertIn("DIRECTORY_TYPE_UNSUPPORTED", [d["code"] for d in report["diagnostics"]])
        report = extract(self.source, self.destination, directory="DSCR", resource_id=1, room_id=1)
        self.assertIn("SELECTION_CONFLICT", [d["code"] for d in report["diagnostics"]])
        self.assertFalse(self.destination.exists())

    def test_corrupt_directory_target_disables_export(self):
        invalid = bytearray(self.idx)
        # Set DSCR slot 1 room number to 77: no such room in fixture.
        d = invalid.index(b"DSCR")
        invalid[d + 11] = 77
        make_zip(self.source, a=bytes(invalid), b=self.container)
        report = extract(self.source, self.destination, directory="DSCR", resource_id=1)
        self.assertEqual(report["status"], "failed")
        self.assertIn("DIRECTORY_ROOM_UNRESOLVED", [d["code"] for d in report["diagnostics"]])
        self.assertIn("EXTRACT_INSPECTION_FAILED", [d["code"] for d in report["diagnostics"]])
        self.assertFalse(self.destination.exists())

    def test_cli_extract_id_and_refuse_overwrite(self):
        cmd = ["extract-id", str(self.source), "--directory", "DSCR", "--id", "2",
               "--output-dir", str(self.destination)]
        self.assertEqual(main(cmd), 0)
        self.assertEqual(main(cmd), 2)
        self.assertIn("MANIFEST_EXISTS", [d["code"] for d in
                                        extract(self.source, self.destination, directory="DSCR",
                                                resource_id=2)["diagnostics"]])

    def test_input_zip_preserved(self):
        before = self.source.read_bytes()
        report = extract(self.source, self.destination, directory="DSCR", resource_id=2)
        self.assertEqual(report["status"], "success", report["diagnostics"])
        self.assertEqual(self.source.read_bytes(), before)


if __name__ == "__main__":
    unittest.main()
