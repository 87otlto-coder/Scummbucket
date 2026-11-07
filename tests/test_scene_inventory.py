"""Synthetic scene relationship checks. No commercial game data or script execution."""
import contextlib
import io
import json
import struct
import tempfile
import unittest
from pathlib import Path

from scummbucket.cli import main
from scummbucket.inspector import inspect, _parse_resource
from scummbucket.scene_inventory import build_scene_inventory
from test_inspector import chunk, index, resource, make_zip


class SceneInventoryTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.source = Path(self.tmp.name) / "synthetic.zip"

    def check(self, data, *, multiple_states=True):
        make_zip(self.source, a=index(), b=bytes(data))
        return inspect(self.source)

    def test_matching_id_produces_paired_multistate_candidate(self):
        report = self.check(resource(multiple_states=True))
        self.assertEqual(report["status"], "success", report["diagnostics"])
        summary = report["scene_inventory"]["summary"]
        self.assertEqual(summary["paired_objects"], 1)
        self.assertEqual(summary["multistate_object_candidates"], 1)
        self.assertEqual(summary["rooms_with_multistate_candidates"], 1)
        self.assertEqual(summary["rooms_with_palette_cycle_candidates"], 1)
        item = report["scene_inventory"]["rooms"][0]["objects"][0]
        self.assertEqual(item["object_id"], 99)
        self.assertEqual(item["status"], "paired")
        self.assertEqual(item["image"]["declared_image_count"], 2)
        self.assertEqual(item["image"]["observed_image_count"], 2)
        self.assertEqual(item["image"]["image_state_tags"], ["IM01", "IM02"])
        self.assertEqual(item["image"]["evidence"], "decoded_v5_header")
        self.assertTrue(item["background_animation_candidate"])
        self.assertFalse(item["animation_observed"])
        self.assertFalse(item["script_control_verified"])
        self.assertEqual(item["candidate_reason"], "multiple_stored_image_states")

    def test_single_state_is_not_a_candidate(self):
        report = self.check(resource(multiple_states=False))
        self.assertEqual(report["status"], "success", report["diagnostics"])
        self.assertEqual(report["scene_inventory"]["summary"]["paired_objects"], 1)
        self.assertEqual(report["scene_inventory"]["summary"]["multistate_object_candidates"], 0)
        self.assertFalse(report["scene_inventory"]["rooms"][0]["objects"][0]
                         ["background_animation_candidate"])

    def test_different_object_ids_do_not_get_paired_by_chunk_order(self):
        data = bytearray(resource(multiple_states=True))
        idx = data.index(b"CDHD")
        data[idx + 8:idx + 10] = struct.pack("<H", 100)
        report = self.check(data)
        self.assertEqual(report["status"], "success", report["diagnostics"])
        summary = report["scene_inventory"]["summary"]
        self.assertEqual(summary["paired_objects"], 0)
        self.assertEqual(summary["unpaired_objects"], 2)
        self.assertEqual(summary["multistate_object_candidates"], 0)
        self.assertEqual({o["object_id"] for o in report["scene_inventory"]["rooms"][0]["objects"]}, {99, 100})
        self.assertIn("OBJECT_COUNTERPART_MISSING",
                      [d["code"] for d in report["diagnostics"]])

    def test_missing_cdhd_is_reported_as_error_and_partial(self):
        data = bytearray(resource(multiple_states=True))
        idx = data.index(b"CDHD")
        data[idx:idx + 4] = b"TEST"
        report = self.check(data)
        self.assertEqual(report["status"], "partial")
        self.assertEqual(report["scene_inventory"]["summary"]["unreadable_object_chunks"], 1)
        self.assertIn("OBJECT_HEADER_COUNT_INVALID",
                      [d["code"] for d in report["diagnostics"]])

    def test_nested_corruption_reports_object_local_failure(self):
        data = bytearray(resource(multiple_states=True))
        idx = data.index(b"CDHD")
        data[idx + 4:idx + 8] = b"\xff\xff\xff\xff"
        report = self.check(data)
        self.assertEqual(report["status"], "partial")
        self.assertIn("OBJECT_CHILD_STRUCTURE_INVALID",
                      [d["code"] for d in report["diagnostics"]])

    def test_declared_image_count_mismatch_stays_visible(self):
        data = bytearray(resource(multiple_states=True))
        idx = data.index(b"IMHD")
        data[idx + 10:idx + 12] = struct.pack("<H", 1)
        report = self.check(data)
        self.assertEqual(report["status"], "success", report["diagnostics"])
        self.assertIn("OBJECT_IMAGE_COUNT_MISMATCH",
                      [d["code"] for d in report["diagnostics"]])
        self.assertEqual(report["scene_inventory"]["summary"]["paired_objects"], 1)

    def test_scenes_cli_renders_selected_room(self):
        self.check(resource(multiple_states=True))
        output, errors = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(output), contextlib.redirect_stderr(errors):
            exit_code = main(["scenes", str(self.source), "--room", "1"])
        self.assertEqual(exit_code, 0, errors.getvalue())
        self.assertIn("Room 001:", output.getvalue())
        self.assertIn("multistate candidates=1", output.getvalue())
        self.assertIn("does not establish active animation", output.getvalue())

    def test_scenes_cli_json_has_explicit_unverified_status(self):
        self.check(resource(multiple_states=True))
        with contextlib.redirect_stdout(io.StringIO()) as unused:
            pass
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            self.assertEqual(main(["scenes", str(self.source), "--room", "1", "--json"]), 0)
        document = json.loads(output.getvalue())
        self.assertEqual(document["operation"], "scene_candidates")
        self.assertEqual(len(document["rooms"]), 1)
        self.assertEqual(document["rooms"][0]["room_id"], 1)
        self.assertIn("no script control", document["interpretation"].lower())

    def test_scenes_cli_unknown_room_and_output_overwrite(self):
        self.check(resource(multiple_states=True))
        out = io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(io.StringIO()):
            self.assertEqual(main(["scenes", str(self.source), "--room", "2", "--json"]), 2)
        self.assertIn("SCENE_ROOM_NOT_FOUND", out.getvalue())
        target = Path(self.tmp.name) / "previous.json"
        target.write_text("UNCHANGED")
        with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
            self.assertEqual(main(["scenes", str(self.source), "--output", str(target)]), 2)
        self.assertEqual(target.read_text(), "UNCHANGED")

    def test_scripts_and_costumes_are_storage_context_not_proven_references(self):
        data = resource(multiple_states=True)
        room_size = struct.unpack_from(">I", data, 34)[0]
        old_payload = data[38:30 + room_size]
        new_room = chunk("ROOM", old_payload + chunk("LSCR", b"x")
                         + chunk("ENCD", b"y") + chunk("EXCD", b"z"))
        new_file = chunk("LECF", data[8:22] + chunk("LFLF", new_room))
        parsed = _parse_resource(new_file, "synthetic", [])
        links = {"entries": [
            {"directory": "DSCR", "id": 12, "room_id": 1, "source_offset": 500,
             "byte_length": 9, "status": "linked"},
            {"directory": "DCOS", "id": 8, "room_id": 1, "source_offset": 600,
             "byte_length": 12, "status": "linked"},
        ]}
        result, diagnostics = build_scene_inventory(new_file, parsed, links, source="synthetic")
        self.assertEqual(diagnostics, [])
        scene = result["rooms"][0]
        self.assertEqual({x["tag"] for x in scene["local_script_chunks"]},
                         {"LSCR", "ENCD", "EXCD"})
        self.assertEqual(scene["global_scripts_stored_here"][0]["id"], 12)
        self.assertEqual(scene["costumes_stored_here"][0]["id"], 8)
        self.assertEqual(scene["global_scripts_stored_here"][0]["relationship"],
                         "stored_in_room_bundle_only")
        self.assertEqual(scene["evidence"]["animation_playback"], "not_verified")
        self.assertFalse(scene["objects"][0]["script_control_verified"])


if __name__ == "__main__":
    unittest.main()
