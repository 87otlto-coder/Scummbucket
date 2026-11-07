"""Optional private integration test for one fingerprinted DOS MI2 sample.

No copyrighted game bytes are stored in this repository. The test is skipped
in CI unless an authorized local archive is explicitly supplied by environment.
"""
import hashlib
import os
from pathlib import Path
import tempfile
import unittest

from scummbucket.extraction import extract
from scummbucket.inspector import inspect, _read_pair, XOR_KEY


ARCHIVE = os.environ.get("SCUMMBUCKET_MI2_ARCHIVE")
EXPECTED_INDEX = "cde7aa8980317e3a750fbb3b49884cdddaf1ff3d4231a0c840b22cceed9033f1"
EXPECTED_RESOURCE = "ad045372e0d49626503bb50fca29a687ec8e01ef75d9b8bca702a366d143819e"
EXPECTED_SCRIPT12 = "58bcbcff5f2bf5d60e4a66e1a2ea5cdf95ffa82566e982527ec7de6868abae12"


@unittest.skipUnless(ARCHIVE, "Private MI2 fixture absent: set SCUMMBUCKET_MI2_ARCHIVE")
class PrivateMonkey2IntegrationTest(unittest.TestCase):
    def test_known_sample_inventory_and_one_script_export(self):
        source = Path(ARCHIVE)
        if not source.exists():
            self.fail(f"SCUMMBUCKET_MI2_ARCHIVE refers to a missing source: {source}")
        before = hashlib.sha256(source.read_bytes()).hexdigest() if source.is_file() else None
        report = inspect(source)
        self.assertEqual(report["status"], "success", report["diagnostics"])
        self.assertEqual([s["sha256"] for s in report["sources"]],
                         [EXPECTED_INDEX, EXPECTED_RESOURCE],
                         "This private test applies only to the fingerprinted MI2 edition")
        resources = report["resources"]
        self.assertEqual(resources["room_count"], 110)
        self.assertEqual(resources["cycle_count"], 127)
        self.assertEqual(resources["rooms_with_cycles"], 21)
        self.assertEqual(resources["multistate_object_images"], 158)
        scene_summary = report["scene_inventory"]["summary"]
        self.assertEqual(scene_summary["rooms"], 110)
        self.assertEqual(scene_summary["paired_objects"], 1145)
        self.assertEqual(scene_summary["unpaired_objects"], 0)
        self.assertEqual(scene_summary["ambiguous_objects"], 0)
        self.assertEqual(scene_summary["unreadable_object_chunks"], 0)
        self.assertEqual(scene_summary["multistate_object_candidates"], 158)
        self.assertEqual(scene_summary["palette_cycle_records"], 127)
        self.assertEqual(scene_summary["rooms_with_palette_cycle_candidates"], 21)
        room34 = next(r for r in report["scene_inventory"]["rooms"] if r["room_id"] == 34)
        object358 = next(o for o in room34["objects"] if o["object_id"] == 358)
        self.assertEqual(object358["image"]["declared_image_count"], 16)
        self.assertEqual(object358["image"]["observed_image_count"], 16)
        candidates = [h for h in room34["script_state_candidates"] if h["object_id"] == 358]
        self.assertEqual(len(candidates), 17)
        self.assertEqual(sum(h["operation_candidate"] == "drawObject" for h in candidates), 11)
        self.assertEqual(sum(h["operation_candidate"] == "setState" for h in candidates), 6)
        self.assertEqual({h["script_id"] for h in candidates}, {201, 202})
        self.assertIn(2742765, {h["source_offset"] for h in candidates})
        self.assertIn(2744442, {h["source_offset"] for h in candidates})
        self.assertTrue(all(not h["instruction_alignment_verified"] for h in candidates))
        self.assertFalse(object358["script_control_verified"])
        # Identity and source positions are checked without committing game bytes.
        _, stored, _, _ = _read_pair(source)
        decoded = bytes(value ^ XOR_KEY for value in stored)
        for sid, at, length, expected in (
            (201, 2740982, 5050, "3dd3377827386229962e9aae8d681426115ad228efe1ecf36d7469154d1fbc09"),
            (202, 2746032, 1107, "1bb2578f20c0aad5146995f7d40b5cfdd0fe6b5c25a65faaffeddb5f12c82ee9"),
        ):
            chunk = decoded[at:at + length]
            self.assertEqual(chunk[:4], b"LSCR")
            self.assertEqual(int.from_bytes(chunk[4:8], "big"), length)
            self.assertEqual(chunk[8], sid)
            self.assertEqual(hashlib.sha256(chunk).hexdigest(), expected)
        self.assertEqual(report["directory_links"]["summary"],
                         {"linked": 646, "unused": 142, "failed": 0})
        link = next(e for e in report["directory_links"]["entries"]
                    if e["directory"] == "DSCR" and e["id"] == 12)
        self.assertEqual((link["room_id"], link["source_offset"], link["byte_length"], link["status"]),
                         (4, 228779, 94, "linked"))
        with tempfile.TemporaryDirectory() as directory:
            out = extract(source, Path(directory) / "script12",
                          directory="DSCR", resource_id=12)
            self.assertEqual(out["status"], "success", out["diagnostics"])
            self.assertEqual(out["summary"]["success"], 1)
            chunk = out["items"][0]
            self.assertEqual(chunk["sha256"], EXPECTED_SCRIPT12)
            extracted = (Path(directory) / "script12" / chunk["file"]).read_bytes()
            self.assertEqual(extracted[:4], b"SCRP")
            self.assertEqual(hashlib.sha256(extracted).hexdigest(), EXPECTED_SCRIPT12)
        if before is not None:
            self.assertEqual(hashlib.sha256(source.read_bytes()).hexdigest(), before,
                             "Original game archive must remain unchanged")


if __name__ == "__main__":
    unittest.main()
