"""Keep the original DOS startup contract explicit and separate from ScummVM."""
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]


class OriginalDosBootContractTests(unittest.TestCase):
    def test_dos_boot_sequence_is_part_of_every_dos_executable_test(self):
        text = (ROOT / "docs/research/P4_MI2_ORIGINAL_DOS_BOOT_20261113.md").read_text()
        self.assertIn("every integration or visual fidelity test", text)
        for checkpoint in (
            "copy-protection prompt",
            "difficulty selection",
            "F5",
            "Room 7 engine-verified",
            "DOSBox",
            "fresh, non-overwriting working copy",
            "Room 7",
        ):
            with self.subTest(checkpoint=checkpoint):
                self.assertIn(checkpoint, text)

    def test_dos_saves_are_not_passed_to_scummvm_launcher(self):
        source = (ROOT / "tools/run_room23_frames.py").read_text()
        scene = (ROOT / "tools/verify_room7_saved_entry.py").read_text()
        self.assertIn('signature != b"SCVM"', source)
        self.assertIn('stream.read(4) != b"SCVM"', scene)
        notes = (ROOT / "docs/research/P4_ROOM7_NORMAL_ENTRY_TEST_20261113.md").read_text()
        self.assertIn("P4_MI2_ORIGINAL_DOS_BOOT_20261113.md", notes)
        self.assertIn("two distinct execution tracks", notes)


if __name__ == "__main__":
    unittest.main()
