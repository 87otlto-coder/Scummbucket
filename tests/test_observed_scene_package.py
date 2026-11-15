"""Private replay packaging tested with fabricated ROOM/COST resources only."""
from hashlib import sha256
import json
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch
import unittest

from scummbucket.observed_scene_package import export_replay_package, verify_replay_package
from scummbucket.observed_scene_replay import observed_frame_packet, replay_observed_frame
from scummbucket.palette_probe import decode_room_background_indexed
from test_classic_costume import sample
from test_palette_probe import fixture


class ObservedPackageTests(unittest.TestCase):
    def setUp(self):
        self.tmp = TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.dest = Path(self.tmp.name)/'replay'
        container = fixture()
        room = container[container.index(b'ROOM'):]
        bg = decode_room_background_indexed(room, room_offset=0, room_length=len(room))
        self.scene = dict(manifest=dict(schema='scumm-source-scene/0.1', room_id=7,
                         dimensions=[8, 8], room_length=len(room), room_sha256=sha256(room).hexdigest(),
                         indexed_sha256=sha256(bg['indexed_pixels']).hexdigest(),
                         palette_sha256=sha256(bg['initial_palette']).hexdigest(), masks={},
                         sources=[dict(name='synthetic', sha256='a'*64)]),
                         room_bytes=room, background=bg['indexed_pixels'], palette=bg['initial_palette'], masks={})
        self.costume = sample()
        actor = dict(id=1, screen_x=3, draw_y=4, plane=0, scales=[255, 255],
                     costume=1, facing=180, stopped=0, cursors=[0]+[65535]*15)
        packet = observed_frame_packet(frame_id=1, tick=10, room_id=7,
                                       viewport=[0, 0, 8, 8], actors=[actor],
                                       palette=bg['initial_palette'], raw_sha256='b'*64)
        result = replay_observed_frame(self.scene, {1:self.costume}, packet)
        self.sequence = dict(schema='scummbucket-observed-scene-sequence/1', room_id=7,
                             source_room_sha256=self.scene['manifest']['room_sha256'],
                             indexed_report_sha256='c'*64, frames=[packet])
        self.comparison = dict(schema='scummbucket-observed-event-replay-comparison/1', room_id=7,
                               samples=1, room_sha256=self.scene['manifest']['room_sha256'],
                               original_archives=self.scene['manifest']['sources'],
                               indexed_report_sha256='c'*64, status='PARTIAL', exact_frames=0,
                               indexed_errors=1, frames=[dict(indexed_frame=1, tick=10, raw_sha256='b'*64,
                               predicted_indexed_sha256=result['indexed_sha256'],
                               predicted_palette_sha256=result['palette_sha256'])])

    def export(self):
        with patch('scummbucket.scene_package.load_scene', return_value=self.scene):
            return export_replay_package('synthetic', self.dest, self.comparison, self.sequence, {1:self.costume})

    def rehash(self, name):
        data = (self.dest/name).read_bytes()
        m = json.loads((self.dest/'replay.json').read_text())
        m['files'][name] = dict(size=len(data), sha256=sha256(data).hexdigest())
        (self.dest/'replay.json').write_text(json.dumps(m))

    def test_offline_replay_uses_source_and_preserves_partial_acceptance(self):
        result = self.export()
        self.assertEqual(result['status'], 'offline_replay_reproduced')
        self.assertEqual(result['historical_scene_acceptance'], 'PARTIAL')
        self.assertEqual(result['historical_indexed_errors'], 1)
        self.assertFalse(result['raw_reference_revalidated'])
        self.assertTrue(result['source_images_redecoded'])
        self.assertEqual(verify_replay_package(self.dest), result)
        with self.assertRaises(FileExistsError):
            self.export()

    def test_altered_costume_and_unexpected_file_fail_integrity(self):
        self.export()
        p = self.dest/'costume-00001.bin'
        p.write_bytes(p.read_bytes()+b'bad')
        with self.assertRaisesRegex(ValueError, 'integrity'):
            verify_replay_package(self.dest)
        p.write_bytes(self.costume.data)
        (self.dest/'unexpected.txt').write_text('unexpected')
        with self.assertRaisesRegex(ValueError, 'Unexpected'):
            verify_replay_package(self.dest)

    def test_rehashed_event_mutation_still_fails_replay_comparison(self):
        self.export()
        p = self.dest/'events.json'
        m = json.loads(p.read_text())
        m['frames'][0]['events'][1]['draw_order'] = []
        p.write_text(json.dumps(m))
        self.rehash('events.json')
        with self.assertRaisesRegex(ValueError, 'differs'):
            verify_replay_package(self.dest)

    def test_rehashed_background_still_fails_independent_room_redecode(self):
        self.export()
        p = self.dest/'source/background.idx'
        p.write_bytes(bytes(64))
        sm_path = self.dest/'source/source.json'
        sm = json.loads(sm_path.read_text())
        sm['indexed_sha256'] = sha256(bytes(64)).hexdigest()
        sm['files']['background.idx']['sha256'] = sm['indexed_sha256']
        sm_path.write_text(json.dumps(sm))
        m = json.loads((self.dest/'replay.json').read_text())
        m['source_manifest_sha256'] = sha256(sm_path.read_bytes()).hexdigest()
        (self.dest/'replay.json').write_text(json.dumps(m))
        with self.assertRaisesRegex(ValueError, 're-decode'):
            verify_replay_package(self.dest)

    def test_traversal_inventory_and_wrong_room_are_rejected(self):
        self.export()
        m = json.loads((self.dest/'replay.json').read_text())
        m['files']['../outside'] = dict(size=0, sha256='a'*64)
        (self.dest/'replay.json').write_text(json.dumps(m))
        with self.assertRaisesRegex(ValueError, 'inventory'):
            verify_replay_package(self.dest)


if __name__ == '__main__':
    unittest.main()
