"""Synthetic channel contracts; no new original runtime capture is claimed."""
from hashlib import sha256
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from scummbucket.actor_capture_state import (STATE_FIELDS, parse_actor_state_record,
    compare_state_to_draw, state_as_composition_candidate)
from tools.prepare_actor_state_capture import STATE_FIELDS as OVERLAY_FIELDS
from tools.audit_actor_state_capture import audit
from tools.verify_cross_room_capture import parse_draw_actor


def snapshot(**changes):
    values = dict(zip(STATE_FIELDS, [
        1, 0, 0, 0, 0, 0, 7, 1, 1, 0, 255, 255, 180, 1, 1, 0,
        0, 0, 0, 0, 1, 0, 0, 0, 0, 2147483647, 0]))
    values.update(changes)
    return 'state_actor '+' '.join(map(str, [values[k] for k in STATE_FIELDS]+[0]+[65535]*15+[255]*32))


DRAW = 'draw_actor '+' '.join(map(str, [1, 0, 0, 0, 255, 255, 180, 1, 1, 0]+[0]+[65535]*15+[255]*32))


class ActorStateParserTests(unittest.TestCase):
    def test_candidate_uses_current_state_and_copies_mutable_fields(self):
        state = parse_actor_state_record(snapshot(need_redraw=0))
        candidate = state_as_composition_candidate(state)
        self.assertEqual(candidate['cursors'],state['cursors'])
        candidate['cursors'][0] = 99
        self.assertEqual(state['cursors'][0],0)
        self.assertEqual(candidate['screen_x'],state['screen_x'])

    def test_candidate_rejects_unmodeled_actor_modes(self):
        for fields in (dict(visible=0),dict(draw_to_back=1),dict(shadow_mode=1),dict(scale_x=128)):
            with self.subTest(fields=fields):
                with self.assertRaises(ValueError):
                    state_as_composition_candidate(parse_actor_state_record(snapshot(**fields)))

    def test_exact_field_layout_and_distinct_state_semantics(self):
        self.assertEqual(STATE_FIELDS, OVERLAY_FIELDS)
        state = parse_actor_state_record(snapshot())
        self.assertEqual(state['top'], 2147483647)
        self.assertEqual(len(state['cursors']), 16)
        self.assertEqual(state['palette_override'], [255]*32)
        self.assertEqual(compare_state_to_draw(state, parse_draw_actor(DRAW)), {})

    def test_renderer_preparation_difference_is_reported_without_pose_replacement(self):
        state = parse_actor_state_record(snapshot(scale_x=200))
        differences = compare_state_to_draw(state, parse_draw_actor(DRAW))
        self.assertEqual(differences, {'scales': {'before_prepare':[200,255], 'actual_draw':[255,255]}})
        self.assertEqual(state['scale_x'], 200)

    def test_bad_width_integer_range_and_boolean_are_rejected(self):
        lines = [snapshot()+' 1', snapshot().replace('state_actor','draw_actor'),
                 snapshot(visible=2), snapshot(scale_x=-1), snapshot(facing=45),
                 snapshot(id=0), snapshot(stopped=65536), snapshot(top=2**31),
                 snapshot().replace('state_actor 1 ', 'state_actor x ', 1)]
        for line in lines:
            with self.subTest(line=line[:40]):
                with self.assertRaises(ValueError):
                    parse_actor_state_record(line)

    def test_wrong_actor_cannot_be_associated_by_fitted_geometry(self):
        with self.assertRaisesRegex(ValueError, 'identity'):
            compare_state_to_draw(parse_actor_state_record(snapshot(id=2)), parse_draw_actor(DRAW))


class ActorStateAuditTests(unittest.TestCase):
    def setUp(self):
        self.tmp = TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.capture = Path(self.tmp.name)
        self.report = self.capture/'indexed.json'

    def write_capture(self, lines):
        front = bytes(46080)
        raw = ('R23E1 1 100 6 6 0 1 1 0 0\nSynthetic\nscene 7 20\n'+'\n'.join(lines)+'\nDATA\n').encode()
        raw += bytes(3072)+front+front+bytes(5760)+bytes(64000)
        (self.capture/'engine-001.bin').write_bytes(raw)
        row = dict(indexed_frame=1, room=7, tick=20, raw_sha256=sha256(raw).hexdigest(),
                   front_sha256=sha256(front).hexdigest(),
                   actors=[parse_draw_actor(s) for s in lines if s.startswith('draw_actor ')])
        self.report.write_text(json.dumps(dict(schema='scummbucket-cross-room-indexed-evidence/1', frames=[row])))

    def test_observed_redraw_and_nonredraw_are_separate_counts(self):
        self.write_capture([snapshot(), DRAW, snapshot(id=11, need_redraw=0)])
        result = audit(self.capture, self.report)
        self.assertEqual(result['status'], 'state_channel_structurally_verified')
        self.assertEqual(result['summary']['states_with_draw'], 1)
        self.assertEqual(result['summary']['states_without_draw'], 1)
        self.assertFalse(result['full_visible_scene_verified'])

    def test_old_capture_without_new_channel_cannot_pass_as_full_state(self):
        self.write_capture([DRAW])
        result = audit(self.capture, self.report)
        self.assertEqual(result['status'], 'MISSING_STATE_CHANNEL')

    def test_source_gate_contradiction_wrong_order_and_duplicate_state_fail(self):
        for lines in ([snapshot(need_redraw=0), DRAW],
                      [snapshot(), snapshot(id=11, need_redraw=0), DRAW],
                      [snapshot(), DRAW, snapshot()]):
            with self.subTest(lines=len(lines)):
                self.write_capture(lines)
                with self.assertRaises(ValueError):
                    audit(self.capture, self.report)

    def test_raw_hash_tampering_is_rejected(self):
        self.write_capture([snapshot(), DRAW])
        (self.capture/'engine-001.bin').write_bytes(b'changed')
        with self.assertRaisesRegex(ValueError, 'changed'):
            audit(self.capture, self.report)


if __name__ == '__main__':
    unittest.main()
