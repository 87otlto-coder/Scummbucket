import unittest

from tools.compare_room35_capture import retain_unchanged_front


class Room35RetainedPoseTests(unittest.TestCase):
    def setUp(self):
        self.actors = (("actor", "1", "163", "106", "1"), ("scale", "1", "81", "81"))

    def test_idle_visible_actor_retains_reconstructed_pixels(self):
        previous = (b"bg", self.actors, b"fg")
        self.assertEqual(retain_unchanged_front(previous, b"bg", self.actors), b"fg")

    def test_missing_or_changed_pose_requires_draw_evidence(self):
        for previous in (None, (b"other", self.actors, b"fg"), (b"bg", (), b"fg")):
            with self.subTest(previous=previous), self.assertRaises(ValueError):
                retain_unchanged_front(previous, b"bg", self.actors)

    def test_no_visible_actors_uses_background(self):
        self.assertEqual(retain_unchanged_front(None, b"bg", ()), b"bg")
