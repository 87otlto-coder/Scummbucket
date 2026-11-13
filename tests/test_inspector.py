"""Self-contained tests: synthetic fixtures only, no proprietary game data."""
import struct
import tempfile
import unittest
from pathlib import Path
import zipfile

from scummbucket.inspector import chunks, inspect, InspectionError
from scummbucket.cli import main


def chunk(tag: str, payload: bytes) -> bytes:
    return tag.encode("ascii") + struct.pack(">I", len(payload) + 8) + payload


def encoded(data: bytes) -> bytes:
    return bytes(x ^ 0x69 for x in data)


def index() -> bytes:
    # Room slot 0 is unused; room 1 lives in file number 1 with offset 0.
    # Other resource directories are empty in this deliberately tiny fixture.
    room_dir = chunk("DROO", struct.pack("<H", 2) + b"\x00\x01" + struct.pack("<II", 0, 0))
    directories = room_dir + b"".join(
        chunk(t, struct.pack("<H", 1) + b"\x00" + struct.pack("<I", 0))
        for t in ("DSCR", "DSOU", "DCOS", "DCHR"))
    return b"".join([chunk("RNAM", b""), chunk("MAXS", b""), directories,
                     chunk("DOBJ", struct.pack("<H", 1) + b"\x00" * 5)])


def resource(*, room_id=1, target=None, bad_length=False, broken_cycle=False,
             extra_room=False, duplicate_loff=False, multiple_states=False) -> bytes:
    cycled = b"\x01\x00\x00\x01\x2c\x00\x02\x0a\x0b"
    if not broken_cycle:
        cycled += b"\x00\x00"  # zero terminator, optional alignment
    # Synthetic v5 IMHD/CDHD headers with the SAME explicit object ID.
    object_id = 99
    count = 2 if multiple_states else 1
    obim = chunk("OBIM", chunk("IMHD", struct.pack("<HH", object_id, count) + b"\x00" * 12)
                 + chunk("IM01", b"y") +
                 (chunk("IM02", b"z") if multiple_states else b""))
    obcd = chunk("OBCD", chunk("CDHD", struct.pack("<H", object_id) + b"\x00" * 11))
    inner = chunk("ROOM", chunk("RMHD", b"\x00") + chunk("CYCL", cycled) + obim + obcd)
    lf = chunk("LFLF", inner)
    # LECF header (8), LOFF (14), LFLF header (8): ROOM begins at offset 30.
    pointer = 30 if target is None else target
    loc = bytes([room_id]) + struct.pack("<I", pointer)
    if duplicate_loff:
        loc += bytes([room_id]) + struct.pack("<I", pointer)
    loff = chunk("LOFF", bytes([2 if duplicate_loff else 1]) + loc)
    if bad_length:
        lf = b"LFLF" + struct.pack(">I", 0xFFFFFFFF) + inner
    return chunk("LECF", loff + lf + (lf if extra_room else b""))


def make_zip(path: Path, *, a: bytes | None = None, b: bytes | None = None,
             names=("mi2/MONKEY2.000", "mi2/MONKEY2.001")) -> None:
    with zipfile.ZipFile(path, "w", compression=zipfile.ZIP_DEFLATED) as z:
        if a is not None:
            z.writestr(names[0], encoded(a))
        if b is not None:
            z.writestr(names[1], encoded(b))


class InspectorTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.zip_path = self.root / "sample.zip"

    def diagnostic(self, report):
        self.assertEqual(report["status"], "failed", report)
        return [x["code"] for x in report["diagnostics"]]

    def test_synthetic_zip_valid(self):
        make_zip(self.zip_path, a=index(), b=resource(multiple_states=True))
        report = inspect(self.zip_path)
        self.assertEqual(report["status"], "success", report["diagnostics"])
        self.assertEqual(report["resources"]["room_count"], 1)
        self.assertEqual(report["resources"]["cycle_count"], 1)
        self.assertEqual(report["resources"]["multistate_object_images"], 1)
        self.assertEqual(report["scene_inventory"]["summary"]["paired_objects"], 1)
        self.assertEqual(report["scene_inventory"]["summary"]["multistate_object_candidates"], 1)
        self.assertEqual(report["scene_inventory"]["rooms"][0]["objects"][0]["object_id"], 99)
        self.assertFalse(report["scene_inventory"]["rooms"][0]["objects"][0]["animation_observed"])
        self.assertEqual(report["index"]["DROO"]["slots"], 2)
        self.assertEqual(report["directory_links"]["summary"],
                         {"linked": 1, "unused": 5, "failed": 0})
        self.assertEqual(report["resources"]["resource_counts"]["OBIM"], 1)
        self.assertEqual(report["diagnostic_counts"].get("error", 0), 0)
        self.assertNotIn("CYCLE_TRAILING_BYTES", [x["code"] for x in report["diagnostics"]])

    def test_directory_and_single_file_entrypoints(self):
        (self.root / "MONKEY2.000").write_bytes(encoded(index()))
        (self.root / "MONKEY2.001").write_bytes(encoded(resource()))
        self.assertEqual(inspect(self.root)["status"], "success")
        self.assertEqual(inspect(self.root / "MONKEY2.000")["status"], "success")

    def test_non_scumm_archive_is_explicit(self):
        with zipfile.ZipFile(self.zip_path, "w") as z:
            z.writestr("MK1.EXE", b"not scumm")
        self.assertIn("GAME_PAIR_NOT_FOUND", self.diagnostic(inspect(self.zip_path)))

    def test_missing_counterpart(self):
        make_zip(self.zip_path, a=index())
        self.assertIn("GAME_PAIR_NOT_FOUND", self.diagnostic(inspect(self.zip_path)))

    def test_bad_signature(self):
        make_zip(self.zip_path, a=b"GARBAGE!", b=resource())
        self.assertIn("GAME_SIGNATURE_UNSUPPORTED", self.diagnostic(inspect(self.zip_path)))

    def test_bad_chunk_length(self):
        make_zip(self.zip_path, a=index(), b=resource(bad_length=True))
        self.assertIn("CHUNK_OUT_OF_BOUNDS", self.diagnostic(inspect(self.zip_path)))

    def test_duplicate_loff(self):
        make_zip(self.zip_path, a=index(), b=resource(duplicate_loff=True))
        self.assertIn("LOFF_ROOM_DUPLICATE", self.diagnostic(inspect(self.zip_path)))

    def test_invalid_loff_target(self):
        make_zip(self.zip_path, a=index(), b=resource(target=1234))
        self.assertIn("LOFF_TARGET_INVALID", self.diagnostic(inspect(self.zip_path)))

    def test_truncated_cycle(self):
        make_zip(self.zip_path, a=index(), b=resource(broken_cycle=True))
        self.assertIn("CYCLE_TERMINATOR_MISSING", self.diagnostic(inspect(self.zip_path)))

    def test_bad_index_directory_count(self):
        bad = index().replace(b"DROO\x00\x00\x00\x14\x02\x00", b"DROO\x00\x00\x00\x14\x03\x00")
        make_zip(self.zip_path, a=bad, b=resource())
        self.assertIn("DIRECTORY_LENGTH_INVALID", self.diagnostic(inspect(self.zip_path)))

    def test_directory_link_mismatch_is_partial_and_visible(self):
        malformed = bytearray(index())
        # DROO: chunk header 8, count 2, room number for slot 1 at +11.
        malformed[malformed.index(b"DROO") + 11] = 2
        make_zip(self.zip_path, a=bytes(malformed), b=resource())
        report = inspect(self.zip_path)
        self.assertEqual(report["status"], "partial")
        self.assertEqual(report["directory_links"]["summary"]["failed"], 1)
        self.assertIn("ROOM_DIRECTORY_UNSUPPORTED", [d["code"] for d in report["diagnostics"]])

    def test_raw_chunk_length_less_than_header(self):
        with self.assertRaises(InspectionError) as c:
            chunks(b"FOOB\x00\x00\x00\x07", 0, 8, "synthetic")
        self.assertEqual(c.exception.code, "CHUNK_LENGTH_INVALID")

    def test_invalid_zip_explicit(self):
        self.zip_path.write_bytes(b"not a zip")
        self.assertIn("ZIP_INVALID", self.diagnostic(inspect(self.zip_path)))

    def test_extra_unindexed_room(self):
        make_zip(self.zip_path, a=index(), b=resource(extra_room=True))
        self.assertIn("LOFF_BUNDLE_COUNT_MISMATCH", self.diagnostic(inspect(self.zip_path)))

    def test_output_does_not_overwrite_existing(self):
        make_zip(self.zip_path, a=index(), b=resource())
        reportfile = self.root / "existing.json"
        reportfile.write_text("DO NOT REPLACE")
        self.assertEqual(main(["inspect", str(self.zip_path), "--output", str(reportfile)]), 2)
        self.assertEqual(reportfile.read_text(), "DO NOT REPLACE")

    def test_cannot_open_missing_file(self):
        self.assertIn("INPUT_NOT_FOUND", self.diagnostic(inspect(self.root / "missing.zip")))


if __name__ == "__main__":
    unittest.main()
