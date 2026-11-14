"""Synthetic P4 indexed-PNG sequence tests; no copyrighted game materials.

The local model uses a video-calibrated *assumption*, not observed timer calls.
"""
from __future__ import annotations

import contextlib
import hashlib
import io
import json
import struct
import tempfile
import unittest
import zlib
from pathlib import Path

from scummbucket.cli import main
from scummbucket.palette_sequence import (
    SequenceError, encode_indexed_png, export_palette_sequence,
    simulate_frame_palettes,
)
from test_inspector import index, make_zip
from test_palette_probe import fixture


def png_chunks(png: bytes):
    if not png.startswith(b"\x89PNG\r\n\x1a\n"):
        raise AssertionError("PNG signature missing")
    position = 8
    result = []
    while position < len(png):
        length = struct.unpack_from(">I", png, position)[0]
        tag = png[position + 4:position + 8]
        payload = png[position + 8:position + 8 + length]
        crc = struct.unpack_from(">I", png, position + 8 + length)[0]
        assert zlib.crc32(tag + payload) & 0xffffffff == crc
        result.append((tag, payload))
        position += length + 12
    assert position == len(png)
    return result


def parse_indexed_png(png: bytes):
    chunks = dict(png_chunks(png))
    width, height, depth, kind, compression, filtering, interlace = (
        struct.unpack(">IIBBBBB", chunks[b"IHDR"]))
    assert (depth, kind, compression, filtering, interlace) == (8, 3, 0, 0, 0)
    pixels = zlib.decompress(chunks[b"IDAT"])
    lines = [pixels[i * (width + 1):(i + 1) * (width + 1)] for i in range(height)]
    assert all(line[0] == 0 for line in lines)
    return width, height, b"".join(line[1:] for line in lines), chunks[b"PLTE"]


class IndexedPngTest(unittest.TestCase):
    def test_indexed_png_has_native_pixels_and_exact_palette(self):
        rgb = bytes(i % 256 for i in range(768))
        data = bytes([0, 1, 2, 3, 3, 2, 1, 0])
        png = encode_indexed_png(4, 2, data, rgb)
        self.assertEqual(parse_indexed_png(png),
                         (4, 2, data, rgb))
        self.assertEqual([tag for tag, _ in png_chunks(png)],
                         [b"IHDR", b"PLTE", b"IDAT", b"IEND"])

    def test_indexed_png_deterministic_and_no_transparency_chunk(self):
        palette = bytes([0] * 768)
        data = bytes([7] * 64)
        first = encode_indexed_png(8, 8, data, palette)
        self.assertEqual(encode_indexed_png(8, 8, data, palette), first)
        self.assertNotIn(b"tRNS", first)

    def test_invalid_palette_dimensions_or_indices_are_errors(self):
        for width, height, pixels, palette, expected in (
            (1, 1, b"\x01", bytes([2] * 767), "SEQUENCE_PALETTE_INVALID"),
            (2, 2, b"\x01\x02", bytes([2] * 768), "SEQUENCE_INDEX_COUNT_INVALID"),
            (0, 2, b"", bytes([2] * 768), "SEQUENCE_DIMENSIONS_INVALID"),
        ):
            with self.subTest(expected=expected):
                with self.assertRaises(SequenceError) as err:
                    encode_indexed_png(width, height, pixels, palette)
                self.assertEqual(err.exception.code, expected)


class PaletteTimelineTest(unittest.TestCase):
    def setUp(self):
        self.palette = bytearray(768)
        self.palette[5 * 3:5 * 3 + 3] = bytes([250, 10, 20])
        self.palette[6 * 3:6 * 3 + 3] = bytes([5, 30, 240])
        self.cycles = [{"id": 1, "rate_raw": 4096, "flags": 0,
                        "start_color": 5, "end_color": 6, "offset": 0}]

    def test_video_calibrated_frame_counter_sampling(self):
        # At four counter units/sec and four PNG fps, the first rotation is
        # at frame index 4, i.e., t = 1 second.
        frames = list(simulate_frame_palettes(
            bytes(self.palette), self.cycles, fps=4, frames=8, counter_rate=4))
        self.assertEqual(len(frames), 8)
        self.assertEqual([f["counter_total"] for f in frames], list(range(8)))
        self.assertEqual([f["counter_delta"] for f in frames],
                         [0, 1, 1, 1, 1, 1, 1, 1])
        self.assertEqual([len(f["rotation_events"]) for f in frames],
                         [0, 0, 0, 0, 1, 0, 0, 0])
        self.assertEqual(frames[0]["palette"], bytes(self.palette))
        self.assertEqual(frames[4]["palette"][5 * 3:5 * 3 + 3],
                         self.palette[6 * 3:6 * 3 + 3])
        self.assertEqual(frames[4]["timestamp_numerator"], 4)
        self.assertEqual(frames[4]["timestamp_denominator"], 4)

    def test_fractional_deltas_are_accumulated_deterministically(self):
        result = list(simulate_frame_palettes(
            bytes(self.palette), self.cycles, fps=6, frames=6, counter_rate=4))
        self.assertEqual([f["counter_total"] for f in result], [0, 0, 1, 2, 2, 3])
        self.assertEqual([f["counter_delta"] for f in result], [0, 0, 1, 1, 0, 1])

    def test_one_model_call_not_multiple_rotations_per_frame(self):
        result = list(simulate_frame_palettes(
            bytes(self.palette), self.cycles, fps=1, frames=2, counter_rate=100))
        self.assertEqual(result[1]["counter_delta"], 100)
        self.assertEqual(result[1]["rotation_events_total"], 1)

    def test_invalid_timing_and_zero_cycles_explicit(self):
        examples = [
            (0, 1, 60, self.cycles, "SEQUENCE_FPS_INVALID"),
            (61, 1, 60, self.cycles, "SEQUENCE_FPS_INVALID"),
            (30, 0, 60, self.cycles, "SEQUENCE_FRAME_COUNT_INVALID"),
            (30, 241, 60, self.cycles, "SEQUENCE_FRAME_COUNT_INVALID"),
            (30, 2, 0, self.cycles, "SEQUENCE_COUNTER_RATE_INVALID"),
            (30, 2, 601, self.cycles, "SEQUENCE_COUNTER_RATE_INVALID"),
            (30, 2, 60, [], "SEQUENCE_NO_CYCLES"),
        ]
        for fps, frames, rate, cycles, code in examples:
            with self.subTest(code=code):
                with self.assertRaises(SequenceError) as err:
                    list(simulate_frame_palettes(
                        bytes(self.palette), cycles,
                        fps=fps, frames=frames, counter_rate=rate))
                self.assertEqual(err.exception.code, code)


class SequenceExporterTest(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.source = self.root / "game.zip"
        self.dest = self.root / "sequence"
        make_zip(self.source, a=index(), b=fixture())

    def export(self, **kwargs):
        return export_palette_sequence(
            self.source, self.dest, room_id=1, fps=4,
            duration_seconds=2, counter_rate=4, **kwargs)

    def test_writes_native_indexed_frames_source_and_manifest(self):
        original_sha = hashlib.sha256(self.source.read_bytes()).hexdigest()
        result = self.export()
        self.assertEqual(result["status"], "success", result["diagnostics"])
        self.assertEqual(result["summary"]["frames_requested"], 8)
        self.assertEqual(result["summary"]["frames_written"], 8)
        self.assertEqual(result["summary"]["cycle_records"], 1)
        self.assertEqual(result["summary"]["unique_cycled_source_pixels"], 64)
        self.assertEqual(len(result["files"]), 10)  # 8 PNGs + original + CLUT
        self.assertEqual(len(result["frames"]), 8)
        self.assertEqual(result["timing"]["assumed_counter_units_per_second"], 4)
        self.assertEqual(result["timing"]["model"],
                         "user_selected_or_cross_room_counter_rate_hypothesis")
        self.assertFalse(result["timing"]["engine_timer_values_observed"])
        self.assertFalse(result["timing"]["seamless_loop_verified"])
        self.assertFalse(result["fidelity"]["comprehensive_background_animation"])
        self.assertTrue(result["fidelity"]["original_palette_indices_preserved"])
        self.assertEqual(hashlib.sha256(self.source.read_bytes()).hexdigest(),
                         original_sha)
        self.assertNotIn("counter", result["cycles"][0])
        self.assertNotIn("rotation_events", result["cycles"][0])

        first = (self.dest / result["frames"][0]["filename"]).read_bytes()
        fifth = (self.dest / result["frames"][4]["filename"]).read_bytes()
        source_image = (self.dest / "room-001_source-indexed.png").read_bytes()
        self.assertEqual(source_image, first)
        width, height, first_index, first_pal = parse_indexed_png(first)
        _, _, fifth_index, fifth_pal = parse_indexed_png(fifth)
        self.assertEqual((width, height), (8, 8))
        self.assertEqual(first_index, bytes(([5, 6] * 4) * 8))
        self.assertEqual(first_index, fifth_index)  # PLTE changes, not indices.
        self.assertNotEqual(first_pal, fifth_pal)
        self.assertEqual(fifth_pal[5 * 3:5 * 3 + 3],
                         first_pal[6 * 3:6 * 3 + 3])
        self.assertEqual(
            (self.dest / "room-001_initial-clut.rgb").read_bytes(), first_pal)
        saved = json.loads((self.dest / "manifest.json").read_text())
        self.assertEqual(saved["status"], "success")
        self.assertEqual(saved["provenance"]["initial_palette_sha256"],
                         hashlib.sha256(first_pal).hexdigest())
        self.assertTrue(all(
            hashlib.sha256((self.dest / file["name"]).read_bytes()).hexdigest()
            == file["sha256"] for file in saved["files"]))

    def test_repeated_export_refuses_overwrite(self):
        self.assertEqual(self.export()["status"], "success")
        old = (self.dest / "manifest.json").read_bytes()
        failure = self.export()
        self.assertEqual(failure["status"], "failed")
        self.assertIn("OUTPUT_COLLISION",
                      [d["code"] for d in failure["diagnostics"]])
        self.assertEqual((self.dest / "manifest.json").read_bytes(), old)

    def test_existing_future_frame_collision_is_preflighted(self):
        self.dest.mkdir()
        collision = self.dest / "room-001_frame-0003.png"
        collision.write_text("PRESERVE")
        failed = self.export()
        self.assertEqual(failed["status"], "failed")
        self.assertIn("OUTPUT_COLLISION",
                      [d["code"] for d in failed["diagnostics"]])
        self.assertEqual(collision.read_text(), "PRESERVE")
        self.assertEqual(len(list(self.dest.iterdir())), 1)

    def test_unsupported_codec_is_reported(self):
        make_zip(self.source, a=index(), b=fixture(image_code=251))
        result = self.export()
        self.assertEqual(result["status"], "failed")
        self.assertIn("STRIP_CODEC_UNSUPPORTED",
                      [d["code"] for d in result["diagnostics"]])
        self.assertFalse((self.dest / "manifest.json").exists())

    def test_static_only_short_export_reports_warnings(self):
        result = export_palette_sequence(
            self.source, self.dest, room_id=1,
            fps=2, duration_seconds=1, counter_rate=1)
        self.assertEqual(result["status"], "success")
        codes = [p["code"] for p in result["diagnostics"]]
        self.assertIn("SEQUENCE_NO_ROTATIONS_IN_DURATION", codes)
        self.assertIn("SEQUENCE_NO_PALETTE_DIFFERENCE", codes)
        self.assertEqual(result["summary"]["frames_written"], 2)

    def test_invalid_limits_have_no_side_effects(self):
        for extras, code in (
            ({"fps": 0}, "SEQUENCE_FPS_INVALID"),
            ({"duration_seconds": 0}, "SEQUENCE_DURATION_INVALID"),
            ({"counter_rate": 0}, "SEQUENCE_COUNTER_RATE_INVALID"),
            ({"duration_seconds": 10, "fps": 60}, "SEQUENCE_FRAME_LIMIT"),
        ):
            with self.subTest(code=code):
                report = export_palette_sequence(
                    self.source, self.dest, room_id=1, **extras)
                self.assertEqual(report["status"], "failed")
                self.assertIn(code, [p["code"] for p in report["diagnostics"]])
                self.assertFalse(self.dest.exists())

    def test_nonstandard_flags_not_suppressed(self):
        make_zip(self.source, a=index(), b=fixture(cycle_flag=4))
        result = self.export()
        self.assertEqual(result["status"], "success", result["diagnostics"])
        self.assertIn("CYCLE_FLAGS_UNVERIFIED",
                      [d["code"] for d in result["diagnostics"]])

    def test_cli_success_and_nonzero_on_existing_output(self):
        argv = ["palette-sequence", str(self.source), "--room", "1",
                "--fps", "4", "--duration-seconds", "2",
                "--counter-rate", "4", "--output-dir", str(self.dest)]
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            exitcode = main(argv)
        self.assertEqual(exitcode, 0)
        self.assertIn("8/8 frames", output.getvalue())
        self.assertIn("Not engine-clock verified", output.getvalue())
        with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
            self.assertEqual(main(argv), 2)


if __name__ == "__main__":
    unittest.main()
