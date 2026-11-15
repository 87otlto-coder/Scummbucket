"""Instrumentation contract tested against fabricated source, not game data."""
from hashlib import sha256
import json
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch
import unittest

from tools.prepare_actor_state_capture import prepare, transform, STATE_FIELDS


SOURCE = 'void Actor::drawActorCostume(bool hitTestMode) {\n\tif (_costume == 0)\n\t\treturn;\n}\n'


class ActorStateCaptureTests(unittest.TestCase):
    def test_snapshot_precedes_redraw_gate_without_forcing_a_render(self):
        result = transform(SOURCE.replace('\n', '\r\n'))
        self.assertLess(result.index('state_actor '), result.index('if (_costume == 0)'))
        inserted = result[result.index('// ScummBucket:'):result.index('\tif (_costume == 0)')]
        for forbidden in ('setupActorScale(', 'prepareDrawActorCostume(', 'drawCostume(',
                          '_needRedraw =', '_cost.curpos[limb] ='):
            self.assertNotIn(forbidden, inserted)
        self.assertEqual(len(STATE_FIELDS), 27)
        with self.assertRaises(ValueError):
            transform(SOURCE+SOURCE)

    def test_bad_pin_fails_before_any_destination_creation(self):
        with TemporaryDirectory() as temp:
            root = Path(temp)
            source = root/'source/engines/scumm/actor.cpp'
            source.parent.mkdir(parents=True)
            source.write_text(SOURCE)
            target = root/'overlay'
            with self.assertRaisesRegex(ValueError, 'fingerprint'):
                prepare(root/'source', target)
            self.assertFalse(target.exists())

    def test_exclusive_overlay_records_source_hash_and_unverified_runtime(self):
        with TemporaryDirectory() as temp:
            root = Path(temp)
            source = root/'source/engines/scumm/actor.cpp'
            source.parent.mkdir(parents=True)
            source.write_bytes(SOURCE.encode())
            with patch('tools.prepare_actor_state_capture.ACTOR_SHA256', sha256(source.read_bytes()).hexdigest()):
                result = prepare(root/'source', root/'overlay')
                self.assertFalse(result['runtime_verified'])
                self.assertFalse(result['snapshot_is_draw_operation'])
                self.assertEqual(result['output_sha256'], sha256((root/'overlay/actor.cpp').read_bytes()).hexdigest())
                with self.assertRaises(FileExistsError):
                    prepare(root/'source', root/'overlay')


if __name__ == '__main__':
    unittest.main()
