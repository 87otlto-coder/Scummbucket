import unittest

from scummbucket.room35_waterfall import paint_indexed_layer, render_waterfall
from scummbucket.scene_events import serialize_scene_events


class Room35WaterfallTests(unittest.TestCase):
    def setUp(self):
        self.palette = bytes(value for index in range(256) for value in (index, 0, 0))
        self.background = dict(width=3, height=1, indexed_pixels=b"\xb0\xa0\x02",
                               initial_palette=self.palette)
        self.states = [
            (dict(object_id=364, state_tag=f"IM{number:02X}", width=2, height=1,
                  source_offset=number),
             bytes((160 + number, 191)), bytes((255, 0)), {})
            for number in range(1, 9)
        ]
        self.records = [
            dict(id=1, start_color=176, end_color=191, rate_raw=3072, flags=4, offset=8),
            dict(id=2, start_color=160, end_color=175, rate_raw=2688, flags=4, offset=17),
        ]

    def render(self, *, bit=False, states=None):
        return render_waterfall(self.background, self.states if states is None else states,
                                self.records, x=1, y=0, effective_bit92=bit,
                                updates=[[5], [1], [], [], [], [], [], []])

    def test_native_pixels_and_palette_remain_separate(self):
        frames, events, diagnostics = self.render()
        self.assertEqual([raster for raster, _ in frames],
                         [bytes((176, 161 + i, 2)) for i in range(8)])
        self.assertEqual(frames[0][1][176 * 3], 191)
        self.assertEqual(frames[0][1][160 * 3], 160)
        self.assertEqual(frames[1][1][160 * 3], 175)
        self.assertEqual(frames[1][1], frames[-1][1])
        self.assertEqual([row["payload"]["state"] for row in events if row["kind"] == "object_draw"],
                         list(range(1, 9)))
        self.assertEqual([row["flags"] for row in diagnostics], [4, 4])
        source = dict(game_edition="synthetic", archive_sha256="a" * 64,
                      logical_room=35, physical_room=35)
        self.assertEqual(self.render(), (frames, events, diagnostics))
        self.assertIn(b'"evidence":"synthetic"', serialize_scene_events(
            dict(schema="p4-scene-events/1", clock=None, source=source, events=events)))

    def test_rejects_unestablished_branch_and_reordered_states(self):
        with self.assertRaisesRegex(ValueError, "effective Bit92"):
            self.render(bit=None)
        with self.assertRaisesRegex(ValueError, "effective Bit92"):
            self.render(bit=True)
        with self.assertRaisesRegex(ValueError, "authored Room 35 waterfall state 1"):
            self.render(states=self.states[::-1])

    def test_clipping_preserves_opaque_palette_index(self):
        self.assertEqual(paint_indexed_layer(bytes((3, 4)), 2, 1, bytes((7, 191)),
                                             bytes((0, 255)), 2, 1, -1, 0),
                         bytes((191, 4)))
