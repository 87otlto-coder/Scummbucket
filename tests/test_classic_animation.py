import unittest
from types import SimpleNamespace
from scummbucket.classic_animation import AnimationState, initialize, advance

def costume(commands, records):
    data=bytearray(256); data[8]=31
    for frame,entries in records.items():
        offset=100+frame*15
        data[60+frame*8:62+frame*8]=(offset-2).to_bytes(2,'little')
        mask=sum(32768>>i for i in entries)
        data[offset:offset+2]=mask.to_bytes(2,'little'); offset+=2
        for limb,(start,extent) in sorted(entries.items()):
            data[offset:offset+2]=start.to_bytes(2,'little'); offset+=2
            if start!=65535: data[offset]=extent; offset+=1
    data[220:220+len(commands)]=bytes(commands)
    return SimpleNamespace(data=bytes(data),table_start=26,commands=220,
        pointer=lambda p:2+int.from_bytes(data[p:p+2],'little'))

class AnimationTests(unittest.TestCase):
    def test_loop_events_and_wrapping(self):
        c=costume([1,0x78,0x7c,2],{1:{0:(0,3)}}); s=AnimationState()
        self.assertTrue(initialize(c,s,1,270)); self.assertEqual(s.cursors[0],0)
        self.assertTrue(advance(c,s)); self.assertEqual(s.cursors[0],3)
        self.assertEqual((s.sound_counter,s.animation_counter),(1,1))
        advance(c,s); self.assertEqual(s.cursors[0],0)

    def test_stop_resume_inherit_and_disable(self):
        c=costume([4,0x79,0x7a],{1:{0:(0,0)},2:{0:(1,0)},3:{0:(2,0)},4:{0:(65535,0)}})
        s=AnimationState();initialize(c,s,1,270);initialize(c,s,2,270)
        self.assertEqual(s.cursors[0],0);self.assertEqual(s.visible_positions()[0],65535)
        initialize(c,s,3,270);self.assertEqual(s.visible_positions()[0],0)
        initialize(c,s,4,270);self.assertEqual(s.cursors[0],65535)

    def test_one_shot_holds_terminal_and_usemask(self):
        c=costume([1,2,3],{1:{0:(0,130),1:(1,0)}});s=AnimationState()
        initialize(c,s,1,270,32768)
        self.assertEqual(s.cursors[1],65535)
        for _ in range(5):advance(c,s)
        self.assertEqual(s.cursors[0],32770)

    def test_control_only_cycle_fails(self):
        c=costume([0x78,0x7c],{1:{0:(0,1)}});s=AnimationState();initialize(c,s,1,270)
        with self.assertRaisesRegex(ValueError,'Control-only'):advance(c,s)

    def test_selector_frames_and_stop_resume_preserve_previous_frame(self):
        c = costume([4, 0x79, 0x7a], {
            1: {0: (0, 0)}, 2: {0: (1, 0)},
            3: {0: (2, 0)}, 4: {0: (65535, 0)},
        })
        state = AnimationState()
        self.assertTrue(initialize(c, state, 1, 270))
        self.assertEqual(state.limb_frames[0], 4)
        initialize(c, state, 2, 270)
        self.assertTrue(state.stopped & 1)
        self.assertEqual(state.limb_frames[0], 4)
        initialize(c, state, 3, 270)
        self.assertFalse(state.stopped & 1)
        self.assertEqual(state.limb_frames[0], 4)
        initialize(c, state, 4, 270)
        self.assertEqual(state.cursors[0], 65535)
        self.assertEqual(state.limb_frames[0], 16)

    def test_late_invalid_limb_does_not_partially_initialize(self):
        from copy import deepcopy
        c = costume([4], {1: {0: (0, 0), 1: (25, 127)}})
        state = AnimationState()
        initial = deepcopy(state)
        with self.assertRaisesRegex(ValueError, 'range outside COST'):
            initialize(c, state, 1, 270)
        self.assertEqual(state, initial)

    def test_usemask_only_initializes_enabled_limb(self):
        c = costume([4, 5], {1: {0: (0, 0), 1: (1, 0)}})
        state = AnimationState()
        initialize(c, state, 1, 270, 32768)
        self.assertEqual(state.cursors[:2], [0, 65535])
        self.assertEqual(state.limb_frames[:2], [4, 65535])
        initialize(c, state, 1, 270, 16384)
        self.assertEqual(state.cursors[:2], [0, 1])
        self.assertEqual(state.limb_frames[:2], [4, 4])

    def test_stop_resume_ignore_unused_extent_without_overreading(self):
        c = costume([4, 0x79, 0x7a],
                    {1: {0: (1, 127)}, 2: {0: (2, 127)}})
        state = AnimationState()
        state.cursors[0] = 7
        state.limb_frames[0] = 3
        self.assertTrue(initialize(c, state, 1, 270))
        self.assertTrue(state.stopped & 1)
        self.assertEqual((state.cursors[0], state.limb_frames[0]), (7, 3))
        self.assertTrue(initialize(c, state, 2, 270))
        self.assertFalse(state.stopped & 1)
        self.assertEqual((state.cursors[0], state.limb_frames[0]), (7, 3))

    def test_unavailable_selector_preserves_all_state(self):
        from copy import deepcopy
        c = costume([4], {})
        state = AnimationState()
        initial = deepcopy(state)
        self.assertFalse(initialize(c, state, 255, 270))
        self.assertEqual(state, initial)

    def test_rejects_malformed_state_width_and_boolean_usemask(self):
        c = costume([4], {1: {0: (0, 0)}})
        state = AnimationState()
        state.limb_frames.pop()
        with self.assertRaisesRegex(ValueError, 'limb state width'):
            initialize(c, state, 1, 270)
        with self.assertRaisesRegex(ValueError, 'selector'):
            initialize(c, AnimationState(), 1, 270, True)

    def test_invalid_selector_and_range(self):
        c=costume([1],{});s=AnimationState()
        with self.assertRaises(ValueError):initialize(c,s,1,45)
        s.cursors[0]=20;s.ends[0]=10
        with self.assertRaises(ValueError):advance(c,s)
