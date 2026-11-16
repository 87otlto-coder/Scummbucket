"""Corpus checks use synthetic resources and preserve individual failures."""
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch
import unittest

from scummbucket.inspector import _read_pair
from test_inspector import index, make_zip
from test_object_images import synthetic_resource
from tools.audit_object_state_corpus import audit


class ObjectCorpusTests(unittest.TestCase):
    def setUp(self):
        self.tmp = TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.game = Path(self.tmp.name)/'synthetic.zip'
        make_zip(self.game, a=index(), b=synthetic_resource())

    def test_consistency_checks_native_opacity_rgba_and_masks(self):
        before = self.game.read_bytes()
        result = audit(self.game)
        self.assertEqual(result['status'], 'source_consistency_passed')
        self.assertEqual(result['summary']['states_consistent'], 2)
        self.assertEqual(result['summary']['decoded_pixels'], 128)
        self.assertEqual(result['summary']['rgba_byte_errors'], 0)
        self.assertEqual(result['summary']['mask_pixel_errors'], 0)
        self.assertFalse(result['runtime_fidelity_verified'])
        self.assertEqual([s['transparent_pixels'] for s in result['states']], [64, 0])
        self.assertEqual(self.game.read_bytes(), before)

    def test_unsupported_state_does_not_hide_successful_state(self):
        make_zip(self.game, a=index(), b=synthetic_resource(bad_code=251))
        result = audit(self.game)
        self.assertEqual(result['status'], 'PARTIAL')
        self.assertEqual(result['summary']['states_failed'], 1)
        self.assertEqual(result['summary']['states_consistent'], 1)
        self.assertEqual(result['failures'], {'STRIP_CODEC_UNSUPPORTED': 1})

    def test_changed_archive_is_rejected_before_corpus_decode(self):
        a, b, x, y = _read_pair(self.game)
        with patch('tools.audit_object_state_corpus._read_pair', return_value=(a, b+b'changed', x, y)):
            with self.assertRaisesRegex(ValueError, 'changed'):
                audit(self.game)


if __name__ == '__main__':
    unittest.main()
