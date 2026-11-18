from hashlib import sha256
import json
from pathlib import Path
import struct
import tempfile
import unittest
from unittest.mock import patch

from scummbucket.inspector import XOR_KEY
from scummbucket.room35_waterfall import export_room35, paint_indexed_layer, render_waterfall
from test_inspector import chunk
from test_object_images import codec_pixels
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

    def test_export_writes_native_components_and_rejects_existing_output(self):
        def smap(codec, index):
            return chunk("SMAP", struct.pack("<I", 12) + codec_pixels(codec, index, height=1))

        rmhd = chunk("RMHD", struct.pack("<HH", 8, 1))
        rmim = chunk("RMIM", chunk("IM00", smap(68, 176)))
        clut = chunk("CLUT", self.palette)
        trns = chunk("TRNS", b"\xbf")
        imhd = chunk("IMHD", struct.pack("<HHHBBHHHH", 364, 8, 0, 0, 0, 0, 0, 8, 1))
        images = b"".join(chunk(f"IM{n:02X}", smap(68, 160 + n)) for n in range(1, 9))
        obim = chunk("OBIM", imhd + images)
        obcd = chunk("OBCD", chunk("CDHD", struct.pack("<HBB", 364, 0, 0)))
        data = chunk("ROOM", rmhd + rmim + clut + trns + obim + obcd)
        resource = bytes(value ^ XOR_KEY for value in data)
        archive_hash = sha256(resource).hexdigest()
        scene = dict(room_id=35, room_offset=0, room_size=len(data), palette_cycles=self.records,
                     objects=[dict(object_id=364, status="paired",
                                   code=dict(source_offset=data.index(b"OBCD"), byte_length=len(obcd)),
                                   image=dict(source_offset=data.index(b"OBIM"),
                                              image_state_tags=[f"IM{n:02X}" for n in range(1, 9)]))])
        inventory = dict(status="success", scene_inventory=dict(rooms=[scene]),
                         sources=[dict(sha256=sha256(b"index").hexdigest()),
                                  dict(sha256=archive_hash)])
        args = dict(effective_bit92=False, updates=[[5]] + [[] for _ in range(7)])
        with (tempfile.TemporaryDirectory() as tmp,
              patch("scummbucket.room35_waterfall.inspect", return_value=inventory),
              patch("scummbucket.room35_waterfall._read_pair",
                    return_value=(b"index", resource, "MONKEY2.000", "MONKEY2.001")),
              patch("scummbucket.room35_waterfall.ARCHIVE_SHA256", archive_hash)):
            output = Path(tmp) / "new"
            manifest = export_room35("input", output, **args)
            self.assertEqual(json.loads((output / "manifest.json").read_bytes()), manifest)
            placement, = (row for row in manifest["events"] if row["kind"] == "object_position")
            self.assertEqual(placement["evidence"], "archive_decoded")
            self.assertEqual(placement["payload"]["source_offset"], data.index(b"CDHD"))
            self.assertEqual((output / "state-01.indices").read_bytes(), bytes([161] * 8))
            self.assertEqual((output / "state-01.rgb").read_bytes()[176 * 3], 191)
            for name, digest in manifest["files"].items():
                self.assertEqual(sha256((output / name).read_bytes()).hexdigest(), digest)
            with self.assertRaises(FileExistsError):
                export_room35("input", output, **args)
