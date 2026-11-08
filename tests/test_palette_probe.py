"""Synthetic palette cycling and native background tests, no game files."""
from __future__ import annotations

import contextlib
import io
import json
import struct
import tempfile
import unittest
from pathlib import Path

from scummbucket.cli import main
from scummbucket.inspector import inspect
from scummbucket.palette_probe import (
    PaletteProbeError, advance_palette, decode_room_background_indexed,
    palette_probe, prepare_cycles, simulate_palette_snapshots,
)
from test_inspector import chunk, index, make_zip


def fixture(*, image_code=1, cycle_flag=0, cycle_rate=4096, bad_offset=False):
    # Native room bitmap, 8x8 pixels. Two palette entries alternate.
    pixels = bytes(([5, 6] * 4) * 8)
    smap = chunk("SMAP",
                 struct.pack("<I", 200 if bad_offset else 12) +
                 bytes([image_code]) + pixels)
    rmim = chunk("RMIM", chunk("RMIH", b"\x00\x00") +
                 chunk("IM00", smap))
    room_palette = bytearray(768)
    room_palette[5 * 3:5 * 3 + 3] = bytes([250, 10, 20])
    room_palette[6 * 3:6 * 3 + 3] = bytes([5, 30, 240])
    cycles = chunk("CYCL", bytes([1, 0, 0]) +
                   struct.pack(">HHBB", cycle_rate, cycle_flag, 5, 6) +
                   b"\x00")
    room = chunk("ROOM", chunk("RMHD", struct.pack("<HHH", 8, 8, 0)) +
                 cycles + chunk("CLUT", bytes(room_palette)) + rmim)
    loff = chunk("LOFF", bytes([1, 1]) + struct.pack("<I", 30))
    return chunk("LECF", loff + chunk("LFLF", room))


class PaletteCycleMathTest(unittest.TestCase):
    def test_forward_and_reverse_color_rotation(self):
        sample = bytearray(768)
        sample[5 * 3:5 * 3 + 3] = b"\x01\x02\x03"
        sample[6 * 3:6 * 3 + 3] = b"\x04\x05\x06"
        for flags, expected in ((0, b"\x04\x05\x06"), (2, b"\x04\x05\x06")):
            # A two-element sequence swaps identically in either direction.
            with self.subTest(flags=flags):
                pal = bytearray(sample)
                cycles, warnings = prepare_cycles([{
                    "id": 1, "rate_raw": 4096, "flags": flags,
                    "start_color": 5, "end_color": 6, "offset": 3,
                }])
                self.assertEqual(warnings, [])
                self.assertEqual(cycles[0]["delay_counter_units"], 4)
                self.assertEqual(advance_palette(pal, cycles), [])
                self.assertEqual(advance_palette(pal, cycles), [])
                self.assertEqual(advance_palette(pal, cycles), [])
                changes = advance_palette(pal, cycles)
                self.assertEqual(len(changes), 1)
                self.assertEqual(pal[5 * 3:5 * 3 + 3], expected)
                self.assertEqual(cycles[0]["counter"], 0)
                self.assertEqual(cycles[0]["rotation_events"], 1)

    def test_direction_for_three_color_entries(self):
        raw = bytearray(768)
        for i, color in enumerate((b"\x01\x00\x00", b"\x02\x00\x00", b"\x03\x00\x00")):
            raw[(5 + i) * 3:(6 + i) * 3] = color
        for flag, expected in ((0, 3), (2, 2)):
            cycles, _ = prepare_cycles([{
                "id": 1, "rate_raw": 16384, "flags": flag,
                "start_color": 5, "end_color": 7, "offset": 0}])
            pal = bytearray(raw)
            advance_palette(pal, cycles)
            self.assertEqual(pal[5 * 3], expected)

    def test_explicit_counter_delta_changes_event_schedule(self):
        palette = bytearray(768)
        palette[5 * 3:5 * 3 + 3] = b"\xff\x00\x00"
        palette[6 * 3:6 * 3 + 3] = b"\x00\x00\xff"
        cycles, _ = prepare_cycles([{
            "id": 1, "rate_raw": 4096, "flags": 0,
            "start_color": 5, "end_color": 6, "offset": 0}])
        snapshots = simulate_palette_snapshots(bytes([5, 6]), bytes(palette), cycles,
                                               [0, 1, 2, 3], counter_increment=2)
        self.assertEqual([s["visible_changed_pixels"] for s in snapshots], [0, 0, 2, 2])
        self.assertEqual([s["cumulative_counter_units"] for s in snapshots],
                         [0, 2, 4, 6])
        self.assertEqual(snapshots[2]["total_rotation_events"], 1)

    def test_single_update_never_rotates_more_than_once(self):
        palette = bytearray(768)
        palette[5 * 3:5 * 3 + 3] = b"\x01\x00\x00"
        palette[6 * 3:6 * 3 + 3] = b"\x02\x00\x00"
        cycles, _ = prepare_cycles([{
            "id": 1, "rate_raw": 4096, "flags": 0,
            "start_color": 5, "end_color": 6, "offset": 0}])
        changed = advance_palette(palette, cycles, delta=13)
        self.assertEqual(len(changed), 1)
        self.assertEqual(cycles[0]["rotation_events"], 1)
        self.assertEqual(cycles[0]["counter"], 1)

    def test_invalid_delta_rejected(self):
        for delta in (-1, 65536, True, 2.5):
            with self.subTest(delta=delta):
                with self.assertRaises(PaletteProbeError) as context:
                    advance_palette(bytearray(768), [], delta=delta)
                self.assertEqual(context.exception.code, "COUNTER_DELTA_INVALID")

    def test_zero_engine_delay_flagged_and_not_rotated(self):
        cycles, findings = prepare_cycles([{
            "id": 3, "rate_raw": 65535, "flags": 0xD906,
            "start_color": 97, "end_color": 98, "offset": 0}])
        self.assertEqual(cycles[0]["delay_counter_units"], 0)
        self.assertIn("CYCLE_DISABLED_ZERO_THRESHOLD",
                      [f["code"] for f in findings])
        self.assertEqual(advance_palette(bytearray(768), cycles), [])

    def test_duplicate_cycle_id_is_error(self):
        record = {"id": 1, "rate_raw": 512, "flags": 0,
                  "start_color": 5, "end_color": 6, "offset": 0}
        with self.assertRaises(PaletteProbeError):
            prepare_cycles([record, record])

    def test_snapshot_timing_counts_are_synthetic(self):
        palette = bytearray(768)
        palette[5 * 3:5 * 3 + 3] = b"\xff\x00\x00"
        palette[6 * 3:6 * 3 + 3] = b"\x00\x00\xff"
        cycles, _ = prepare_cycles([{
            "id": 1, "rate_raw": 4096, "flags": 0,
            "start_color": 5, "end_color": 6, "offset": 0}])
        snaps = simulate_palette_snapshots(
            bytes([5, 6, 5, 6]), bytes(palette), cycles, [0, 4, 8])
        self.assertEqual([s["visible_changed_pixels"] for s in snaps], [0, 4, 0])
        self.assertEqual([s["total_rotation_events"] for s in snaps], [0, 1, 2])


class PaletteBackgroundTest(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.root = Path(temp.name)
        self.archive = self.root / "game.zip"
        self.dest = self.root / "output"
        make_zip(self.archive, a=index(), b=fixture())

    def test_indexed_background_eight_by_eight(self):
        inv = inspect(self.archive)
        self.assertEqual(inv["status"], "success", inv["diagnostics"])
        from scummbucket.inspector import XOR_KEY, _read_pair
        raw = _read_pair(self.archive)[1]
        decoded = bytes(byte ^ XOR_KEY for byte in raw)
        room = inv["resources"]["rooms"][0]
        bg = decode_room_background_indexed(
            decoded, room_offset=room["room_offset"], room_length=room["room_size"])
        self.assertEqual((bg["width"], bg["height"]), (8, 8))
        self.assertEqual(bg["indexed_pixels"], bytes(([5, 6] * 4) * 8))
        self.assertEqual(len(bg["strips"]), 1)
        self.assertEqual(bg["strips"][0]["codec"], 1)

    def test_probe_exports_three_nonoverwriting_pngs(self):
        before = self.archive.read_bytes()
        result = palette_probe(self.archive, self.dest, room_id=1,
                               ticks=[0, 4, 8])
        self.assertEqual(result["status"], "success", result["diagnostics"])
        self.assertEqual(result["summary"],
                         {"snapshots": 3, "visible_cycle_pixels": 64,
                          "cycle_records": 1})
        self.assertEqual([s["visible_changed_pixels_vs_initial"] for s in result["snapshots"]],
                         [0, 64, 0])
        self.assertEqual(len(result["files"]), 3)
        self.assertTrue(all((self.dest / f["filename"]).read_bytes().startswith(
            b"\x89PNG\r\n\x1a\n") for f in result["files"]))
        self.assertEqual(json.loads((self.dest / "manifest.json").read_text())["status"],
                         "success")
        self.assertFalse(result["verification"]["runtime_observed"])
        self.assertEqual(self.archive.read_bytes(), before)

    def test_image_codec_failure_and_no_silent_output(self):
        make_zip(self.archive, a=index(), b=fixture(image_code=251))
        result = palette_probe(self.archive, self.dest, room_id=1, ticks=[0, 4])
        self.assertEqual(result["status"], "failed")
        self.assertIn("STRIP_CODEC_UNSUPPORTED",
                      [e["code"] for e in result["diagnostics"]])
        self.assertFalse((self.dest / "manifest.json").exists())

    def test_out_of_bounds_strip_pointer_fails(self):
        make_zip(self.archive, a=index(), b=fixture(bad_offset=True))
        result = palette_probe(self.archive, self.dest, room_id=1, ticks=[0])
        self.assertEqual(result["status"], "failed")
        self.assertIn("BACKGROUND_SMAP_OFFSET_INVALID",
                      [e["code"] for e in result["diagnostics"]])

    def test_nonstandard_flags_are_retained_as_diagnostics(self):
        make_zip(self.archive, a=index(), b=fixture(cycle_flag=4))
        result = palette_probe(self.archive, self.dest, room_id=1, ticks=[0, 4])
        self.assertEqual(result["status"], "success")
        self.assertTrue(any(e["code"] == "CYCLE_FLAGS_UNVERIFIED"
                            for e in result["diagnostics"]))
        self.assertEqual(result["cycles"][0]["nonstandard_flag_bits"], 4)

    def test_cli_explicit_increment_changes_schedule(self):
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            code = main(["palette-probe", str(self.archive), "--room", "1",
                         "--ticks", "0", "1", "2", "--counter-increment", "4",
                         "--output-dir", str(self.dest)])
        self.assertEqual(code, 0)
        report = json.loads((self.dest / "manifest.json").read_text())
        self.assertEqual(report["selection"]["counter_increment"], 4)
        self.assertEqual(
            [f["visible_changed_pixels_vs_initial"] for f in report["snapshots"]],
            [0, 64, 0])
        self.assertEqual(
            [f["cumulative_counter_units"] for f in report["snapshots"]],
            [0, 4, 8])
        self.assertIn("cumulative counter units", output.getvalue())

    def test_invalid_counter_increment_is_reported(self):
        report = palette_probe(self.archive, self.dest, room_id=1,
                               ticks=[0], counter_increment=0)
        self.assertEqual(report["status"], "failed")
        self.assertIn("COUNTER_INCREMENT_INVALID",
                      [d["code"] for d in report["diagnostics"]])
        self.assertFalse(self.dest.exists())

    def test_existing_manifest_refuses_overwrite(self):
        self.dest.mkdir()
        (self.dest / "manifest.json").write_text("KEEP")
        result = palette_probe(self.archive, self.dest, room_id=1, ticks=[0, 4])
        self.assertEqual(result["status"], "failed")
        self.assertIn("OUTPUT_COLLISION", [e["code"] for e in result["diagnostics"]])
        self.assertEqual((self.dest / "manifest.json").read_text(), "KEEP")

    def test_invalid_ticks_and_missing_room_are_explicit(self):
        for ticks in ([0, 0], [-1], [4097], []):
            with self.subTest(ticks=ticks):
                result = palette_probe(self.archive, self.dest, room_id=1, ticks=ticks)
                self.assertEqual(result["status"], "failed")
                self.assertIn("TICKS_INVALID", [e["code"] for e in result["diagnostics"]])
        missing = palette_probe(self.archive, self.dest, room_id=99, ticks=[0])
        self.assertEqual(missing["status"], "failed")
        self.assertIn("ROOM_NOT_FOUND", [e["code"] for e in missing["diagnostics"]])

    def test_cli_explicitly_calls_frames_hypothetical(self):
        output = io.StringIO()
        argv = ["palette-probe", str(self.archive), "--room", "1",
                "--ticks", "0", "4", "8", "--output-dir", str(self.dest)]
        with contextlib.redirect_stdout(output):
            code = main(argv)
        self.assertEqual(code, 0)
        self.assertIn("hypothetical PNG snapshots", output.getvalue())
        self.assertIn("real gameplay execution and timing remain unverified",
                      output.getvalue().lower())
        with contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(main(argv), 2)


if __name__ == "__main__":
    unittest.main()
