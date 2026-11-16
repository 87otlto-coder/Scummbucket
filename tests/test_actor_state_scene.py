"""Synthetic raw-native reference; archive loading alone is substituted."""
from hashlib import sha256
import json
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch
import unittest

from test_actor_capture_state import snapshot
from test_classic_costume import sample_32
from tools.index_actor_state_capture import index_capture
from tools.compare_actor_state_scene import compare


class CompleteActorStateTests(unittest.TestCase):
    def setUp(self):
        self.tmp = TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.capture = Path(self.tmp.name)
        exe = self.capture/'fake.exe'
        exe.write_bytes(b'never executed synthetic build')
        self.exe = exe
        (self.capture/'run.json').write_text(json.dumps(dict(schema='scummbucket-actor-state-capture/1',
            capture_mode='actor_state',command=[str(exe)],exe_sha256=sha256(exe.read_bytes()).hexdigest())))
        (self.capture/'exit.json').write_text('{"returncode":0}')
        for marker in ('capture.enabled','doorway.enabled'):
            (self.capture/marker).touch()
        self.front = bytearray([9])*46080
        # Independent hand-built raster for sample_32's 2x3 cel at (3,2).
        for y in range(2,5):
            self.front[y*320+3:y*320+5] = bytes([42,77])
        self.draw = 'draw_actor '+' '.join(map(str,
            [1,3,4,0,255,255,180,1,1,0]+[0]+[65535]*15+[255]*32))
        self.write_frame(1,True)
        self.write_frame(2,False)
        self.index = self.capture/'indexed.json'
        self.index.write_text(json.dumps(index_capture(self.capture)))
        self.scene = dict(manifest=dict(room_id=7,dimensions=[320,144],sources=[],room_sha256='a'*64),
                          background=bytes([9])*46080,palette=bytes(768),masks={})

    def write_frame(self,n,draw):
        state = snapshot(world_x=3,world_y=4,screen_x=3,draw_y=4,need_redraw=int(draw))
        header = f'R23E1 {n} 100 6 6 0 1 1 0 0\nSynthetic\nscene 7 {n}\n'
        header += 'camera 160 72 0 0 320 144 320 144\n'+state+'\n'
        if draw:
            header += self.draw+'\n'
        raw = (header+'DATA\n').encode()+bytes(3072)+bytes([9])*46080+bytes(self.front)
        raw += bytes(5760)+bytes(self.front)+bytes(17920)
        (self.capture/f'engine-{n:03}.bin').write_bytes(raw)

    def test_current_state_reconstructs_nonredraw_reference_without_cached_pose(self):
        with (patch('tools.compare_actor_state_scene.load_scene',return_value=self.scene),
              patch('tools.compare_actor_state_scene.costumes_from_archive',return_value={1:sample_32()})):
            result,sequence,_ = compare('synthetic',self.capture,self.index,7)
        self.assertEqual(result['status'],'observed_samples_exact')
        self.assertEqual(result['exact_frames'],2)
        self.assertEqual(result['draw_only_errors'],6)
        self.assertGreater(result['actors_shifted_right_errors'],0)
        self.assertEqual(len(sequence['frames'][1]['events'][1]['draw_order']),1)
        self.assertEqual(sequence['frames'][1]['actor_evidence_phase'],
                         'current_frame_pre_redraw_state; not actual draw operations')

    def test_index_rejects_changed_executable_and_failed_exit(self):
        self.exe.write_bytes(b'changed')
        with self.assertRaisesRegex(ValueError,'executable changed'):
            index_capture(self.capture)
        (self.capture/'exit.json').write_text('{"returncode":1}')
        with self.assertRaisesRegex(ValueError,'close successfully'):
            index_capture(self.capture)

    def test_comparison_rejects_tampered_original_without_fallback(self):
        (self.capture/'engine-002.bin').write_bytes(b'changed')
        with self.assertRaisesRegex(ValueError,'changed'):
            compare('synthetic',self.capture,self.index,7)

    def test_index_does_not_silently_accept_an_old_draw_only_channel(self):
        p = self.capture/'engine-001.bin'
        raw = p.read_bytes()
        state_line = snapshot(world_x=3,world_y=4,screen_x=3,draw_y=4,need_redraw=1)+'\n'
        p.write_bytes(raw.replace(state_line.encode(),b''))
        p = self.capture/'engine-002.bin'
        state_line = snapshot(world_x=3,world_y=4,screen_x=3,draw_y=4,need_redraw=0)+'\n'
        p.write_bytes(p.read_bytes().replace(state_line.encode(),b''))
        with self.assertRaisesRegex(ValueError,'No actor-state channel'):
            index_capture(self.capture)


if __name__ == '__main__':
    unittest.main()
