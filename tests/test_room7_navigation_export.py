"""Synthetic-only contract tests for segmented native Room 7 animation export.

No original game art or capture binary is used in public CI.
"""
from copy import deepcopy
import unittest

from scummbucket.room7_navigation_export import (
    make_manifest, make_segments, render_player,
)


def rows_and_frames():
    rows = []
    pictures = []
    for frame, tick, ms in [(1, 960, 10000), (2, 961, 10100),
                            (3, 1113, 25302), (4, 1114, 25402)]:
        rows.append(dict(frame=frame, tick=tick, present_ms=ms,
                         comparison={"masked_errors": 0},
                         transition="segment_start" if frame in (1, 3) else None))
        pictures.append(dict(
            frame=frame, file=f"frame-{frame:04d}.png", present_ms=ms,
            indexed_sha256="a"*64, palette_sha256="b"*64,
            png_sha256="c"*64,
        ))
    return rows, pictures


class Room7NavigationExportTests(unittest.TestCase):
    def test_missing_interior_ticks_split_segments_not_playback(self):
        rows, pictures = rows_and_frames()
        sections = make_segments(rows, pictures)
        self.assertEqual(len(sections), 2)
        self.assertEqual([(s["first_frame"], s["last_frame"])
                          for s in sections], [(1, 2), (3, 4)])
        self.assertIsNone(sections[0]["omitted_ticks_before"])
        self.assertEqual(sections[1]["omitted_ticks_before"], 151)

    def test_player_resets_clock_after_interior_gap(self):
        rows, pictures = rows_and_frames()
        manifest = make_manifest(rows, pictures, capture="private-capture",
                                 archive_hashes={"MONKEY2.000":"a"*64})
        html = render_player(manifest)
        self.assertIn("frame-0001.png", html)
        self.assertIn("frame-0004.png", html)
        self.assertIn('"frames":[["frame-0003.png",0],["frame-0004.png",100]]', html)
        self.assertIn("unrecorded ticks", html)
        self.assertNotIn("__ANIMATION_TIMELINE__", html)
        self.assertFalse(manifest["room12_frames_included"])
        self.assertTrue(manifest["all_indexed_comparisons_exact"])

    def test_a_single_zero_error_gapless_trace_is_one_segment(self):
        rows, pictures = rows_and_frames()
        rows[2]["tick"], rows[3]["tick"] = 962, 963
        self.assertEqual(len(make_segments(rows, pictures)), 1)

    def test_missing_or_unverified_frame_is_rejected(self):
        rows, pictures = rows_and_frames()
        for altered_rows, altered_pictures in [
            (rows, pictures[:-1]),
            ([*rows[:1], *rows[2:]], pictures),
            (rows, [{**pictures[0], "file":"../evil.png"}, *pictures[1:]]),
            ([{**rows[0], "comparison":{"masked_errors":1}}, *rows[1:]], pictures),
            ([{**rows[0], "comparison":None}, *rows[1:]], pictures),
            (rows, [{**pictures[0], "indexed_sha256":"g"*64}, *pictures[1:]]),
        ]:
            with self.subTest(altered_rows=altered_rows, altered_pictures=altered_pictures):
                with self.assertRaises(ValueError):
                    make_segments(altered_rows, altered_pictures)

    def test_tick_and_presentation_regressions_fail(self):
        rows, pictures = rows_and_frames()
        for field, value in [
            ("tick", 960), ("tick", 959), ("present_ms", 9999),
        ]:
            broken = deepcopy(rows)
            broken[1][field] = value
            with self.subTest(field=field, value=value):
                with self.assertRaises(ValueError):
                    make_segments(broken, pictures)

    def test_manifest_retains_capture_provenance(self):
        rows, pictures = rows_and_frames()
        manifest = make_manifest(
            rows, pictures, archive_hashes={"MONKEY2.001":"d"*64},
            capture="FIXTURE/CAPTURES/Room7/example")
        self.assertEqual(manifest["frame_count"], 4)
        self.assertEqual(manifest["edition"], "Monkey Island 2, original DOS VGA")
        self.assertEqual(manifest["archive_sha256"]["MONKEY2.001"], "d"*64)
        self.assertEqual(manifest["palette_source"],
                         "engine-observed post-presentation palette; not independently forecast here")
        self.assertEqual(manifest["gap_policy"],
                         "separate playbacks, never interpolate skipped engine ticks")


if __name__ == "__main__":
    unittest.main()
