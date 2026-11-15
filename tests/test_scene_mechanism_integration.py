"""Real decoder/compositor integration using wholly synthetic OBIM and COST bytes.

These exercise the actual native engine modules without mocking actor painting.
No synthetic order, state change or palette event is called gameplay evidence.
"""
import unittest

from scummbucket.native_object_state import decode_indexed_object_state
from scummbucket.ordered_scene_events import render_scene_event_frames
from test_classic_costume import sample_32
from test_object_images import synth_obim, codec_pixels


class SceneMechanismIntegrationTests(unittest.TestCase):
    def setUp(self):
        data = synth_obim()
        self.states = {(99, tag):decode_indexed_object_state(
            data, obim_offset=0, state_tag=tag, transparent_color=5)
            for tag in ('IM01', 'IM02')}
        mask = bytearray(144)
        mask[2*12+3] = 255
        self.scene = dict(manifest=dict(dimensions=[12,12]), background=bytes([9])*144,
                          palette=bytes(768), masks={1:bytes(mask)})
        self.costume = sample_32()
        self.row = dict(id=1, screen_x=3, draw_y=4, plane=0, scales=[255,255],
                        facing=180, costume=1, logical_frame=1, stopped=0,
                        cursors=[0]+[65535]*15, palette_override=[255]*32)

    def event(self, tick, order, kind, **fields):
        return dict(tick=tick, order=order, kind=kind, evidence='synthetic', **fields)

    def render(self, events, viewport=None):
        return list(render_scene_event_frames(self.scene, self.states,
                    {1:self.costume}, events, viewport=viewport))

    def selection(self, tag='IM02'):
        return self.event(0,0,'object_state', object_id=99, state_tag=tag, x=2, y=2)

    def object_draw(self, plane=0):
        return dict(kind='object', object_id=99, occlusion_plane=plane)

    def actor_draw(self, **changes):
        return dict(kind='actor', row=dict(self.row, **changes))

    def test_actual_cost_and_obim_decode_respect_explicit_mixed_draw_order(self):
        events = [self.selection(),
                  self.event(0,1,'frame', draw_order=[self.object_draw(),self.actor_draw()]),
                  self.event(1,0,'frame', draw_order=[self.actor_draw(),self.object_draw()])]
        first, second = self.render(events)
        self.assertEqual(first['indices'][2*12+3],42)
        self.assertEqual(first['indices'][2*12+4],77)
        self.assertEqual(second['indices'][2*12+3],1)
        self.assertEqual(first['indices'][2*12+2],1)
        self.assertEqual(first['indices'][0],9)
        self.assertEqual(first['evidence'], ['archive_decoded','synthetic'])

    def test_actor_mask_reveals_prior_object_and_object_mask_reveals_prior_actor(self):
        events = [self.selection(),
                  self.event(0,1,'frame', draw_order=[
                      self.object_draw(),self.actor_draw(plane=1)]),
                  self.event(1,0,'frame', draw_order=[
                      self.actor_draw(),self.object_draw(plane=1)])]
        first, second = self.render(events)
        self.assertEqual(first['indices'][2*12+3],1)
        self.assertEqual(second['indices'][2*12+3],42)
        self.assertEqual(first['indices'][2*12+4],77)
        self.assertEqual(second['indices'][2*12+4],1)

    def test_palette_change_preserves_indices_through_both_actual_layer_types(self):
        events = [self.selection(),
                  self.event(0,1,'frame', draw_order=[self.object_draw(),self.actor_draw()]),
                  self.event(1,0,'palette_patch', entries=[
                      dict(index=42,rgb=[40,50,60]),dict(index=1,rgb=[10,20,30])]),
                  self.event(1,1,'frame', draw_order=[self.object_draw(),self.actor_draw()])]
        first, second = self.render(events)
        self.assertEqual(first['indices'],second['indices'])
        self.assertNotEqual(first['palette_sha256'],second['palette_sha256'])
        self.assertEqual(second['palette'][42*3:42*3+3],bytes([40,50,60]))
        self.assertEqual(second['palette'][3:6],bytes([10,20,30]))

    def test_nonzero_viewport_and_transparency_preserve_native_layers(self):
        events = [self.selection(),
                  self.event(0,1,'frame', draw_order=[
                      self.object_draw(),self.actor_draw(screen_x=1,draw_y=3)]),
                  self.event(1,0,'object_state', object_id=99,state_tag='IM01',x=2,y=2),
                  self.event(1,1,'frame', draw_order=[self.object_draw()])]
        first, second = self.render(events, viewport=(2,1,8,8))
        self.assertEqual(first['indices'][1*8+1],42)
        self.assertEqual(first['indices'][1*8+2],77)
        self.assertEqual(first['indices'][1*8],1)
        self.assertEqual(second['indices'],bytes([9])*64)

    def test_nominal_transparency_index_can_be_opaque_under_an_actual_strip_codec(self):
        data = synth_obim().replace(codec_pixels(68,1),codec_pixels(68,5))
        state = decode_indexed_object_state(data,obim_offset=0,state_tag='IM02',transparent_color=5)
        self.states[(99,'IM02')] = state
        frame, = self.render([self.selection(),self.event(0,1,'frame',draw_order=[self.object_draw()])])
        self.assertEqual(frame['indices'][2*12+2],5)
        self.assertEqual(state['opacity'],bytes([255])*64)


if __name__ == '__main__':
    unittest.main()
