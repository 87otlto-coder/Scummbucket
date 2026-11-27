"""Synthetic-only adapter tests; real BigR is opt-in via BIGR_TEST_CLI."""
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

from scummbucket import bigr_export as be

try:
    from PIL import Image
except ImportError:
    Image = None


def capabilities():
    return {"ok": True, "contract": be.CONTRACT, "appVersion": "test",
            "packageSchema": be.SCHEMA, "commands": ["capabilities", "validate", "render"],
            "render": {"supportedKinds": ["raster"], "inputPixelFormats": ["rgba8"],
                       "outputFormats": ["png"], "scalingMethods": ["nearest"],
                       "scale": "uniform positive integer (default 1)",
                       "maxOutputPixels": 4_000_000}}


@unittest.skipIf(Image is None, "Pillow optional dependency absent")
class AdapterTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.png = self.root / "source.png"
        self.rgba = bytes([255, 1, 2, 255, 3, 254, 4, 0,
                           5, 6, 253, 64, 7, 8, 9, 128,
                           11, 12, 13, 1, 14, 15, 16, 254])
        Image.frombytes("RGBA", (3, 2), self.rgba).save(self.png)
        self.source = self.png.read_bytes()

    def fake(self, code):
        script = self.root / "fake.py"
        script.write_text(code, encoding="utf-8")
        return be.BigR(script, sys.executable)

    def test_package_bytes_and_nonoverwrite(self):
        raster = be.load_raster(self.png)
        path = self.root / "package"
        h = be.make_package(raster, "synthetic", path)
        m = json.loads((path / "manifest.json").read_bytes())
        self.assertEqual(h, be.digest((path / "manifest.json").read_bytes()))
        self.assertEqual(m["schema"], be.SCHEMA)
        self.assertEqual(m["raster"], {"width": 3, "height": 2, "format": "rgba8", "pixels": be.PIXELS})
        self.assertEqual((path / be.PIXELS).read_bytes(), self.rgba)
        self.assertEqual(m["payloads"][be.PIXELS], {"byteLength": 24, "sha256": be.digest(self.rgba)})
        with self.assertRaises(FileExistsError):
            be.make_package(raster, "synthetic", path)
        self.assertEqual(self.png.read_bytes(), self.source)

    def test_real_process_capability_envelope(self):
        backend = self.fake("print(" + repr(json.dumps(capabilities())) + ")")
        self.assertEqual(backend.capabilities()["packageSchema"], be.SCHEMA)

    def test_invalid_response_and_incompatible_capabilities(self):
        with self.assertRaisesRegex(be.BackendError, "Expecting value"):
            self.fake("print('not json')").capabilities()
        bad = capabilities()
        bad["packageSchema"] = "other"
        with self.assertRaises(be.BackendError) as cm:
            self.fake("print(" + repr(json.dumps(bad)) + ")").capabilities()
        self.assertEqual(cm.exception.code, "INCOMPATIBLE")
        bad = capabilities()
        bad["render"]["outputFormats"] = []
        with self.assertRaises(be.BackendError):
            self.fake("print(" + repr(json.dumps(bad)) + ")").capabilities()

    def test_structured_process_failure(self):
        error = {"ok": False, "contract": be.CONTRACT,
                 "error": {"code": "INVALID_PACKAGE", "message": "bad digest"}}
        backend = self.fake("import sys\nprint(" + repr(json.dumps(error)) +
                            ", file=sys.stderr)\nsys.exit(4)")
        with self.assertRaises(be.BackendError) as cm:
            backend.run("validate")
        self.assertEqual(cm.exception.code, "INVALID_PACKAGE")
        self.assertEqual(cm.exception.diagnostic, error)

    def test_absent_and_explicit_fallback(self):
        absent = self.root / "missing.mjs"
        out = self.root / "output"
        with self.assertRaises(be.BackendError) as cm:
            be.export(self.png, out, asset_id="synthetic", cli=absent)
        self.assertEqual(cm.exception.code, "UNAVAILABLE")
        self.assertFalse(out.exists())
        result = be.export(self.png, out, asset_id="synthetic", scale=4,
                           cli=absent, fallback_native=True)
        self.assertEqual(result["status"], "fallback-native")
        self.assertEqual(result["actualScale"], 1)
        self.assertEqual(result["requestedScale"], 4)
        self.assertEqual((out / "image.png").read_bytes(), self.source)
        self.assertFalse((out / "result.json").exists())
        with self.assertRaises(FileExistsError):
            be.export(self.png, out, asset_id="synthetic", cli=absent, fallback_native=True)
        self.assertEqual(self.png.read_bytes(), self.source)

    def test_incompatible_rejected_and_limit_fallback(self):
        for code in ("INCOMPATIBLE", "INVALID_PACKAGE", "INTERNAL_ERROR"):
            out = self.root / code
            with patch.object(be.BigR, "__init__", return_value=None), \
                 patch.object(be.BigR, "capabilities", side_effect=be.BackendError(code, "test")):
                r = be.export(self.png, out, asset_id="synthetic", fallback_native=True)
            self.assertEqual(r["error"]["code"], code)
        with patch.object(be.BigR, "__init__", return_value=None), \
             patch.object(be.BigR, "capabilities", return_value=capabilities()):
            with self.assertRaises(be.BackendError) as cm:
                be.export(self.png, self.root / "too-large", asset_id="synthetic", scale=1000)
        self.assertEqual(cm.exception.code, "UNSUPPORTED_FEATURE")

    def test_indexed_requires_verified_room7_manifest(self):
        p = self.root / "frame-0001.png"
        im = Image.frombytes("P", (320, 144), bytes([0, 1]) * (320 * 144 // 2))
        palette = bytes([10, 20, 30, 40, 50, 60] + [0] * 762)
        im.putpalette(palette)
        im.save(p)
        with self.assertRaises(ValueError):
            be.load_raster(p)
        m = {"schema": "room7-navigation-native-export/1", "room_id": 7,
             "edition": "Monkey Island 2, original DOS VGA", "geometry": [320, 144],
             "all_indexed_comparisons_exact": True,
             "palette_source": "engine-observed post-presentation palette; not independently forecast here",
             "segments": [{"frames": [{"file": p.name, "frame": 1,
                                        "png_sha256": be.digest(p.read_bytes()),
                                        "indexed_sha256": be.digest(im.tobytes()),
                                        "palette_sha256": be.digest(palette)}]}]}
        manifest = self.root / "animation.json"
        manifest.write_text(json.dumps(m), encoding="utf-8")
        raster = be.load_raster(p, manifest)
        self.assertEqual(raster.rgba[:8], bytes([10, 20, 30, 255, 40, 50, 60, 255]))
        m["segments"][0]["frames"][0]["palette_sha256"] = "0" * 64
        manifest.write_text(json.dumps(m), encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "hashes"):
            be.load_raster(p, manifest)

    def test_output_verifier_rejects_false_success(self):
        raster = be.load_raster(self.png)
        folder = self.root / "bad"
        folder.mkdir()
        Image.new("RGBA", (3, 2), (0, 0, 0, 0)).save(folder / "image.png")
        report = {"ok": True, "contract": be.CONTRACT, "status": "complete",
                  "source": {"assetId": "test", "packageSchema": be.SCHEMA, "manifestSha256": "hash"},
                  "output": {"path": "image.png", "format": "png", "pixelFormat": "rgba8",
                             "width": 3, "height": 2, "sha256": be.digest((folder / "image.png").read_bytes())},
                  "rendering": {"method": "nearest", "scaleX": 1, "scaleY": 1},
                  "warnings": [], "encoder": {}}
        (folder / "result.json").write_text(json.dumps(report), encoding="utf-8")
        with self.assertRaisesRegex(be.BackendError, "pixels differ"):
            be.verify_output(folder, report, raster, 1, "test", "hash")

    @unittest.skipUnless(os.environ.get("BIGR_TEST_CLI"), "Set BIGR_TEST_CLI for real sidecar")
    def test_real_bigr_native_and_uniform_4x(self):
        import base64
        for scale in (1, 4):
            out = self.root / f"bigr-{scale}"
            result = be.export(self.png, out, asset_id="synthetic", scale=scale,
                               cli=os.environ["BIGR_TEST_CLI"])
            self.assertEqual(result["status"], "complete")
            self.assertEqual(result["verification"]["pixelMismatches"], 0)
            with Image.open(out / "image.png") as im:
                self.assertEqual(im.size, (3 * scale, 2 * scale))
                actual = im.tobytes()
            # Independent explicit coordinate mapping, including RGB behind alpha zero.
            expected = b"".join(self.rgba[4 * ((y // scale) * 3 + x // scale):
                                          4 * ((y // scale) * 3 + x // scale + 1)]
                                for y in range(2 * scale) for x in range(3 * scale))
            self.assertEqual(actual, expected)
            self.assertEqual(self.png.read_bytes(), self.source)
            self.assertEqual((out / "package" / be.PIXELS).read_bytes(), self.rgba)
            print("SYNTHETIC BIGR PROOF", scale, json.dumps(result["verification"]),
                  (out / "result.json").read_text(encoding="utf-8"))
            # Tiny, original synthetic raster only; not a game asset or artifact upload.
            print("SYNTHETIC PNG BASE64", scale, base64.b64encode((out / "image.png").read_bytes()).decode())


if __name__ == "__main__":
    unittest.main()
