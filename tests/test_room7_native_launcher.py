"""Fixture-free safety tests for the isolated native Room 7 save launcher."""
from pathlib import Path
from types import SimpleNamespace
import tempfile
import unittest

from tools.run_room23_frames import validate_native_room7_save


class NativeRoom7LauncherTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.game = self.root / "FIXTURE/GAMES/MonkeyIsland2_DOS_VGA"
        self.game.mkdir(parents=True)
        self.exe = self.root / "TOOLS/ScummVM-P4-Room7/scummvm.exe"
        self.exe.parent.mkdir(parents=True)
        self.exe.write_bytes(b"synthetic executable")
        self.save = self.root / "FIXTURE/CAPTURES/saved-game.s01"
        self.save.parent.mkdir(parents=True, exist_ok=True)
        self.save.write_bytes(b"SCVM synthetic private save")
        self.output = self.root / "FIXTURE/CAPTURES/Room7/native-NEW"
        self.args = SimpleNamespace(
            room=7, save=self.save, enter_room=False, walk=None,
            native_room7_save=True,
        )

    def check(self):
        validate_native_room7_save(self.args, self.exe, self.game, self.output)

    def test_clean_native_saved_room7_capture_is_admitted(self):
        self.check()
        self.assertFalse(self.output.exists(), "preflight must be read-only")
        self.assertEqual(self.save.read_bytes(), b"SCVM synthetic private save")

    def test_debugger_jump_and_injected_walk_are_refused(self):
        for name, value in (("enter_room", True), ("walk", "normal"),
                            ("room", 23), ("save", None)):
            with self.subTest(option=name):
                previous = getattr(self.args, name)
                setattr(self.args, name, value)
                try:
                    with self.assertRaisesRegex(ValueError, "requires --room 7"):
                        self.check()
                finally:
                    setattr(self.args, name, previous)

    def test_missing_or_empty_save_is_refused(self):
        self.save.write_bytes(b"")
        with self.assertRaisesRegex(ValueError, "nonempty"):
            self.check()
        self.save.unlink()
        with self.assertRaisesRegex(ValueError, "nonempty"):
            self.check()

    def test_dos_save_is_rejected_before_any_output(self):
        self.save.write_bytes(b"123" + bytes(37) + b"synthetic DOS state")
        with self.assertRaisesRegex(ValueError, "not an original DOS SAVEGAME"):
            self.check()
        self.assertFalse(self.output.exists())

    def test_executable_must_exist_outside_source(self):
        self.exe.unlink()
        with self.assertRaisesRegex(ValueError, "TOOLS executable"):
            self.check()
        other = self.root / "SOURCE/ScummBucket/scummvm.exe"
        other.parent.mkdir(parents=True)
        other.write_bytes(b"synthetic executable")
        with self.assertRaisesRegex(ValueError, "TOOLS executable"):
            validate_native_room7_save(self.args, other, self.game, self.output)

    def test_outputs_must_stay_in_private_fixture(self):
        wrong = self.root / "SOURCE/ScummBucket/outputs/new"
        with self.assertRaisesRegex(ValueError, "FIXTURE/CAPTURES/Room7"):
            validate_native_room7_save(self.args, self.exe, self.game, wrong)
        other = self.root / "OUTPUT/Room7/native"
        with self.assertRaisesRegex(ValueError, "FIXTURE/CAPTURES/Room7"):
            validate_native_room7_save(self.args, self.exe, self.game, other)

    def test_game_must_be_in_fixture_games(self):
        wrong = self.root / "SOURCE/GAMES/MonkeyIsland2_DOS_VGA"
        with self.assertRaisesRegex(ValueError, "FIXTURE/GAMES"):
            validate_native_room7_save(self.args, self.exe, wrong, self.output)
        other = self.root / "FIXTURE/OTHER/MonkeyIsland2_DOS_VGA"
        with self.assertRaisesRegex(ValueError, "FIXTURE/GAMES"):
            validate_native_room7_save(self.args, self.exe, other, self.output)
        mislabeled = self.root / "FIXTURE/GAMES/MonkeyIsland2_unknown"
        with self.assertRaisesRegex(ValueError, "FIXTURE/GAMES"):
            validate_native_room7_save(self.args, self.exe, mislabeled, self.output)

    def test_original_save_must_not_reside_inside_git_source(self):
        source_save = self.root / "SOURCE/ScummBucket/example.s01"
        source_save.parent.mkdir(parents=True)
        source_save.write_bytes(b"SCVM synthetic private save")
        self.args.save = source_save
        with self.assertRaisesRegex(ValueError, "cannot reside inside SOURCE"):
            self.check()

    def test_default_legacy_launcher_is_unchanged(self):
        self.args.native_room7_save = False
        self.args.save = None
        self.args.room = 23
        self.args.enter_room = True
        validate_native_room7_save(self.args, self.exe, self.game, self.output)


if __name__ == "__main__":
    unittest.main()
