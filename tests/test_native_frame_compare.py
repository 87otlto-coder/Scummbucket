import unittest

from scummbucket.native_frame_compare import compare_native_frame


class NativeFrameComparisonTests(unittest.TestCase):
    def test_coordinates_values_and_palette_entry_count(self):
        actual = bytes([1, 2, 3, 4])
        reference = bytes([1, 2, 4, 5])
        palette = bytes(768)
        reference_palette = bytes(3) + bytes([7, 8, 9]) + bytes(762)
        report = compare_native_frame(actual, palette, reference, reference_palette, width=2, height=2)
        self.assertEqual(report["indices"]["mismatches"], 2)
        self.assertEqual(report["indices"]["first_mismatch"],
                         dict(location=dict(x=0, y=1), actual=[3], expected=[4]))
        self.assertEqual(report["palette"]["mismatches"], 1)
        self.assertEqual(report["palette"]["first_mismatch"],
                         dict(location=dict(index=1), actual=[0, 0, 0], expected=[7, 8, 9]))
        exact = compare_native_frame(actual, palette, actual, palette, width=2, height=2)
        for family in ("indices", "palette"):
            self.assertEqual(exact[family]["mismatches"], 0)
            self.assertIsNone(exact[family]["first_mismatch"])

    def test_rejects_truncated_reference(self):
        with self.assertRaisesRegex(ValueError, "Expected 768 bytes"):
            compare_native_frame(b"x", bytes(768), b"x", bytes(767), width=1, height=1)
