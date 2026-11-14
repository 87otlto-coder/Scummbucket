"""Synthetic indexed-PNG contract tests for Room 7 navigation export verification."""
from hashlib import sha256
import json
from pathlib import Path
import tempfile
import unittest

from PIL import Image

from scummbucket.room7_navigation_export import make_manifest, render_player
from tools.verify_room7_navigation_export import verify_export


def digest(data):
    return sha256(data).hexdigest()


class NativeRoom7IntegrityTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.folder = Path(self.temp.name)
        rows, records = [], []
        palette = [(x * 7) % 256 for x in range(768)]
        for seq, (tick, ms) in enumerate(((960, 100), (961, 200),
                                          (1113, 15300)), 1):
            name = f"frame-{seq:04d}.png"
            img = Image.new("P", (320, 144), seq)
            img.putpalette(palette)
            path = self.folder / name
            img.save(path)
            rows.append(dict(
                frame=seq, tick=tick, present_ms=ms,
                comparison=dict(masked_errors=0),
            ))
            records.append(dict(
                frame=seq, file=name, present_ms=ms,
                indexed_sha256=digest(img.tobytes()),
                palette_sha256=digest(bytes(palette)),
                png_sha256=digest(path.read_bytes()),
            ))
        self.manifest = make_manifest(
            rows, records, archive_hashes={"MONKEY2.000": "0" * 64},
            capture="synthetic_only")
        (self.folder / "animation.json").write_text(json.dumps(self.manifest))
        (self.folder / "play.html").write_text(render_player(self.manifest))

    def test_synthetic_export_verified(self):
        result = verify_export(self.folder)
        self.assertEqual(result["status"], "native_png_integrity_verified")
        self.assertEqual(result["indexed_pngs_verified"], 3)
        self.assertEqual(len(result["segments"]), 2)
        self.assertEqual(result["segments"][1]["omitted_ticks_before"], 151)

    def test_rejects_png_mutation(self):
        image = Image.new("P", (320,144), 250)
        image.save(self.folder / "frame-0002.png")
        with self.assertRaisesRegex(ValueError, "Encoded PNG SHA-256 mismatch"):
            verify_export(self.folder)

    def test_rejects_manifest_pixel_digest_mutation(self):
        self.manifest["segments"][0]["frames"][1]["indexed_sha256"] = "f" * 64
        (self.folder / "animation.json").write_text(json.dumps(self.manifest))
        with self.assertRaisesRegex(ValueError, "Indexed pixels or palette mismatch"):
            verify_export(self.folder)

    def test_rejects_gap_fabrication(self):
        self.manifest["segments"][1]["omitted_ticks_before"] = 0
        (self.folder / "animation.json").write_text(json.dumps(self.manifest))
        with self.assertRaisesRegex(ValueError, "fabricated segment gap"):
            verify_export(self.folder)

    def test_rejects_missing_and_extra_png(self):
        (self.folder / "frame-0003.png").unlink()
        with self.assertRaises(FileNotFoundError):
            verify_export(self.folder)

    def test_rejects_undeclared_extra_png(self):
        Image.new("P",(320,144),0).save(self.folder / "frame-0004.png")
        with self.assertRaisesRegex(ValueError, "PNG inventory"):
            verify_export(self.folder)

    def test_rejects_wrong_dimensions_even_with_matching_encoded_hash(self):
        img = Image.new("P", (12, 12), 1)
        img.putpalette([(x * 7) % 256 for x in range(768)])
        path = self.folder / "frame-0002.png"
        img.save(path)
        self.manifest["segments"][0]["frames"][1]["png_sha256"] = digest(path.read_bytes())
        (self.folder / "animation.json").write_text(json.dumps(self.manifest))
        with self.assertRaisesRegex(ValueError, "geometry/mode"):
            verify_export(self.folder)


if __name__ == "__main__":
    unittest.main()
