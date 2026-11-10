"""Synthetic regression tests for portable Room 7 HTML packaging.

No copyrighted fixture content or ScummVM runtime is needed.
"""
import hashlib
import json
from pathlib import Path
import tempfile
import unittest

from PIL import Image

from scummbucket.room23_export import PLAYER
from scummbucket.standalone_preview import render_standalone_preview
from tools.package_room7_preview import package_existing


class Room7StandalonePreviewTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.folder = Path(self.tmp.name)
        self.rows = []
        for i in (1, 2):
            img = Image.new("P", (320, 144), i)
            img.putpalette([v % 256 for v in range(768)])
            name = f"frame-{i:03}.png"
            img.save(self.folder / name)
            self.rows.append({
                "frame": i, "file": name, "time_ms": 1000 + i * 101,
                "indexed_sha256": hashlib.sha256(img.tobytes()).hexdigest(),
                "mismatches": 0,
            })

    def test_portable_player_contains_images_and_timing(self):
        html = render_standalone_preview(self.folder, self.rows, PLAYER)
        self.assertEqual(html.count("data:image/png;base64,"), 2)
        self.assertIn("Room 7 reconstruction", html)
        self.assertIn(",101]", html)
        self.assertNotIn("frame-001.png", html)
        self.assertNotIn("TIMELINE", html)

    def test_missing_frame_raises_instead_of_inert_player(self):
        (self.folder / "frame-002.png").unlink()
        with self.assertRaisesRegex(ValueError, "Missing PNG frame"):
            render_standalone_preview(self.folder, self.rows, PLAYER)

    def test_tampered_frame_raises(self):
        img = Image.new("P", (320, 144), 99)
        img.save(self.folder / "frame-002.png")
        with self.assertRaisesRegex(ValueError, "SHA-256 mismatch"):
            render_standalone_preview(self.folder, self.rows, PLAYER)

    def test_rejects_bad_geometry_and_unsafe_filename(self):
        Image.new("P", (12, 12), 0).save(self.folder / "frame-001.png")
        with self.assertRaisesRegex(ValueError, "geometry"):
            render_standalone_preview(self.folder, self.rows, PLAYER)
        self.rows[0]["file"] = "../frame-001.png"
        with self.assertRaisesRegex(ValueError, "Unsafe"):
            render_standalone_preview(self.folder, self.rows, PLAYER)

    def test_rejects_reversed_timestamps(self):
        self.rows[1]["time_ms"] = 10
        with self.assertRaisesRegex(ValueError, "timestamp"):
            render_standalone_preview(self.folder, self.rows, PLAYER)

    def test_packager_creates_new_standalone_without_overwriting(self):
        base = self.rows[0]
        raw = (self.folder / base["file"]).read_bytes()
        for i in range(3, 88):
            name = f"frame-{i:03}.png"
            (self.folder / name).write_bytes(raw)
            self.rows.append({
                "frame": i, "file": name, "time_ms": 1000 + i * 101,
                "indexed_sha256": base["indexed_sha256"], "mismatches": 0,
            })
        manifest = self.folder / "manifest.json"
        manifest.write_text(json.dumps({"frames": self.rows}), encoding="utf-8")
        old_preview = self.folder / "preview.html"
        old_preview.write_text("existing original", encoding="utf-8")
        output = package_existing(self.folder)
        self.assertEqual(output.name, "preview-standalone.html")
        self.assertEqual(output.read_text(encoding="utf-8").count("data:image/png;base64,"), 87)
        self.assertEqual(old_preview.read_text(encoding="utf-8"), "existing original")
        with self.assertRaises(FileExistsError):
            package_existing(self.folder)

    def test_packager_rejects_incomplete_or_unverified_report(self):
        (self.folder / "manifest.json").write_text(json.dumps({"frames": self.rows}), encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "87 verified"):
            package_existing(self.folder)


if __name__ == "__main__":
    unittest.main()
