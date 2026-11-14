"""Public, synthetic-only guards for Room 7 actor-11 instrumentation."""
from pathlib import Path
import tempfile
import unittest

from tools.instrument_room7_actor11 import (
    ANCHOR, CAMERA_GUARD, WALK_GUARD, install, instrument
)


SAMPLE = "\n".join((CAMERA_GUARD, WALK_GUARD, ANCHOR)) + "\n"


class Room7Actor11PatcherTests(unittest.TestCase):
    def test_single_snapshot_insertion_preserves_old_trace_lines(self):
        changed = instrument(SAMPLE)
        self.assertIn("costume11 %d %d %d %d %d", changed)
        self.assertEqual(changed.count(ANCHOR), 1)
        self.assertIn(WALK_GUARD, changed)
        self.assertIn(CAMERA_GUARD, changed)
        with self.assertRaisesRegex(ValueError, "already present"):
            instrument(changed)

    def test_rejects_unknown_or_incomplete_instrumentation(self):
        for text in ("", ANCHOR, WALK_GUARD + ANCHOR, SAMPLE + ANCHOR):
            with self.subTest(text=text[:20]), self.assertRaises(ValueError):
                instrument(text)

    def test_patch_requires_independent_exact_source_copy(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            original = root / "old" / "engines" / "scumm"
            updated = root / "new" / "engines" / "scumm"
            original.mkdir(parents=True)
            updated.mkdir(parents=True)
            src = original / "scumm.cpp"
            dst = updated / "scumm.cpp"
            src.write_text(SAMPLE, encoding="utf-8")
            dst.write_text(SAMPLE, encoding="utf-8")
            install(root / "old", root / "new")
            self.assertEqual(src.read_text(encoding="utf-8"), SAMPLE)
            self.assertIn("costume11", dst.read_text(encoding="utf-8"))
            with self.assertRaises(ValueError):
                install(root / "old", root / "new")


if __name__ == "__main__":
    unittest.main()
