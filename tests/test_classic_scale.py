import hashlib
import unittest

from scummbucket.classic_scale import threshold


class ScaleTableTest(unittest.TestCase):
    def test_pinned_dos_table_and_phase_wrap(self):
        expected = '4848f9b3128d7bd5f591097002c691fb997da40168f12035ec5f80a9f75696e8'
        for start in (-256, 0, 256):
            table = bytes(threshold(i) for i in range(start,start+256))
            self.assertEqual(hashlib.sha256(table).hexdigest(),expected)
