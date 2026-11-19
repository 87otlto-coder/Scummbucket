import struct
import unittest

from scummbucket.inspector import chunks
from scummbucket.object_images import ImageDecodeError, _decode_zplane
from scummbucket.palette_probe import PaletteProbeError, decode_room_background_indexed
from test_inspector import chunk

from scummbucket.zplanes import compare_plane, compose_planes, crop_plane, pack_plane


class ZPlaneTests(unittest.TestCase):
    def test_sparse_literal_and_repeat(self):
        payload = struct.pack("<3H", 14, 0, 17) + bytes((2, 0x80, 1, 0x82, 0xff))
        packet = b"ZP01" + struct.pack(">I", len(payload) + 8) + payload
        plane, = chunks(packet, 0, len(packet), "synthetic")
        self.assertEqual(pack_plane(_decode_zplane(packet, plane, width=24, height=2), 24, 2),
                         bytes((128, 0, 255, 1, 0, 255)))
        for damaged in (packet[:8] + bytes((3, 0)) + packet[10:], packet[:-1] + bytes((0,))):
            with self.assertRaises(ImageDecodeError):
                _decode_zplane(damaged[:-1] if damaged[-1] == 0 else damaged,
                               plane, width=24, height=2)

    def test_ordered_replacement_union_and_restoration(self):
        baseline = {1: b"\xaa\xaa", 2: b"\xcc\xcc"}
        first = (0, 0, 16, 1, {1: b"\x01\x04"}, (False, True))
        second = (8, 0, 8, 1, {1: b"\x00"}, (False,))
        self.assertEqual(compose_planes(baseline, 16, 1, [first])[1], b"\x01\xae")
        self.assertEqual(compose_planes(baseline, 16, 1, [first, second])[1], b"\x01\x00")
        self.assertEqual(compose_planes(baseline, 16, 1, [])[1], baseline[1])
        self.assertEqual(compose_planes(baseline, 16, 1, [first, second])[2], baseline[2])
        clipped = (-8, 0, 16, 1, {1: b"\x08\x10"}, (False, False))
        self.assertEqual(compose_planes(baseline, 16, 1, [clipped])[1], b"\x10\xaa")

    def test_crop_and_bit_diagnostics(self):
        self.assertEqual(crop_plane(b"\xff\x80\x00\x01", 16, 2,
                                    x=8, y=0, view_width=8, view_height=2), b"\x80\x01")
        report = compare_plane(b"\x80\x01", b"\x40\x01", 8, 2)
        self.assertEqual(report["bytes_mismatched"], 1)
        self.assertEqual(report["bits_mismatched"], 2)
        self.assertEqual((report["first_mismatch"]["x"], report["first_mismatch"]["y"]), (0, 0))

    def test_background_resource_exposes_native_masks_and_layout(self):
        bitmap = chunk("SMAP", struct.pack("<I", 12) + bytes((1,)) + bytes(16))
        mask = chunk("ZP01", struct.pack("<H", 10) + bytes((0x82, 0x81)))
        rmih = chunk("RMIH", struct.pack("<H", 1))
        header = chunk("RMHD", struct.pack("<HHH", 8, 2, 0)) + chunk("CLUT", bytes(768))
        room = chunk("ROOM", header + chunk("RMIM", rmih + chunk("IM00", bitmap + mask)))
        bg = decode_room_background_indexed(room, room_offset=0, room_length=len(room),
                                            include_masks=True)
        self.assertEqual(bg["zplane_count"], 2)
        plane = bg["zplane_masks"]["ZP01"]
        self.assertEqual(plane["offset"], room.index(b"ZP01"))
        self.assertEqual(plane["strip_offsets"], [10])
        self.assertEqual(pack_plane(plane["pixels"], 8, 2), b"\x81\x81")
        unsupported = room.replace(b"ZP01", b"ZP99")
        with self.assertRaises(PaletteProbeError):
            decode_room_background_indexed(unsupported, room_offset=0, room_length=len(room),
                                           include_masks=True)
