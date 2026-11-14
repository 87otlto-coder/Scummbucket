"""Private, edition-pinned Room 7 scenery-costume animation-table regression.

The source archive is read-only. Public CI skips this original-game test.
Do not infer runtime timing or additional animation support from this structure.
"""
import hashlib
import os
from pathlib import Path
import unittest

from scummbucket.classic_costume import ClassicCostume
from scummbucket.inspector import inspect, _read_pair, XOR_KEY

ARCHIVE = os.getenv("SCUMMBUCKET_MI2_ARCHIVE")
INDEX_SHA = "cde7aa8980317e3a750fbb3b49884cdddaf1ff3d4231a0c840b22cceed9033f1"
RESOURCE_SHA = "ad045372e0d49626503bb50fca29a687ec8e01ef75d9b8bca702a366d143819e"
COST_SHA = "7ef3e98fb9cd824782b0cf7e93d9e7f3c059354557ec7e08d714eda9425a7c5f"
CEL_SLOTS_SHA = "0dd785d9b58e4cdc54c9035a4d6875dbafef662df86a42f153cd031735848b15"


@unittest.skipUnless(ARCHIVE, "Private MI2 DOS VGA original archive not configured")
class Room7Costume142PrivateTest(unittest.TestCase):
    def test_only_two_animation_entries_address_the_same_cel(self):
        archive = Path(ARCHIVE)
        self.assertTrue(archive.exists(), f"Missing original archive: {archive}")
        inventory = inspect(archive)
        self.assertEqual(inventory["status"], "success", inventory["diagnostics"])
        self.assertEqual([row["sha256"] for row in inventory["sources"]],
                         [INDEX_SHA, RESOURCE_SHA])
        links = [row for row in inventory["directory_links"]["entries"]
                 if row["directory"] == "DCOS" and row["id"] == 142]
        self.assertEqual(len(links), 1)
        link = links[0]
        self.assertEqual((link["status"], link["room_id"], link["source_offset"],
                          link["byte_length"]), ("linked", 7, 584460, 1509))

        _, resource, _, _ = _read_pair(archive)
        self.assertEqual(hashlib.sha256(resource).hexdigest(), RESOURCE_SHA)
        start = link["source_offset"]
        cost_data = bytes(value ^ XOR_KEY for value in
                          resource[start:start + link["byte_length"]])
        self.assertEqual(hashlib.sha256(cost_data).hexdigest(), COST_SHA)
        costume = ClassicCostume(cost_data)
        self.assertEqual((costume.colors, costume.table_start, cost_data[8]),
                         (32, 42, 14))

        # A zero table offset is an unpopulated animation, not a malformed
        # pointer to follow. Populated entries must stay in COST bounds.
        animations = {}
        for anim in range(cost_data[8] + 1):
            at = costume.table_start + 34 + 2 * anim
            offset = int.from_bytes(cost_data[at:at + 2], "little")
            if offset == 0:
                continue
            record = 2 + offset
            self.assertLessEqual(record + 5, len(cost_data))
            animations[anim] = (
                record,
                int.from_bytes(cost_data[record:record + 2], "little"),
                int.from_bytes(cost_data[record + 2:record + 4], "little"),
                cost_data[record + 4],
            )
        self.assertEqual(animations, {
            6: (106, 0x8000, 0, 0),
            14: (111, 0x8000, 0, 0),
        })
        self.assertEqual(costume.commands, 116)
        self.assertEqual(cost_data[costume.commands], 0)

        cel_offset, cel = costume.limb(0, 0)
        self.assertEqual(cel_offset, 119)
        self.assertEqual((cel.width, cel.height, cel.rel_x, cel.rel_y,
                          cel.move_x, cel.move_y), (89, 51, -47, -50, 0, 0))
        self.assertEqual(len(cel.slots), 4539)
        self.assertEqual(sum(bool(slot) for slot in cel.slots), 2225)
        self.assertEqual(hashlib.sha256(cel.slots).hexdigest(), CEL_SLOTS_SHA)


if __name__ == "__main__":
    unittest.main()
