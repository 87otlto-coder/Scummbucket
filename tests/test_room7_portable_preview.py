"""Synthetic tests for portable Room 7 preview/save/archive cross-check.

No original game bytes, previews or captured engine pixels are committed.
"""
import gzip
import hashlib
import io
import json
from pathlib import Path
import struct
import tempfile
import unittest
import zipfile

from PIL import Image

from fixture_scummvm_save import synthetic_scummvm_save
from scummbucket.palette_probe import prepare_cycles, advance_palette
from scummbucket.room7_portable_preview import (
    verify_saved_preview, parse_room7_cycles, PortableRoom7Error)


CYCLES = [
    (1, 384, 0, 16, 18),
    (2, 384, 0, 176, 177),
    (3, 459, 0, 178, 179),
    (4, 306, 0, 180, 181),
    (5, 228, 0, 182, 183),
    (6, 153, 0, 184, 185),
]
COUNTERS = (12, 12, 26, 35, 13, 80)


def synthetic_archive():
    entries = b"".join(
        bytes((cid, 0x3c, 0)) + rate.to_bytes(2, "big") +
        flags.to_bytes(2, "big") + bytes((start, end))
        for cid, rate, flags, start, end in CYCLES
    ) + bytes(2)
    child = b"CYCL" + (len(entries)+8).to_bytes(4, "big") + entries
    room = b"ROOM" + (len(child)+8).to_bytes(4, "big") + child
    return bytes(x ^ 0x69 for x in room)


def synthetic_save():
    slot = bytearray(16 * 8)
    for index, (cid, rate, flags, start, end) in enumerate(CYCLES):
        struct.pack_into("<HHHBB", slot, index*8,
                         16384 // rate, COUNTERS[index], flags, start, end)
    raw = synthetic_scummvm_save(compressed=False) + b"marker" + bytes(slot)
    return gzip.compress(raw, mtime=0)


class PortablePreviewTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.dir = Path(self.temp.name)
        self.save = self.dir / "monkey2.s01"
        self.save.write_bytes(synthetic_save())
        self.preview = self.dir / "play.zip"
        self.archive = synthetic_archive()
        self.sha = hashlib.sha256(self.archive).hexdigest()
        self.records = [
            dict(id=cid, rate_raw=rate, flags=flags,
                 start_color=start, end_color=end, offset=100+i*9)
            for i, (cid, rate, flags, start, end) in enumerate(CYCLES)
        ]
        self.index_sha = "a" * 64
        self.make_preview()

    def make_preview(self, tamper=None, time_mutation=None, extra=False,
                     reported_palette_corruption=False):
        initial = bytearray(768)
        for _, _, _, start, end in CYCLES:
            for color in range(start, end+1):
                initial[color*3:color*3+3] = bytes((color, color ^ 17, color ^ 23))
        cycles, issues = prepare_cycles(self.records)
        self.assertFalse(issues)
        for index, cycle in enumerate(cycles):
            cycle["counter"] = COUNTERS[index]
        palette = bytearray(initial)
        frame_rows = []
        members = {}
        for frame in range(1, 5):
            before = bytes(palette)
            delta = 6 if time_mutation is None or frame != 2 else time_mutation
            advance_palette(palette, cycles, delta=6)
            after = bytes(palette)
            sha = hashlib.sha256(after).hexdigest()
            if reported_palette_corruption and frame == 3:
                sha = "f" * 64
            png_palette = bytearray(after)
            if tamper == frame:
                png_palette[16*3] ^= 1
            image = Image.frombytes("P", (320, 144), bytes([16]) * (320*144))
            image.putpalette(bytes(png_palette))
            stream = io.BytesIO()
            image.save(stream, format="PNG")
            members[f"viewport-{frame:03}.png"] = stream.getvalue()
            frame_rows.append({
                "id": frame, "present_ms": 1000 + 100*frame,
                "timer_pair": [delta, delta],
                "palette_stages_sha256": [
                    hashlib.sha256(before).hexdigest(), sha, sha, sha],
            })
        report = {
            "schema": "room7-sweep/1",
            "run": {
                "room": 7, "archives": {
                    "MONKEY2.000": self.index_sha, "MONKEY2.001": self.sha},
                "save_sha256": hashlib.sha256(self.save.read_bytes()).hexdigest(),
                "debugger_equivalent_entry": False,
                "entry_provenance": {
                    "method": "loaded_private_save_no_debugger_or_injected_walk",
                },
            },
            "frames": frame_rows,
        }
        members["report.json"] = json.dumps(report).encode()
        members["play.html"] = b"<p>synthetic</p>"
        if extra:
            members["untrusted.png"] = b"extra"
        with zipfile.ZipFile(self.preview, "w", zipfile.ZIP_DEFLATED) as zf:
            for name, data in members.items():
                zf.writestr(name, data)

    def check(self, **kwargs):
        return verify_saved_preview(
            self.preview, self.save, self.archive,
            expected_sha=self.sha,
            expected_index_sha=self.index_sha,
            room_offset=0, room_length=len(self.archive),
            expected_frames=4, **kwargs)

    def test_parse_source_cycl_chunks_without_copied_records(self):
        rows = parse_room7_cycles(
            self.archive, expected_sha=self.sha,
            room_offset=0, room_length=len(self.archive))
        self.assertEqual([(r["id"], r["rate_raw"]) for r in rows],
                         [(row[0], row[1]) for row in CYCLES])

    def test_fully_correlated_four_frame_forecast(self):
        first = self.preview.read_bytes()
        saved = self.save.read_bytes()
        result = self.check()
        self.assertEqual(result["status"], "portable_palettes_matched")
        self.assertEqual(result["exact_palette_count"], 4)
        self.assertEqual(result["mismatching_palette_count"], 0)
        self.assertEqual(result["distinct_index_planes"], 1)
        self.assertFalse(result["evidence_boundary"]["actual_raw_engine_buffers_reexamined"])
        self.assertFalse(result["counter_phase_fitting_used"])
        self.assertEqual(self.preview.read_bytes(), first)
        self.assertEqual(self.save.read_bytes(), saved)

    def test_tampered_png_refused_against_report(self):
        self.make_preview(tamper=2)
        with self.assertRaisesRegex(PortableRoom7Error, "PNG palette differs"):
            self.check()

    def test_tampered_report_palette_refused(self):
        self.make_preview(reported_palette_corruption=True)
        with self.assertRaisesRegex(PortableRoom7Error, "PNG palette differs"):
            self.check()

    def test_perturbed_report_timer_produces_visible_mismatch(self):
        self.make_preview(time_mutation=100)
        result = self.check()
        self.assertEqual(result["status"], "portable_palette_mismatch")
        self.assertGreater(result["mismatching_palette_count"], 0)

    def test_unexpected_zip_member_refused(self):
        self.make_preview(extra=True)
        with self.assertRaisesRegex(PortableRoom7Error, "inventory mismatch"):
            self.check()

    def test_wrong_game_archive_hash_refused(self):
        broken = bytearray(self.archive)
        broken[-1] ^= 1
        with self.assertRaisesRegex(PortableRoom7Error, "archive hash mismatch"):
            verify_saved_preview(
                self.preview, self.save, bytes(broken),
                expected_sha=self.sha, expected_index_sha=self.index_sha,
                room_offset=0, room_length=len(self.archive),
                expected_frames=4)

    def test_game_save_room23_refused(self):
        # Construct a syntactically valid gzip-wrapped Room 23 save,
        # not a valid gzip stream followed by malformed trailing bytes.
        self.save.write_bytes(synthetic_scummvm_save(room=23))
        with self.assertRaisesRegex(PortableRoom7Error, "not Room 7"):
            self.check()


if __name__ == "__main__":
    unittest.main()
