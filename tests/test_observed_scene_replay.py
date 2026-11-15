"""Synthetic native-indexed integration, including real COST painting delegation."""
from copy import deepcopy
from hashlib import sha256
from types import SimpleNamespace
from unittest.mock import patch
import unittest

from scummbucket.observed_scene_replay import (
    observed_frame_packet, replay_observed_frame, compare_native_frame)
from tools.replay_observed_scene import read_observed_packet
from tools.compare_cross_room_scene import costumes_from_archive


class ObservedReplayTests(unittest.TestCase):
    def setUp(self):
        self.scene = dict(manifest=dict(room_id=7, dimensions=[8, 4]),
                          background=bytes(range(32)), palette=bytes(768),
                          masks={1: bytes([0]*3+[255]+[0]*28)})
        cel = SimpleNamespace(rel_x=0, rel_y=0, width=1, height=1,
                              slots=b'\1', move_x=0, move_y=0)
        self.costume = SimpleNamespace(colors=16, force_right=False,
                                       palette=bytes([0, 99]+[0]*14),
                                       limb=lambda n, pos: None if pos == 65535 else (0, cel))
        self.actor = dict(id=1, screen_x=0, draw_y=0, plane=0, scales=[255, 255],
                          costume=1, facing=180, stopped=0, logical_frame=1,
                          cursors=[0]+[65535]*15, palette_override=[255]*32)

    def packet(self, actors=None, viewport=(2, 0, 4, 4)):
        return observed_frame_packet(frame_id=1, tick=20, room_id=7,
                                     viewport=viewport, actors=[self.actor] if actors is None else actors,
                                     palette=bytes([4])*768, raw_sha256='a'*64)

    def test_camera_crops_source_without_double_transforming_recorded_actor(self):
        result = replay_observed_frame(self.scene, {1: self.costume}, self.packet())
        self.assertEqual(result['indices'][:4], bytes([99, 3, 4, 5]))
        self.assertEqual(result['palette'], bytes([4])*768)
        self.assertEqual(result['scene_fidelity'], 'NOT VALIDATED')
        self.assertEqual(result['evidence'], ['archive_decoded', 'engine_observed'])

    def test_observed_order_mask_and_stopped_limb_through_actual_compositor(self):
        first = deepcopy(self.actor)
        first['screen_x'] = 1
        second = deepcopy(first)
        second['palette_override'][1] = 77
        second['plane'] = 1
        packet = self.packet([first, second])
        result = replay_observed_frame(self.scene, {1: self.costume}, packet)
        self.assertEqual(result['indices'][1], 99)  # Room x=3 is masked.
        control = replay_observed_frame(self.scene, {1: self.costume}, packet, mask_enabled=False)
        self.assertEqual(control['indices'][1], 77)
        packet['events'][1]['draw_order'][0]['row']['stopped'] = 1
        result = replay_observed_frame(self.scene, {1: self.costume}, packet)
        self.assertEqual(result['indices'][1], 3)
        self.assertEqual(self.scene['masks'][1][3], 255)

    def test_no_missing_actor_pose_is_inserted_and_order_is_copied(self):
        packet = self.packet()
        self.actor['screen_x'] = 3
        self.assertEqual(packet['events'][1]['draw_order'][0]['row']['screen_x'], 0)
        no_actors = replay_observed_frame(self.scene, {}, self.packet([]))
        self.assertEqual(no_actors['indices'][:4], bytes([2, 3, 4, 5]))

    def test_reference_mismatch_is_explicit_and_palette_is_not_predicted(self):
        result = replay_observed_frame(self.scene, {1: self.costume}, self.packet())
        reference = bytearray(result['indices'])
        reference[0] ^= 1
        comparison = compare_native_frame(result, bytes(reference), bytes(768))
        self.assertEqual(comparison['indexed_errors'], 1)
        self.assertEqual(comparison['palette_byte_errors'], 768)
        self.assertNotEqual(comparison['predicted_indexed_sha256'], comparison['reference_indexed_sha256'])
        with self.assertRaises(ValueError):
            compare_native_frame(result, b'', bytes(768))

    def test_packet_rejects_invalid_provenance_and_geometry(self):
        for changes in (dict(frame_id=0), dict(tick=True), dict(viewport=[-1, 0, 4, 4]),
                        dict(raw_sha256='bad'), dict(palette=b''), dict(actors=[None])):
            args = dict(frame_id=1, tick=0, room_id=7, viewport=[0, 0, 4, 4],
                        actors=[], palette=bytes(768), raw_sha256='a'*64)
            args.update(changes)
            with self.subTest(changes=list(changes)):
                with self.assertRaises(ValueError):
                    observed_frame_packet(**args)
        wrong_room = self.packet()
        wrong_room['room_id'] = 12
        with self.assertRaisesRegex(ValueError, 'different source room'):
            replay_observed_frame(self.scene, {}, wrong_room)


class RawObservationTests(unittest.TestCase):
    def test_costume_archive_reopen_and_scene_fingerprints_are_checked(self):
        sources = [dict(sha256=sha256(v).hexdigest()) for v in (b'index', b'resource')]
        inventory = dict(status='success', sources=sources, directory_links=dict(entries=[]))
        with (patch('tools.compare_cross_room_scene.inspect', return_value=inventory),
              patch('tools.compare_cross_room_scene._read_pair',
                    return_value=(b'index', b'changed', '', ''))):
            with self.assertRaisesRegex(ValueError, 'changed after inspection'):
                costumes_from_archive('synthetic', set())
            with self.assertRaisesRegex(ValueError, 'differs from source scene'):
                costumes_from_archive('synthetic', set(), expected_sources=[dict(sha256='bad')])

    def make_raw(self, camera='camera 160 72 0 0 320 144 320 144'):
        palette = bytes([7])*768
        background = bytes(46080)
        front = bytes([9])+bytes(46079)
        actor = 'draw_actor 1 0 0 0 255 255 180 1 1 0 ' + ' '.join(
            map(str, [0]+[65535]*15+[255]*32))
        header = ('R23E1 1 100 6 6 0 1 1 0 0\nSynthetic\nscene 7 20\n'+
                  camera+'\n'+actor+'\nDATA\n').encode()
        raw = header+palette*4+background+front+bytes(5760)+front+bytes(17920)
        from tools.verify_cross_room_capture import parse_draw_actor
        row = dict(indexed_frame=1, room=7, tick=20, actors=[parse_draw_actor(actor)],
                   raw_sha256=sha256(raw).hexdigest(), front_sha256=sha256(front).hexdigest(),
                   background_sha256=sha256(background).hexdigest(),
                   final_palette_sha256=sha256(palette).hexdigest())
        scene = dict(manifest=dict(room_id=7, dimensions=[320, 144]))
        return raw, row, scene

    def test_original_raw_record_and_report_bind_actor_order_camera_and_palette(self):
        raw, row, scene = self.make_raw()
        packet, background, front, palette = read_observed_packet(raw, row, scene)
        self.assertEqual(packet['viewport'], [0, 0, 320, 144])
        self.assertEqual(front[0], 9)
        self.assertEqual(palette, bytes([7])*768)
        self.assertEqual(len(background), 46080)
        for key, value in (('tick', 21), ('actors', []), ('front_sha256', 'b'*64),
                           ('final_palette_sha256', 'b'*64), ('raw_sha256', 'b'*64)):
            bad = dict(row, **{key: value})
            with self.subTest(key=key):
                with self.assertRaises(ValueError):
                    read_observed_packet(raw, bad, scene)

    def test_bad_or_ambiguous_camera_is_not_guessed(self):
        for camera in ('', 'camera 1 2', 'camera 160 72 0 0 320 144 784 144',
                       'camera 160 72 0 0 320 144 320 144\ncamera 160 72 0 0 320 144 320 144'):
            with self.subTest(camera=camera):
                raw, row, scene = self.make_raw(camera)
                with self.assertRaises(ValueError):
                    read_observed_packet(raw, row, scene)


if __name__ == '__main__':
    unittest.main()
