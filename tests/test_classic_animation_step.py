"""Synthetic source-level step controls plus raw-channel regression boundaries."""
from copy import deepcopy
from hashlib import sha256
import json
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch
import unittest

from scummbucket.classic_animation_step import parse_animation_step,predict_animation_step,compare_animation_step
from test_classic_animation import costume
from tools.audit_animation_steps import audit
from tools.prepare_animation_step_capture import transform


def observed(phase='before',**changes):
    row = dict(phase=phase,id=1,costume=1,progress=0,speed=0,stopped=0,
               animation_counter=0,sound_counter=0,cursors=[0]+[65535]*15,
               starts=[0]+[65535]*15,ends=[3]+[65535]*15,limb_frames=[4]+[65535]*15)
    row.update(changes)
    values = [row[k] for k in ('id','costume','progress','speed','stopped','animation_counter','sound_counter')]
    for limb in zip(row['cursors'],row['starts'],row['ends'],row['limb_frames']):
        values.extend(limb)
    return 'anim_step '+phase+' '+' '.join(map(str,values))


class AnimationStepTests(unittest.TestCase):
    def setUp(self):
        self.costume = costume([1,0x78,0x7c,2],{})

    def test_events_native_counter_widths_and_nonmutating_input(self):
        before = parse_animation_step(observed(animation_counter=65535,sound_counter=255))
        saved = deepcopy(before)
        after,operation = predict_animation_step(self.costume,before)
        self.assertEqual(after['cursors'][0],3)
        self.assertEqual((after['animation_counter'],after['sound_counter']),(0,0))
        self.assertTrue(operation['animation_updated'])
        self.assertTrue(operation['cel_changed'])
        self.assertEqual(before,saved)

    def test_progress_threshold_and_byte_wrap_do_not_invent_extra_updates(self):
        for progress,speed,expected,updated in ((0,3,1,False),(2,3,0,True),(255,1,0,False),(255,0,0,True)):
            with self.subTest(progress=progress,speed=speed):
                after,operation = predict_animation_step(self.costume,parse_animation_step(observed(progress=progress,speed=speed)))
                self.assertEqual(after['progress'],expected)
                self.assertEqual(operation['animation_updated'],updated)
                self.assertEqual(after['cursors'][0],3 if updated else 0)

    def test_one_shot_terminal_and_stopped_state_follow_source_cursor_rules(self):
        c = costume([1,2,3],{})
        before = parse_animation_step(observed(stopped=1,cursors=[32770]+[65535]*15,ends=[2]+[65535]*15))
        after,operation = predict_animation_step(c,before)
        self.assertEqual(after['cursors'][0],32770)
        self.assertFalse(operation['cel_changed'])
        self.assertEqual(after['stopped'],1)

    def test_bad_phase_width_ranges_and_identity_are_rejected(self):
        for line in (observed()+' 1',observed(speed=256),observed(stopped=-1),observed().replace('before','middle',1)):
            with self.subTest(line=line[:30]):
                with self.assertRaises(ValueError):
                    parse_animation_step(line)
        with self.assertRaisesRegex(ValueError,'identity'):
            compare_animation_step(self.costume,parse_animation_step(observed()),parse_animation_step(observed('after',id=2)))

    def test_overlay_brackets_existing_update_without_forcing_one(self):
        source = 'void Actor::animateCostume() {\n\tif (_costume == 0)\n\t\treturn;\n\t_animProgress++;\n}\n'
        result = transform(source)
        self.assertEqual(result.count('_animProgress++;'),1)
        self.assertLess(result.index('sbAnimationSnapshot("before")'),result.index('_animProgress++;'))
        self.assertGreater(result.index('sbAnimationSnapshot("after")'),result.index('_animProgress++;'))
        self.assertNotIn('increaseAnims(',result)
        with self.assertRaises(ValueError):
            transform(source+source)


class AnimationAuditTests(unittest.TestCase):
    def setUp(self):
        self.tmp = TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.costume = costume([1,0x78,0x7c,2],{})

    def write_capture(self,after_cursor=3,paired=True):
        body = observed()+'\n'
        if paired:
            body += observed('after',cursors=[after_cursor]+[65535]*15,animation_counter=1,sound_counter=1)+'\n'
        raw = ('R23E1 1 1 6 6 0 1 1 0 0\nSynthetic\nscene 7 1\n'+body+'DATA\n').encode()
        raw += bytes(3072+2*46080+5760+64000)
        (self.root/'engine-001.bin').write_bytes(raw)
        report = dict(schema='scummbucket-cross-room-indexed-evidence/1',frames=[dict(
            indexed_frame=1,room=7,tick=1,raw_sha256=sha256(raw).hexdigest(),front_sha256=sha256(bytes(46080)).hexdigest())])
        (self.root/'indexed.json').write_text(json.dumps(report))

    def run_audit(self):
        with (patch('tools.audit_animation_steps.inspect',return_value=dict(status='success',sources=[])),
              patch('tools.audit_animation_steps.costumes_from_archive',return_value={1:self.costume})):
            return audit('synthetic',self.root,self.root/'indexed.json')

    def test_matches_original_after_state_and_keeps_wrong_prediction_partial(self):
        self.write_capture()
        result = self.run_audit()
        self.assertEqual(result['status'],'observed_calls_exact')
        self.assertEqual(result['summary']['sound_counter_changes'],1)
        self.write_capture(after_cursor=2)
        result = self.run_audit()
        self.assertEqual(result['status'],'PARTIAL')
        self.assertEqual(result['summary']['mismatched_calls'],1)
        self.assertIn('cursors',result['findings'][0]['differences'])

    def test_missing_channel_and_tampered_raw_fail_closed(self):
        self.write_capture(paired=False)
        with self.assertRaisesRegex(ValueError,'unpaired'):
            self.run_audit()
        self.write_capture()
        (self.root/'engine-001.bin').write_bytes(b'changed')
        with self.assertRaisesRegex(ValueError,'changed'):
            self.run_audit()


if __name__ == '__main__':
    unittest.main()
