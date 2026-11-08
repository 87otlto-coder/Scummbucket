"""Optional private Room 23 source-backed event-GIF regression.

Never ships original game files or derived images to the repository. With no
SCUMMBUCKET_ROOM23_EVENT_BUNDLE environment variable, public CI skips the test.
The hashes below anchor a SYNTHETIC event replay, NOT observed engine timing.
"""
from __future__ import annotations

from hashlib import sha256
from importlib.util import find_spec
import os
from pathlib import Path
import tempfile
import unittest

from scummbucket.palette_bundle_render import read_palette_event_bundle
from scummbucket.palette_event_gif import export_palette_event_gif

BUNDLE = os.environ.get("SCUMMBUCKET_ROOM23_EVENT_BUNDLE")
PIL_AVAILABLE = find_spec("PIL") is not None
BUNDLE_SHA256 = "51407c03772450505d3f3a9cf5af37dd3a2109f69b1290b2c3c511058217028c"
RGB_FRAME_SHA256 = (
    "976f73b04aa917b0d53a58bdf8b445263b1855c5a43a22148862701714862cf7",
    "a17fe2e7a3fcec2f521db1bb84628780061abbb20fc47f545e7c68123c67763d",
    "b39cb91bece898d95cb57342cb57846f4f1d536d94c12917c742453d7fecb14f",
    "a85bdda6933890e65cf2109247735e3299499e6c602eebd220c2f02ac46b3dd7",
    "096bd19499e703ac02853ceb06d7d31521227386c95b83421d1fad0dd84c3f9b",
    "a19302583f36411d8eefc47126c26acb854d9dc48fe8ab3bdcc8538f6d4a3b3d",
    "d9d1333fab290295155eed0a3ad7c032f62c4589805994e599639d1704480595",
    "b6f65b9e207d0f6dcc12819f4772f8f83f2b4bd28e573fe2b4c2b520913b3b31",
    "01db7d86cabff7ba7dfbfcdd381c41a60efcd31c9fdd1e045a38118940f24469",
    "497af1ddef3193ceb1fa4a862529502e99567584d8e4db03751adf37a7d4cac5",
    "086b2deb49b8e4c22e99996410e328b935c9e273f973056bce7f4a91addbc6e1",
    "f10f6ee91a340e6fa95910dc84a2f852b1288731c56bf62d643efc490dd2056d",
    "944876cd5de3a26b4b713e7f311be1952474adcf88f6331d482e6bd33018d759",
    "5bd2c6508b7b04f30c07811a32bc630976402fa73aba565a3ffa976b006f3a66",
    "15382cf8980daa7abc5b16195b51ff681e9d597296d0aea03ead2bcd1bd64ffc",
    "0e26a809384e081b8b2b1c85b0a080c71931b7837375fd70b32350c6dc165aa9",
    "5bd2c6508b7b04f30c07811a32bc630976402fa73aba565a3ffa976b006f3a66",
    "944876cd5de3a26b4b713e7f311be1952474adcf88f6331d482e6bd33018d759",
    "f10f6ee91a340e6fa95910dc84a2f852b1288731c56bf62d643efc490dd2056d",
    "4196f4ae73671544c7a4761a65d56e3b0f5ee88cbb17c0277c1153de729c62b8",
)
DURATIONS_MS = (
    580, 120, 180, 290, 10, 220, 350, 20, 10, 320,
    230, 40, 280, 150, 120, 580, 30, 20, 20, 430,
)
EVENT_TICKS = (
    0, 35, 42, 53, 70, 71, 84, 105, 106, 107,
    126, 140, 142, 159, 168, 175, 210, 212, 213, 214,
)


@unittest.skipUnless(bool(BUNDLE), "Private Room 23 event bundle not configured")
@unittest.skipUnless(PIL_AVAILABLE, "Pillow GIF extra not installed")
class PrivateRoom23EventGifTest(unittest.TestCase):
    def test_source_backed_rgb_frames_and_event_durations(self):
        from PIL import Image

        bundle_path = Path(BUNDLE)
        bundle = read_palette_event_bundle(bundle_path)
        self.assertEqual(bundle["room"], 23)
        self.assertEqual((bundle["width"], bundle["height"]), (320, 144))
        self.assertEqual(bundle["counter_rate"], 60)
        self.assertEqual(bundle["duration_seconds"], 4)
        self.assertEqual(len(bundle["events"]), 19)
        self.assertEqual(bundle["manifest_sha256"], BUNDLE_SHA256)
        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp) / "event-preview.gif"
            report = export_palette_event_gif(bundle_path, output)
            self.assertEqual(report["status"], "success", report["diagnostics"])
            self.assertEqual(report["summary"]["gif_frames_written"], 20)
            self.assertEqual(report["summary"]["unique_visual_states"], 17)
            self.assertEqual(report["summary"]["duration_encoded_ms"], 4000)
            self.assertFalse(report["timing"]["real_engine_update_schedule_verified"])
            self.assertEqual(
                report["provenance"]["bundle_manifest_sha256"], BUNDLE_SHA256)
            self.assertEqual(
                tuple(s["start_counter_tick"] for s in report["segments"]),
                EVENT_TICKS)

            with Image.open(output) as decoded:
                self.assertEqual(decoded.size, (320, 144))
                self.assertEqual(decoded.n_frames, 20)
                self.assertNotIn("loop", decoded.info)
                pixels = []
                durations = []
                for frame in range(decoded.n_frames):
                    decoded.seek(frame)
                    pixels.append(decoded.convert("RGB").tobytes())
                    durations.append(decoded.info["duration"])
                self.assertEqual(tuple(durations), DURATIONS_MS)
                self.assertEqual(
                    tuple(sha256(frame).hexdigest() for frame in pixels),
                    RGB_FRAME_SHA256)
                self.assertEqual(len(set(pixels)), 17)
                original_rgb = bytes(
                    component
                    for index in bundle["indices"]
                    for component in bundle["initial_palette"][3*index:3*index+3]
                )
                self.assertEqual(pixels[0], original_rgb)
                changes = {
                    i for i in range(320 * 144)
                    if any(frame[3*i:3*i+3] != original_rgb[3*i:3*i+3]
                           for frame in pixels[1:])
                }
                source_cycle_pixels = {
                    i for i, index in enumerate(bundle["indices"])
                    if 176 <= index <= 191
                }
                self.assertEqual(len(source_cycle_pixels), 480)
                self.assertEqual(changes, source_cycle_pixels)


if __name__ == "__main__":
    unittest.main()
