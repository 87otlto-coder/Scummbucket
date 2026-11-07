"""Synthetic-only tests for SCUMM directory slot -> chunk linking."""
from copy import deepcopy
import unittest

from scummbucket.linking import link_index_resources


def fixture():
    room = {"id": 1, "room_offset": 100, "room_size": 60}
    inventory = [
        {"room_id": 1, "offset": 180, "tag": "SCRP", "length": 12, "scope": "bundle"},
        {"room_id": 1, "offset": 190, "tag": "SOUN", "length": 12, "scope": "bundle"},
        {"room_id": 1, "offset": 200, "tag": "COST", "length": 12, "scope": "bundle"},
        {"room_id": 1, "offset": 210, "tag": "CHAR", "length": 12, "scope": "bundle"},
    ]
    index = {}
    for kind, offset in [("DROO", 0), ("DSCR", 80), ("DSOU", 90), ("DCOS", 100), ("DCHR", 110)]:
        index[kind] = {"slots": 2, "resource_locations": [
            {"id": 0, "room_number": 0, "offset": 0},
            {"id": 1, "room_number": 1, "offset": offset},
        ]}
    return index, {"rooms": [room], "resource_inventory": inventory}


class LinkingTest(unittest.TestCase):
    def test_linked_and_unused(self):
        i, r = fixture()
        result, errors = link_index_resources(i, r, source="synthetic.001")
        self.assertEqual(result["summary"], {"linked": 5, "unused": 5, "failed": 0})
        self.assertEqual(errors, [])
        self.assertEqual(result["by_directory"]["DCOS"], {"linked": 1, "unused": 1, "failed": 0})
        script = next(e for e in result["entries"] if e["directory"] == "DSCR" and e["id"] == 1)
        self.assertEqual(script["source_offset"], 180)
        self.assertEqual(script["byte_length"], 12)
        self.assertEqual(script["status"], "linked")

    def test_unresolved_room_is_error(self):
        i, r = fixture()
        i["DSCR"]["resource_locations"][1]["room_number"] = 99
        result, errors = link_index_resources(i, r)
        self.assertEqual(result["summary"]["failed"], 1)
        self.assertEqual(errors[0]["code"], "DIRECTORY_ROOM_UNRESOLVED")

    def test_chunk_offset_missing_is_error(self):
        i, r = fixture()
        i["DSCR"]["resource_locations"][1]["offset"] += 1
        result, errors = link_index_resources(i, r)
        self.assertEqual(result["summary"]["failed"], 1)
        self.assertEqual(errors[0]["code"], "DIRECTORY_TARGET_MISSING")

    def test_wrong_tag_is_error(self):
        i, r = fixture()
        i["DSCR"]["resource_locations"][1]["offset"] = 90
        result, errors = link_index_resources(i, r)
        self.assertEqual(result["summary"]["failed"], 1)
        self.assertEqual(errors[0]["code"], "DIRECTORY_TAG_MISMATCH")

    def test_nonstandard_room_file_is_reported(self):
        i, r = fixture()
        i["DROO"]["resource_locations"][1]["room_number"] = 2
        result, errors = link_index_resources(i, r)
        self.assertEqual(result["summary"]["failed"], 1)
        self.assertEqual(errors[0]["code"], "ROOM_DIRECTORY_UNSUPPORTED")

    def test_reused_target_warns(self):
        i, r = fixture()
        i["DSCR"]["resource_locations"].append({"id": 2, "room_number": 1, "offset": 80})
        i["DSCR"]["slots"] = 3
        result, errors = link_index_resources(i, r)
        self.assertEqual(result["summary"]["failed"], 0)
        self.assertIn("DIRECTORY_TARGET_REUSED", [e["code"] for e in errors])

    def test_duplicate_inventory_location_reported(self):
        i, r = fixture()
        r["resource_inventory"].append(deepcopy(r["resource_inventory"][0]))
        _, errors = link_index_resources(i, r)
        self.assertIn("INVENTORY_LOCATION_DUPLICATE", [e["code"] for e in errors])

    def test_missing_directory_reported(self):
        i, r = fixture()
        del i["DSCR"]
        result, errors = link_index_resources(i, r)
        self.assertIn("DIRECTORY_MISSING", [e["code"] for e in errors])
        self.assertEqual(result["summary"]["linked"], 4)

    def test_mismatched_slot_count_reported(self):
        i, r = fixture()
        i["DSCR"]["slots"] = 10
        result, errors = link_index_resources(i, r)
        self.assertIn("DIRECTORY_SLOTS_INCONSISTENT", [e["code"] for e in errors])
        self.assertEqual(result["summary"]["linked"], 5)

    def test_unused_slots_are_not_failures(self):
        i, r = fixture()
        for key in i:
            i[key]["resource_locations"] = i[key]["resource_locations"][:1]
            i[key]["slots"] = 1
        result, errors = link_index_resources(i, r)
        self.assertEqual(result["summary"], {"linked": 0, "unused": 5, "failed": 0})
        self.assertEqual(errors, [])


if __name__ == "__main__":
    unittest.main()
