"""Optional private Room 23 comparison: event-resolved vs six-unit GIF.

Only derived fingerprints are version-controlled. No commercial game bytes,
frame images, or private output files are embedded here. Public CI skips this
unless both private GIF paths are configured in the environment.
"""
from __future__ import annotations

from bisect import bisect_right
from hashlib import sha256
from importlib.util import find_spec
import json
import os
from pathlib import Path
import unittest

EVENT_GIF = os.environ.get("SCUMMBUCKET_ROOM23_EVENT_GIF")
SIXUNIT_GIF = os.environ.get("SCUMMBUCKET_ROOM23_SIXUNIT_GIF")
PIL_AVAILABLE = find_spec("PIL") is not None
EXPECTED = (
    ("1a654c4ed3575ccca020d00566be0baab1bfade51d0c1439e144d7e91b516f95", 20, 17),
    ("c93407c5e95114849daf3faf12077393f5ae6680f3093f9aa5bd0a3c69262d03", 14, 13),
)
SOURCE_SHA = "ad045372e0d49626503bb50fca29a687ec8e01ef75d9b8bca702a366d143819e"


def read_gif(path: Path):
    """Validate private GIF and adjacent manifest, returning decoded RGB frames."""
    from PIL import Image

    manifest = path.with_suffix(".manifest.json")
    data = json.loads(manifest.read_text(encoding="utf-8"))
    raw = path.read_bytes()
    digest = sha256(raw).hexdigest()
    expected_digest = data["files"][0].get("sha256", digest)
    # The older source-backed exporter uses `name`, not `filename`.
    assert digest == expected_digest
    frames, durations = [], []
    with Image.open(path) as image:
        assert image.size == (320, 144)
        assert "loop" not in image.info
        for i in range(image.n_frames):
            image.seek(i)
            frames.append(image.convert("RGB").tobytes())
            durations.append(image.info["duration"])
    assert sum(durations) == 4000
    starts = [sum(durations[:i]) for i in range(len(durations))]
    return digest, frames, durations, starts, data


@unittest.skipUnless(bool(EVENT_GIF and SIXUNIT_GIF), "Set both private Room 23 GIF paths")
@unittest.skipUnless(PIL_AVAILABLE, "Pillow GIF extra not installed")
class PrivateRoom23CadenceComparison(unittest.TestCase):
    def test_six_unit_model_preserves_all_100ms_samples(self):
        a_hash, a, ad, a_starts, am = read_gif(Path(EVENT_GIF))
        b_hash, b, bd, b_starts, bm = read_gif(Path(SIXUNIT_GIF))
        for digest, frames, expected in zip((a_hash, b_hash), (a, b), EXPECTED):
            self.assertEqual(digest, expected[0])
            self.assertEqual(len(frames), expected[1])
            self.assertEqual(len(set(frames)), expected[2])

        self.assertEqual(am["summary"]["gif_frames_written"], 20)
        self.assertEqual(am["summary"]["visible_event_boundaries"], 19)
        self.assertEqual(am["summary"]["duration_encoded_ms"], 4000)
        self.assertEqual(bm["summary"]["gif_frames_written"], 14)
        self.assertEqual(bm["summary"]["palette_rotation_events"], 32)
        self.assertEqual(bm["summary"]["unique_source_cycle_pixels"], 480)
        self.assertEqual(bm["source"]["resource_sha256"], SOURCE_SHA)
        self.assertEqual(am["provenance"]["declared_original_resource_sha256"], SOURCE_SHA)
        self.assertEqual([s["duration_ms"] for s in am["segments"]], ad)
        self.assertEqual([s["duration_ms"] for s in bm["segments"]], bd)
        self.assertFalse(am["timing"]["real_engine_update_schedule_verified"])
        self.assertFalse(bm["timing"]["engine_timer_values_observed"])
        self.assertTrue(set(b).issubset(set(a)))
        self.assertEqual(len(set(a) - set(b)), 4)
        for t in range(0, 4000, 100):
            a_frame = a[bisect_right(a_starts, t) - 1]
            b_frame = b[bisect_right(b_starts, t) - 1]
            self.assertEqual(a_frame, b_frame, f"RGB mismatch at t={t} ms")
        altered = {i for i in range(320 * 144) if any(
            frame[i * 3:i * 3 + 3] != b[0][i * 3:i * 3 + 3]
            for frame in b[1:]
        )}
        self.assertEqual(len(altered), 480)
        self.assertEqual((min(i // 320 for i in altered), max(i // 320 for i in altered)),
                         (52, 123))


if __name__ == "__main__":
    unittest.main()
