import unittest
from struct import pack
from types import SimpleNamespace
from scummbucket.scene_source import decode_boxes,decode_scales,source_scale,compose_actor,compose_actor_layers

class SceneSourceTests(unittest.TestCase):
    def test_scale_slot_truncation_clamp_and_reverse_slope(self):
        slots=decode_scales(pack('<4H',190,65,255,103))
        box=dict(scale_raw=32768)
        self.assertEqual(source_scale(box,slots,58),179)
        self.assertEqual(source_scale(box,slots,74),205)
        self.assertEqual(source_scale(box,slots,200),255)
        self.assertEqual(source_scale(dict(scale_raw=150),slots,58),150)
        self.assertEqual(source_scale(box,{1:dict(scale1=200,y1=100,scale2=100,y2=0)},99),199)
        with self.assertRaises(ValueError):decode_scales(b'x')

    def test_box_layout_and_scale_slot_preserved(self):
        b=decode_boxes(pack('<H8hBBH',1,-1,2,8,2,8,9,-1,9,2,64,32770))
        self.assertEqual(b,[dict(id=0,corners=[[-1,2],[8,2],[8,9],[-1,9]],plane=2,flags=64,scale_raw=32770)])
        for x in (b'',b'\1\0',b'\0\0x'):
            with self.assertRaises(ValueError):decode_boxes(x)

    def test_unknown_plane_and_unequal_scale_fail(self):
        s=dict(manifest=dict(dimensions=[8,8]),background=bytes(64),masks={})
        pose=[0,0,2,255,255,180,1]+[65535]*16
        with self.assertRaisesRegex(ValueError,'depth'):compose_actor(s,None,pose,(0,0,8,8))
        pose[2]=0;pose[4]=1
        with self.assertRaisesRegex(ValueError,'scaling'):compose_actor(s,None,pose,(0,0,8,8))

    def test_mask_restores_source_pixel_and_negative_control_exposes_cel(self):
        cel=SimpleNamespace(rel_x=0,rel_y=0,width=1,height=1,slots=b'\1',move_x=0,move_y=0)
        costume=SimpleNamespace(force_right=False,palette=b'\0\7',limb=lambda n,p:None if p==65535 else (0,cel))
        scene=dict(manifest=dict(dimensions=[8,8]),background=bytes([3])*64,masks={2:bytes([255])+bytes(63)})
        pose=[0,0,2,255,255,180,1]+[0]+[65535]*15
        self.assertEqual(compose_actor(scene,costume,pose,(0,0,8,8))[0],3)
        self.assertEqual(compose_actor(scene,costume,pose,(0,0,8,8),mask_enabled=False)[0],7)


    def test_multi_actor_depth_restores_previous_composite_not_bare_background(self):
        cel=SimpleNamespace(rel_x=0,rel_y=0,width=1,height=1,slots=b'\1',
                            move_x=0,move_y=0)
        costume=SimpleNamespace(force_right=False,colors=16,palette=b'\0\7'+bytes(14),
                                limb=lambda n,p:None if p==65535 else (0,cel))
        scene=dict(manifest=dict(dimensions=[8,8]),background=bytes([3])*64,
                   masks={2:bytes([255])+bytes(63)})
        def draw(actor,plane,color):
            palette=[0]*32
            palette[1]=color
            return dict(id=actor,screen_x=0,draw_y=0,plane=plane,scales=[255,255],
                        facing=180,costume=20,logical_frame=0,stopped=0,
                        cursors=[0]+[65535]*15,palette_override=palette)
        first=draw(7,0,7)
        second=draw(8,2,9)
        masked=compose_actor_layers(scene,{20:costume},[first,second],(0,0,8,8))
        bare=compose_actor_layers(scene,{20:costume},[first,second],(0,0,8,8),
                                  mask_enabled=False)
        self.assertEqual(masked[0],7)
        self.assertEqual(bare[0],9)
        self.assertEqual(masked[1],3)

    def test_live_palette_override_and_stopped_limb_are_explicit(self):
        cel=SimpleNamespace(rel_x=0,rel_y=0,width=1,height=1,slots=b'\1',
                            move_x=0,move_y=0)
        costume=SimpleNamespace(force_right=False,colors=16,palette=b'\0\7'+bytes(14),
                                limb=lambda n,p:None if p==65535 else (0,cel))
        scene=dict(manifest=dict(dimensions=[8,8]),background=bytes([3])*64,masks={})
        record=dict(id=7,screen_x=0,draw_y=0,plane=0,scales=[255,255],facing=180,
                    costume=20,stopped=0,cursors=[0]+[65535]*15,
                    palette_override=[0,12]+[0]*30)
        self.assertEqual(compose_actor_layers(scene,{20:costume},[record],(0,0,8,8))[0],12)
        record["stopped"]=1
        self.assertEqual(compose_actor_layers(scene,{20:costume},[record],(0,0,8,8))[0],3)
        record["palette_override"]=[999]*32
        with self.assertRaisesRegex(ValueError,"palette override"):
            compose_actor_layers(scene,{20:costume},[record],(0,0,8,8))


    def test_actor_palette_255_falls_back_to_original_cost_slots(self):
        cel=SimpleNamespace(rel_x=0,rel_y=0,width=1,height=1,slots=b'\1',
                            move_x=0,move_y=0)
        costume=SimpleNamespace(force_right=False,colors=16,
                                palette=b'\0\7'+bytes(14),
                                limb=lambda n,p:None if p==65535 else (0,cel))
        scene=dict(manifest=dict(dimensions=[8,8]),background=bytes([3])*64,
                   masks={})
        actor=dict(id=7,screen_x=0,draw_y=0,plane=0,scales=[255,255],
                   facing=180,costume=20,logical_frame=12,stopped=0,
                   cursors=[0]+[65535]*15,palette_override=[255]*32)
        self.assertEqual(
            compose_actor_layers(scene,{20:costume},[actor],(0,0,8,8))[0],7)
        actor["palette_override"][1]=12
        self.assertEqual(
            compose_actor_layers(scene,{20:costume},[actor],(0,0,8,8))[0],12)
        actor["palette_override"][1]=255
        actor["stopped"]=1
        self.assertEqual(
            compose_actor_layers(scene,{20:costume},[actor],(0,0,8,8))[0],3)
