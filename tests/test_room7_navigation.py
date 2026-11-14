import unittest
from types import SimpleNamespace

from tools.analyze_room7_navigation import fields, transition, walk_stops
from tools.instrument_room7_navigation import replace_once


class NavigationTests(unittest.TestCase):
    def test_room_return_starts_new_segment_even_in_same_box(self):
        current = dict(tick=1113, walkbox=23)
        self.assertEqual(transition(dict(tick=961,walkbox=23),current),"segment_start")
        self.assertEqual(transition(dict(tick=1112,walkbox=1),current),"walkbox_change")
        self.assertIsNone(transition(dict(tick=1112,walkbox=23),current))

    def test_inactive_limb_keeps_cursor_but_is_excluded_by_archive_stop(self):
        data = bytearray(64)
        data[4:12] = bytes.fromhex("00c0 ffff 0200 00 00")
        data[42] = 0x79
        costume = SimpleNamespace(pointer=lambda offset: 4, data=data, table_start=0, commands=40)
        self.assertEqual(walk_stops(costume,90),2)
        data[42] = 0x7a
        self.assertEqual(walk_stops(costume,90),0)

    def test_truncated_or_ambiguous_pose_cannot_pass(self):
        for lines in (["draw 1 2"],["draw 1","draw 2"]):
            with self.assertRaises(ValueError):
                fields(lines,"draw",23)
        self.assertEqual(fields(["actor 11 555","actor 1 42"],"actor 1",1),[42])

    def test_instrumentation_rejects_changed_hook(self):
        for source in ("","hook hook"):
            with self.assertRaises(ValueError):
                replace_once(source,"hook","capture")
