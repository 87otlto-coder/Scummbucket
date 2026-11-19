import os
from pathlib import Path
import unittest
from unittest.mock import patch

from tools.compare_room24_capture import compare
from tools.room24_probe_log import replay_rng
from tools.verify_independent_zplanes import ArchiveDepth


ENTRY = "SB24 entry room=24 resource=24\n"


class Room24RngReplayTests(unittest.TestCase):
    def test_repeated_candidates_retain_state_until_acceptance(self):
        log = ENTRY + (
            "SB24 RNG max=2 result=2 previous=3\n"
            "SB24 RNG max=2 result=2 previous=3\n"
            "SB24 RNG max=2 result=0 previous=3\n"
            "SB24 RNG max=2 result=0 previous=1\n"
            "SB24 RNG max=2 result=1 previous=1\n"
        )
        batches = replay_rng(log, initial_state=3)
        self.assertEqual([[r["accepted"] for r in b] for b in batches],
                         [[False, False, True], [False, True]])
        self.assertEqual([[r["previous"] for r in b] for b in batches],
                         [[3, 3, 3], [1, 1]])
        self.assertEqual([b[-1]["candidate"] for b in batches], [1, 2])

    def test_observed_previous_cannot_override_maintained_state(self):
        log = ENTRY + (
            "SB24 RNG max=2 result=0 previous=3\n"
            "SB24 RNG max=2 result=0 previous=2\n"
        )
        with self.assertRaisesRegex(ValueError, "continuity mismatch"):
            replay_rng(log, initial_state=3)

    def test_missing_entry_or_calls_fail_closed(self):
        for log in ("", ENTRY, ENTRY * 2):
            with self.subTest(log=log), self.assertRaises(ValueError):
                replay_rng(log, initial_state=3)

    @unittest.skipUnless(os.getenv("SCUMMBUCKET_ROOM24_GAME") and
                         os.getenv("SCUMMBUCKET_ROOM24_CAPTURE"), "private Room 24 fixtures")
    def test_modified_references_change_diagnostics_only(self):
        game = Path(os.environ["SCUMMBUCKET_ROOM24_GAME"])
        capture = Path(os.environ["SCUMMBUCKET_ROOM24_CAPTURE"])
        original_read = Path.read_bytes

        def change_reference(path):
            raw = original_read(path)
            if path != capture / "engine-001.bin":
                return raw
            header, separator, payload = raw.partition(b"\nDATA\n")
            rows = header.split(b"\n")
            indices = [i for i, row in enumerate(rows) if row.startswith(b"object ")]
            changed = [b"object 246 0" if rows[i].startswith(b"object 246 ") else rows[i]
                       for i in reversed(indices)]
            for i, row in zip(indices, changed):
                rows[i] = row
            data = bytearray(payload)
            data[49152] ^= 1  # First reference front pixel.
            data[95232 + 5760] ^= 128  # First reference ZP01 bit.
            return b"\n".join(rows) + separator + data

        normal_depth = ArchiveDepth(game, 24)
        normal = compare(game, capture, zplanes=normal_depth, entry_script_local=3)
        altered_depth = ArchiveDepth(game, 24)
        with patch.object(Path, "read_bytes", change_reference), patch.object(
                ArchiveDepth, "predict", side_effect=AssertionError("snapshot path used")):
            altered = compare(game, capture, zplanes=altered_depth, entry_script_local=3)
        self.assertEqual(normal["events"], altered["events"])
        for first, second in zip(normal["frames"], altered["frames"], strict=True):
            for buffer in ("back", "front"):
                self.assertEqual(first[buffer]["indices"]["actual_sha256"],
                                 second[buffer]["indices"]["actual_sha256"])
        self.assertFalse(altered["frames"][0]["object_state_matches"])
        self.assertEqual(altered["frames"][0]["front"]["indices"]["mismatches"], 1)
        self.assertEqual(altered_depth.frames[0]["masks"][1]["bits_mismatched"], 1)
