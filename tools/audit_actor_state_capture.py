"""Read-only audit of pre-redraw actor-state evidence; no rendering or inference."""
import argparse
from collections import Counter
from hashlib import sha256
import json
from pathlib import Path

from scummbucket.actor_capture_state import parse_actor_state_record, compare_state_to_draw
from tools.compare_room23_frames import engine
from tools.verify_cross_room_capture import parse_draw_actor


def audit(capture, indexed_report):
    capture = Path(capture)
    report_bytes = Path(indexed_report).read_bytes()
    reference = json.loads(report_bytes)
    if reference.get('schema') != 'scummbucket-cross-room-indexed-evidence/1':
        raise ValueError('Expected original indexed evidence report')
    frames = reference.get('frames')
    if not isinstance(frames, list) or not 0 < len(frames) <= 2400:
        raise ValueError('Missing/excessive indexed evidence frames')
    counts, findings = Counter(), []
    previous = 0
    for row in frames:
        number = row['indexed_frame']
        if type(number) is not int or number <= previous:
            raise ValueError('Indexed evidence order regression')
        previous = number
        raw = (capture/f'engine-{number:03}.bin').read_bytes()
        if sha256(raw).hexdigest() != row['raw_sha256']:
            raise ValueError('Original raw frame changed')
        meta, _, _, front, _ = engine(raw, number)
        if sha256(front).hexdigest() != row['front_sha256']:
            raise ValueError('Original frontbuffer hash mismatch')
        identities = [s for s in meta['state'] if s.startswith('scene ')]
        if identities != [f"scene {row['room']} {row['tick']}"]:
            raise ValueError('Raw scene/tick identity disagrees with indexed report')
        states = [parse_actor_state_record(s) for s in meta['state'] if s.startswith('state_actor ')]
        draws = [parse_draw_actor(s) for s in meta['state'] if s.startswith('draw_actor ')]
        if draws != row['actors']:
            raise ValueError('Original ordered actor draw records changed')
        counts['frames'] += 1
        if not states:
            counts['frames_missing_state_channel'] += 1
            findings.append(dict(indexed_frame=number, status='MISSING_STATE_CHANNEL'))
            continue
        if len({s['id'] for s in states}) != len(states) or len({d['id'] for d in draws}) != len(draws):
            raise ValueError('Duplicate actor state/draw observation')
        by_actor = {d['id']: d for d in draws}
        if not set(by_actor) <= {s['id'] for s in states}:
            raise ValueError('Draw record lacks a preceding actor state')
        # Check source-defined state-before-draw association, not just ID sets.
        pending = None
        for line in meta['state']:
            if line.startswith('state_actor '):
                pending = int(line.split()[1])
            elif line.startswith('draw_actor '):
                if pending != int(line.split()[1]):
                    raise ValueError('Draw does not follow its own pre-redraw state')
                pending = None
        samples = []
        for state in states:
            if state['room'] != row['room']:
                raise ValueError('Actor state belongs to another room')
            draw = by_actor.get(state['id'])
            # For this pinned v5 hook, zero costume or false redraw returns.
            should_draw = bool(state['costume'] and state['need_redraw'])
            if should_draw != (draw is not None):
                raise ValueError('Actor redraw gate and actual draw evidence contradict')
            differences = compare_state_to_draw(state, draw) if draw else None
            counts['actor_states'] += 1
            counts['states_with_draw' if draw else 'states_without_draw'] += 1
            if differences:
                counts['states_changed_during_prepare'] += 1
            samples.append(dict(actor=state['id'], visible=state['visible'],
                                need_redraw=state['need_redraw'], has_actual_draw=draw is not None,
                                preparation_differences=differences))
        findings.append(dict(indexed_frame=number, tick=row['tick'],
                             actor_process_order=[s['id'] for s in states], actors=samples))
    missing = counts['frames_missing_state_channel']
    return dict(schema='scummbucket-actor-state-channel-audit/1',
                status='MISSING_STATE_CHANNEL' if missing == len(frames) else
                       'PARTIAL_STATE_CHANNEL' if missing else 'state_channel_structurally_verified',
                summary=dict(counts), frames=findings,
                indexed_report_sha256=sha256(report_bytes).hexdigest(),
                full_visible_scene_verified=False, native_timing_verified=False,
                state_evidence_phase='before redraw gate and renderer preparation',
                limitation='State rows are not draw operations or proof of retained framebuffer pixels')


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--capture', type=Path, required=True)
    p.add_argument('--indexed-report', type=Path, required=True)
    p.add_argument('--output', type=Path, required=True)
    args = p.parse_args()
    if args.output.exists() or args.output.is_symlink():
        p.error('Refusing existing output')
    result = audit(args.capture, args.indexed_report)
    with args.output.open('x', encoding='utf-8') as out:
        json.dump(result, out, indent=2)
    print(json.dumps({k:v for k,v in result.items() if k != 'frames'}, indent=2))
    return 0 if result['status'] == 'state_channel_structurally_verified' else 2


if __name__ == '__main__':
    raise SystemExit(main())
