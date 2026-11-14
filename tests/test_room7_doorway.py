import tempfile
import unittest
from pathlib import Path

from tools.room7_doorway import finish, read_ticks


def record(tick, room, draw=""):
    return "\t".join(map(str, (tick, room, room, 10, 20, 2, 160, 100, 0, 0, 150, 150, draw)))


class DoorwayTests(unittest.TestCase):
    def test_round_trip_preserves_unsampled_planes(self):
        draw = "draw " + " ".join(map(str, [10, 20, 1] + [0] * 20))
        ticks = read_ticks([record(4, 7, draw), record(5, 12), record(6, 7)])
        self.assertEqual(ticks[4]["draw_plane"], 1)
        self.assertIsNone(ticks[5]["draw_plane"])

    def test_missing_tick_or_return_is_rejected(self):
        for sequence in [[(1, 7), (3, 12), (4, 7)], [(1, 7), (2, 12)], [(1, 7)]]:
            with self.subTest(sequence=sequence), self.assertRaises(ValueError):
                read_ticks(record(tick, room) for tick, room in sequence)

    def test_presentation_clock_must_match_binary(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp)
            (p / "ticks.tsv").write_text("\n".join(record(i, r) for i, r in enumerate((7, 12, 7), 1)))
            (p / "presents.tsv").write_text("1\t1\t100\n")
            (p / "present-001.bin").write_bytes(b"R23D1 1 101 1 1 sdl\nabc")
            with self.assertRaisesRegex(ValueError, "timestamp mismatch"):
                finish(p, p, p / "report")
