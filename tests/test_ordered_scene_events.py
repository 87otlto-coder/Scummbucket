"""P4 event-driven native scene composition, synthetic indexed buffers only."""
from hashlib import sha256
from unittest.mock import patch
import unittest

from scummbucket.ordered_scene_events import SceneEventError, render_scene_event_frames


class OrderedSceneEventTests(unittest.TestCase):
    def setUp(self):
        self.scene = {
            'manifest': {'dimensions': [6, 4]},
            'background': bytes([9] * 24),
            'palette': bytes(768),
            'masks': {1: bytes([255, 0, 0, 0, 0, 0] + [0] * 18)},
        }
        self.a = {'object_id': 57, 'state_tag': 'IM01', 'width': 2, 'height': 2,
                  'pixels': bytes([5, 2, 3, 4]), 'opacity': bytes([255, 0, 255, 255])}
        self.b = {**self.a, 'state_tag': 'IM02', 'pixels': bytes([8] * 4),
                  'opacity': bytes([255] * 4)}
        self.objects = {(57, 'IM01'): self.a, (57, 'IM02'): self.b}

    @staticmethod
    def event(tick, order, kind, **kwargs):
        return dict(tick=tick, order=order, kind=kind, evidence='synthetic', **kwargs)

    def run_frames(self, events, *, viewport=None):
        return list(render_scene_event_frames(self.scene, self.objects, {}, events,
                                              viewport=viewport))

    def test_palette_changes_do_not_modify_native_indices(self):
        e = self.event
        events = [e(1, 0, 'object_state', object_id=57, state_tag='IM01', x=1, y=1),
                  e(1, 1, 'frame', draw_order=[{'kind': 'object', 'object_id': 57,
                                                'occlusion_plane': 0}]),
                  e(2, 0, 'palette_patch', entries=[{'index': 5, 'rgb': [15, 40, 80]}]),
                  e(2, 1, 'frame', draw_order=[{'kind': 'object', 'object_id': 57,
                                                'occlusion_plane': 0}])]
        a, b = self.run_frames(events)
        self.assertEqual(a['indices'], b['indices'])
        self.assertNotEqual(a['palette_sha256'], b['palette_sha256'])
        self.assertEqual(b['palette'][15:18], bytes([15, 40, 80]))
        self.assertEqual(b['indices'][1 * 6 + 1], 5)  # Opaque TRNS-like index.
        self.assertEqual(b['indices'][1 * 6 + 2], 9)  # Explicit transparent pixel.
        self.assertEqual(b['indexed_sha256'], sha256(b['indices']).hexdigest())
        self.assertEqual(b['scene_fidelity'], 'NOT VALIDATED')
        self.assertIn('synthetic', b['evidence'])
        self.assertFalse(b['engine_timing_inferred'])

    def test_explicit_state_change_hide_and_nonautomatic_draw(self):
        e = self.event
        events = [e(0, 0, 'object_state', object_id=57, state_tag='IM01', x=0, y=0),
                  e(0, 1, 'frame', draw_order=[]),
                  e(1, 0, 'object_state', object_id=57, state_tag='IM02', x=0, y=0),
                  e(1, 1, 'frame', draw_order=[{'kind': 'object', 'object_id': 57,
                                                'occlusion_plane': 0}]),
                  e(2, 0, 'object_hide', object_id=57),
                  e(2, 1, 'frame', draw_order=[])]
        frames = self.run_frames(events)
        self.assertEqual(frames[0]['indices'], self.scene['background'])
        self.assertEqual(frames[1]['indices'][0], 8)
        self.assertEqual(frames[2]['indices'], self.scene['background'])

    def test_room_occlusion_and_fixed_viewport_clipping(self):
        e = self.event
        events = [e(1, 0, 'object_state', object_id=57, state_tag='IM02', x=0, y=0),
                  e(1, 1, 'frame', draw_order=[{'kind': 'object', 'object_id': 57,
                                                'occlusion_plane': 1}])]
        frame, = self.run_frames(events)
        self.assertEqual(frame['indices'][0], 9)
        self.assertEqual(frame['indices'][1], 8)
        clipped, = self.run_frames(events, viewport=(1, 0, 3, 2))
        self.assertEqual(clipped['indices'][0], 8)
        self.assertEqual(len(clipped['indices']), 6)

    def test_actor_draw_delegates_to_existing_ordered_compositor(self):
        e = self.event
        events = [e(1, 0, 'object_state', object_id=57, state_tag='IM02', x=0, y=0),
                  e(1, 1, 'frame', draw_order=[
                      {'kind': 'object', 'object_id': 57, 'occlusion_plane': 0},
                      {'kind': 'actor', 'row': {'actor_id': 1}}]),
                  e(2, 0, 'frame', draw_order=[
                      {'kind': 'actor', 'row': {'actor_id': 1}},
                      {'kind': 'object', 'object_id': 57, 'occlusion_plane': 0}])]
        def fake_actor(scene, costumes, rows, viewport):
            self.assertEqual(rows, [{'actor_id': 1}])
            self.assertEqual(viewport, (0, 0, 6, 4))
            canvas = bytearray(scene['background'])
            canvas[0] = 7
            return bytes(canvas)
        with patch('scummbucket.scene_source.compose_actor_layers', side_effect=fake_actor) as called:
            first, second = self.run_frames(events)
        self.assertEqual(called.call_count, 2)
        self.assertEqual(first['indices'][0], 7)
        self.assertEqual(second['indices'][0], 8)

    def test_fail_closed_for_unobserved_or_missing_layer_state(self):
        e = self.event
        cases = [
            ([e(0, 0, 'frame', draw_order=[{'kind': 'object', 'object_id': 57,
                                           'occlusion_plane': 0}])], 'OBJECT_NOT_ACTIVE'),
            ([e(0, 0, 'object_hide', object_id=57)], 'OBJECT_NOT_ACTIVE'),
            ([e(0, 0, 'object_state', object_id=58, state_tag='IM01', x=0, y=0)],
             'OBJECT_STATE_MISSING'),
            ([e(0, 0, 'object_state', object_id=57, state_tag='IM01', x=0, y=0),
              e(0, 1, 'frame', draw_order=[{'kind': 'object', 'object_id': 57,
                                           'occlusion_plane': 2}])], 'OCCLUSION_PLANE_MISSING'),
            ([e(0, 0, 'frame', draw_order=[{'kind': 'unknown'}])], 'DRAW_KIND_UNSUPPORTED'),
            ([e(0, 0, 'frame', draw_order=[]), e(0, 0, 'frame', draw_order=[])],
             'EVENT_ORDER_INVALID'),
            ([e(0, 0, 'frame', draw_order=[]), e(0, 1, 'palette_patch',
                                                entries=[{'index': 5, 'rgb': [1, 2, 3]},
                                                         {'index': 5, 'rgb': [4, 5, 6]}])],
             'PALETTE_PATCH_INVALID'),
            ([e(0, 0, 'frame', draw_order=[]), dict(tick=1, order=0, kind='frame',
                                                draw_order=[])], 'EVENT_EVIDENCE_INVALID'),
            ([e(0, 0, 'frame', draw_order=[], surprise=True)], 'FRAME_EVENT_INVALID'),
        ]
        for events, code in cases:
            with self.subTest(code=code):
                with self.assertRaises(SceneEventError) as caught:
                    self.run_frames(events)
                self.assertEqual(caught.exception.code, code)
                self.assertIsNotNone(caught.exception.event_index)

    def test_actor_compositor_failure_surfaces_event_context(self):
        e = self.event
        events = [e(0, 0, 'frame', draw_order=[{'kind': 'actor', 'row': {'bad': 1}}])]
        with patch('scummbucket.scene_source.compose_actor_layers',
                   side_effect=ValueError('Unsupported pose')):
            with self.assertRaises(SceneEventError) as caught:
                self.run_frames(events)
        self.assertEqual(caught.exception.code, 'ACTOR_COMPOSITION_FAILED')
        self.assertEqual(caught.exception.event_index, 0)
        self.assertIn('Unsupported pose', str(caught.exception))

    def test_input_buffers_not_modified(self):
        e = self.event
        before = (self.scene['background'], self.scene['palette'], self.a['pixels'])
        events = [e(0, 0, 'object_state', object_id=57, state_tag='IM01', x=0, y=0),
                  e(0, 1, 'frame', draw_order=[{'kind': 'object', 'object_id': 57,
                                                'occlusion_plane': 0}])]
        self.run_frames(events)
        self.assertEqual(before, (self.scene['background'], self.scene['palette'], self.a['pixels']))


if __name__ == '__main__':
    unittest.main()
