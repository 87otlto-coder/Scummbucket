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

    def test_invalid_selector_and_range(self):
        c=costume([1],{});s=AnimationState()
        with self.assertRaises(ValueError):initialize(c,s,1,45)
        s.cursors[0]=20;s.ends[0]=10
        with self.assertRaises(ValueError):advance(c,s)
