"""Synthetic tests of limited P2 SCUMM v5 OBIM pixel and mask codecs."""
import contextlib
import io
import json
import struct
import tempfile
import unittest
from pathlib import Path

from scummbucket.cli import main
from scummbucket.object_images import (
    ImageDecodeError, decode_strip, decode_mask_strip, encode_png,
    decode_object_state, export_object_images,
)
from test_inspector import chunk, index, make_zip


def codec_pixels(code, color=5, height=8):
    # A constant-color source with no color-change bits.
    # This is legal for both 4-8 bit major/minor and basic SCUMM strip codecs.
    return bytes([code, color]) + bytes(2 + 3 * height)


def synth_obim(*, bad_code=None):
    width, height = 8, 8
    head = struct.pack("<HHHBBHHHH", 99, 2, 0, 0, 0, 0, 0, width, height)
    mask_payload = struct.pack("<H", 10) + bytes([0x88, 0x81])
    masks = b"".join(chunk(z, mask_payload) for z in ("ZP01", "ZP02", "ZP03"))
    state1 = chunk("SMAP", struct.pack("<I", 12) + codec_pixels(37 if bad_code is None else bad_code))
    state2 = chunk("SMAP", struct.pack("<I", 12) + codec_pixels(68, 1))
    return chunk("OBIM", chunk("IMHD", head) +
                 chunk("IM01", state1 + masks) +
                 chunk("IM02", state2 + masks))


def synthetic_resource(*, bad_code=None, transparent_color=5, include_palette=True):
    pal = bytearray(768)
    pal[5 * 3:5 * 3 + 3] = b"\x12\x34\x56"
    pal[1 * 3:1 * 3 + 3] = b"\x33\x44\x55"
    children = chunk("RMHD", b"\x00")
    if include_palette:
        children += chunk("CLUT", bytes(pal))
    children += chunk("TRNS", bytes([transparent_color, 0]))
    children += synth_obim(bad_code=bad_code)
    children += chunk("OBCD", chunk("CDHD", struct.pack("<H", 99) + b"\x00" * 11))
    room = chunk("ROOM", children)
    loff = chunk("LOFF", b"\x01\x01" + struct.pack("<I", 30))
    return chunk("LECF", loff + chunk("LFLF", room))


class StripCodecTest(unittest.TestCase):
    def test_basic_vertical_transparent(self):
        rgb, transp, used = decode_strip(37, codec_pixels(37)[1:], 8)
        self.assertEqual(rgb, bytes([5] * 64))
        self.assertTrue(transp)
        self.assertGreater(used, 0)

    def test_major_minor_nontransparent(self):
        idx, transp, _ = decode_strip(68, codec_pixels(68, 1)[1:], 8)
        self.assertEqual(idx, bytes([1] * 64))
        self.assertFalse(transp)

    def test_unsupported_codec_is_error(self):
        with self.assertRaises(ImageDecodeError) as err:
            decode_strip(251, b"\x01\x02\x03", 8)
        self.assertEqual(err.exception.code, "STRIP_CODEC_UNSUPPORTED")

    def test_strip_truncation_is_error(self):
        with self.assertRaises(ImageDecodeError) as err:
            decode_strip(37, b"\x01\x00", 8)
        self.assertEqual(err.exception.code, "STRIP_BITSTREAM_TRUNCATED")

    def test_zmask_repeat_and_literals(self):
        expanded, used = decode_mask_strip(bytes([0x88, 0xAA]), 8)
        self.assertEqual(expanded, bytes([0xAA] * 8))
        self.assertEqual(used, 2)
        raw, _ = decode_mask_strip(bytes([3, 1, 2, 3]), 3)
        self.assertEqual(raw, b"\x01\x02\x03")

    def test_mask_overflow_and_zero_run_rejected(self):
        for data, code in ((b"\x89\x11", "MASK_RUN_OVERFLOW"),
                           (b"\x00", "MASK_ZERO_RUN"),
                           (b"\x02\x10", "MASK_STREAM_TRUNCATED")):
            with self.subTest(code=code):
                with self.assertRaises(ImageDecodeError) as err:
                    decode_mask_strip(data, 8)
                self.assertEqual(err.exception.code, code)

    def test_png_signature_and_dimension_fields(self):
        png = encode_png(8, 8, bytes(8 * 8 * 4), rgba=True)
        self.assertEqual(png[:8], b"\x89PNG\r\n\x1a\n")
        self.assertEqual(png[12:16], b"IHDR")
        self.assertEqual(struct.unpack_from(">II", png, 16), (8, 8))
        self.assertEqual(png[25], 6)

    def test_png_wrong_pixel_count_rejected(self):
        with self.assertRaises(ImageDecodeError) as err:
            encode_png(8, 8, b"\x00", rgba=True)
        self.assertEqual(err.exception.code, "PNG_PIXEL_BUFFER_INVALID")


class ImageExportTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.source = self.root / "game.zip"
        self.output = self.root / "decoded"
        make_zip(self.source, a=index(), b=synthetic_resource())

    def test_export_two_images_and_six_masks_and_manifest(self):
        report = export_object_images(self.source, self.output, room_id=1, object_id=99)
        self.assertEqual(report["status"], "success", report["diagnostics"])
        self.assertEqual(report["summary"]["success"], 2)
        self.assertEqual(report["summary"]["failed"], 0)
        self.assertEqual(len(report["files"]), 8)
        self.assertEqual(report["rendering_status"], "pixel_decoded_not_compared_to_reference")
        self.assertEqual(report["layering_status"], "zplanes_separated_not_composited")
        for state in report["states"]:
            self.assertEqual(len(state["masks"]), 3)
            self.assertEqual(state["metadata"]["width"], 8)
            self.assertEqual(state["metadata"]["height"], 8)
            self.assertEqual((self.output / state["image"]).read_bytes()[:8],
                             b"\x89PNG\r\n\x1a\n")
        self.assertEqual(json.loads((self.output / "manifest.json").read_text())["files"],
                         report["files"])

    def test_transparent_pixel_and_nontransparent_codec(self):
        import zlib
        report = export_object_images(self.source, self.output, room_id=1, object_id=99,
                                      include_masks=False)
        self.assertEqual(report["status"], "success", report["diagnostics"])
        self.assertEqual(len(report["files"]), 2)
        for idx, alpha in ((0, 0), (1, 255)):
            png = (self.output / report["states"][idx]["image"]).read_bytes()
            # Read the known synthetic unfiltered PNG IDAT contents.
            p = png.index(b"IDAT")
            n = struct.unpack_from(">I", png, p - 4)[0]
            raw = zlib.decompress(png[p + 4:p + 4 + n])
            self.assertEqual(raw[0], 0)
            self.assertEqual(raw[4], alpha)

    def test_corrupted_strip_reports_error_for_state(self):
        make_zip(self.source, a=index(), b=synthetic_resource(bad_code=251))
        report = export_object_images(self.source, self.output, room_id=1, object_id=99)
        self.assertEqual(report["status"], "partial")
        self.assertEqual(report["summary"]["success"], 1)
        self.assertEqual(report["summary"]["failed"], 1)
        self.assertEqual(report["summary"]["unsupported"], 1)
        self.assertIn("STRIP_CODEC_UNSUPPORTED",
                      [p["code"] for p in report["diagnostics"]])
        self.assertEqual(json.loads((self.output / "manifest.json").read_text())["status"],
                         "partial")

    def test_existing_manifest_refused_with_no_overwrite(self):
        self.output.mkdir()
        (self.output / "manifest.json").write_text("KEEP")
        report = export_object_images(self.source, self.output, room_id=1, object_id=99)
        self.assertEqual(report["status"], "failed")
        self.assertIn("MANIFEST_EXISTS", [e["code"] for e in report["diagnostics"]])
        self.assertEqual((self.output / "manifest.json").read_text(), "KEEP")
        self.assertEqual(len(list(self.output.iterdir())), 1)

    def test_missing_palette_is_structured_failure(self):
        make_zip(self.source, a=index(), b=synthetic_resource(include_palette=False))
        report = export_object_images(self.source, self.output, room_id=1, object_id=99)
        self.assertEqual(report["status"], "failed")
        self.assertIn("CLUT_COUNT_INVALID", [e["code"] for e in report["diagnostics"]])

    def test_input_is_not_changed(self):
        before = self.source.read_bytes()
        report = export_object_images(self.source, self.output, room_id=1, object_id=99)
        self.assertEqual(report["status"], "success", report["diagnostics"])
        self.assertEqual(self.source.read_bytes(), before)

    def test_cli_images_success_and_refuses_existing(self):
        argv = ["images", str(self.source), "--room", "1", "--object", "99",
                "--output-dir", str(self.output)]
        with contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(main(argv), 0)
            self.assertEqual(main(argv), 2)


if __name__ == "__main__":
    unittest.main()
