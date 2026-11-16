"""Compare archive COST execution with paired original before/after call records."""
from collections import Counter
from hashlib import sha256
import argparse
import json
from pathlib import Path

from scummbucket.classic_animation_step import parse_animation_step,compare_animation_step
from tools.compare_cross_room_scene import costumes_from_archive
from tools.compare_room23_frames import engine
from tools.run_room23_frames import ARCHIVES
from scummbucket.inspector import inspect


def audit(game,capture,indexed_report):
    capture,indexed_report = Path(capture),Path(indexed_report)
    report_bytes = indexed_report.read_bytes()
    evidence = json.loads(report_bytes)
    if evidence.get('schema')!='scummbucket-cross-room-indexed-evidence/1':
        raise ValueError('Expected raw indexed evidence')
    inventory = inspect(game)
    if inventory['status']!='success':
        raise ValueError('Original source inspection failed')
    frames = evidence['frames']
    if not frames or len(frames)>2400:
        raise ValueError('Missing/excessive animation frames')
    calls = []
    for row in frames:
        number = row['indexed_frame']
        raw = (capture/f'engine-{number:03}.bin').read_bytes()
        if sha256(raw).hexdigest()!=row['raw_sha256']:
            raise ValueError('Original animation raw record changed')
        meta,_,_,front,_ = engine(raw,number)
        if (sha256(front).hexdigest()!=row['front_sha256'] or
                [s for s in meta['state'] if s.startswith('scene ')] != [f"scene {row['room']} {row['tick']}"]):
            raise ValueError('Animation raw frame identity mismatch')
        records = [parse_animation_step(s) for s in meta['state'] if s.startswith('anim_step ')]
        if not records or len(records)%2:
            raise ValueError('Missing or unpaired animation call channel')
        for before,after in zip(records[::2],records[1::2]):
            if (before['phase'],after['phase'])!=('before','after') or before['id']!=after['id']:
                raise ValueError('Animation phase/order contradiction')
            calls.append((row,before,after))
    costumes = costumes_from_archive(game,{b['costume'] for _,b,_ in calls},expected_sources=inventory['sources'])
    totals,actors,speeds = Counter(),Counter(),Counter()
    variants = {}
    findings = []
    for row,before,after in calls:
        result = dict(indexed_frame=row['indexed_frame'],tick=row['tick'],actor_id=before['id'],
                      costume=before['costume'],status='failed')
        try:
            differences,operation = compare_animation_step(costumes[before['costume']],before,after)
            result.update(status='exact_call_match' if not differences else 'MODEL_MISMATCH',
                          differences=differences,**operation)
            totals['matched_calls' if not differences else 'mismatched_calls']+=1
            totals['limb_cursor_comparisons']+=16
            totals['animation_updates']+=int(operation['animation_updated'])
            totals['cel_changes']+=int(operation['cel_changed'])
            totals['sound_counter_changes']+=int(before['sound_counter']!=after['sound_counter'])
            totals['animation_counter_changes']+=int(before['animation_counter']!=after['animation_counter'])
        except (ValueError,IndexError) as exc:
            result.update(code='ANIMATION_MODEL_ERROR',message=str(exc))
            totals['model_errors']+=1
        actors[str(before['id'])]+=1
        speeds[str(before['speed'])]+=1
        variants.setdefault(before['id'],set()).add(tuple(before['cursors']))
        findings.append(result)
    return dict(schema='scummbucket-native-animation-step-audit/1',
                status='observed_calls_exact' if not totals['mismatched_calls'] and not totals['model_errors'] else 'PARTIAL',
                samples=len(frames),calls=len(calls),summary=dict(totals),actor_calls=dict(actors),
                observed_speeds=dict(speeds),cursor_variants={str(k):len(v) for k,v in variants.items()},
                indexed_report_sha256=sha256(report_bytes).hexdigest(),original_archives=inventory['sources'],
                basis='actual per-call before state + archive commands; independent original after state',
                limitations=['observed call states only; no automatic script initialization',
                             'unobserved speed/event/stop-resume modes remain unverified',
                             'no wall-clock or SDL presentation timing claim'],findings=findings)


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    for name in ('game','capture','indexed-report','output'):
        p.add_argument('--'+name,type=Path,required=True)
    args = p.parse_args()
    if args.output.exists() or args.output.is_symlink():
        p.error('Refusing existing output')
    result = audit(args.game,args.capture,args.indexed_report)
    with args.output.open('x',encoding='utf-8') as out:
        json.dump(result,out,indent=2)
    print(json.dumps({k:v for k,v in result.items() if k not in ('findings','original_archives')},indent=2))
    raise SystemExit(0 if result['status']=='observed_calls_exact' else 2)
