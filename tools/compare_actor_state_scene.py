"""Compare observed pre-redraw scene candidates against original indexed fronts.

Uses only each frame's own state records. No old-pose persistence, cursor
interpolation, RGB fitting or missing-state replacement is performed.
"""
from collections import Counter
from copy import deepcopy
from hashlib import sha256
import argparse
import json
from pathlib import Path

from scummbucket.actor_capture_state import parse_actor_state_record, state_as_composition_candidate
from scummbucket.observed_scene_replay import observed_frame_packet, replay_observed_frame, compare_native_frame
from scummbucket.scene_source import load_scene
from tools.audit_actor_state_capture import audit
from tools.compare_cross_room_scene import costumes_from_archive
from tools.compare_room23_frames import engine
from tools.replay_observed_scene import read_observed_packet


def compare(game,capture,indexed_report,room_id):
    capture,indexed_report = Path(capture),Path(indexed_report)
    channel = audit(capture,indexed_report)
    if (channel['status'] != 'state_channel_structurally_verified' or
            channel['summary'].get('states_changed_during_prepare',0)):
        raise ValueError('Complete phase-consistent actor state channel required')
    source = indexed_report.read_bytes()
    rows = [r for r in json.loads(source)['frames'] if r['room']==room_id]
    if not rows or len(rows)>1000:
        raise ValueError('Missing/excessive observed room samples')
    scene = load_scene(game,room_id)
    needed = set()
    for row in rows:
        raw = (capture/f"engine-{row['indexed_frame']:03}.bin").read_bytes()
        if sha256(raw).hexdigest() != row['raw_sha256']:
            raise ValueError('Original raw record changed after channel audit')
        meta,*_ = engine(raw,row['indexed_frame'])
        needed.update(parse_actor_state_record(s)['costume'] for s in meta['state'] if s.startswith('state_actor '))
    costumes = costumes_from_archive(game,needed,expected_sources=scene['manifest']['sources'])
    findings,packets = [],[]
    totals = Counter()
    variants = {}
    palette_hashes = set()
    for row in rows:
        raw = (capture/f"engine-{row['indexed_frame']:03}.bin").read_bytes()
        draw_packet,background,front,palette = read_observed_packet(raw,row,scene)
        meta,*_ = engine(raw,row['indexed_frame'])
        states = [parse_actor_state_record(s) for s in meta['state'] if s.startswith('state_actor ')]
        actors = [state_as_composition_candidate(s) for s in states]
        packet = observed_frame_packet(frame_id=row['indexed_frame'],tick=row['tick'],
                                       room_id=room_id,viewport=draw_packet['viewport'],
                                       actors=actors,palette=palette,raw_sha256=row['raw_sha256'])
        packet['actor_evidence_phase'] = 'current_frame_pre_redraw_state; not actual draw operations'
        predicted = replay_observed_frame(scene,costumes,packet)
        draw_only = replay_observed_frame(scene,costumes,draw_packet)
        unmasked = replay_observed_frame(scene,costumes,packet,mask_enabled=False)
        shifted = deepcopy(packet)
        for draw in shifted['events'][1]['draw_order']:
            draw['row']['screen_x'] += 1
        moved = replay_observed_frame(scene,costumes,shifted)
        result = compare_native_frame(predicted,front,palette)
        left,top,width,height = packet['viewport']
        sw = scene['manifest']['dimensions'][0]
        crop = b''.join(scene['background'][(top+y)*sw+left:(top+y)*sw+left+width] for y in range(height))
        record = dict(indexed_frame=row['indexed_frame'],tick=row['tick'],viewport=packet['viewport'],
                      raw_sha256=row['raw_sha256'],actor_order=[a['id'] for a in actors],
                      actual_draw_order=[a['id'] for a in row['actors']],**result,
                      draw_only_errors=compare_native_frame(draw_only,front,palette)['indexed_errors'],
                      mask_disabled_errors=compare_native_frame(unmasked,front,palette)['indexed_errors'],
                      actors_shifted_right_errors=compare_native_frame(moved,front,palette)['indexed_errors'],
                      source_background_errors=sum(a!=b for a,b in zip(crop,background)))
        findings.append(record)
        packets.append(packet)
        totals.update({k:record[k] for k in ('indexed_errors','palette_byte_errors','draw_only_errors',
                      'mask_disabled_errors','actors_shifted_right_errors','source_background_errors')})
        for state in states:
            variants.setdefault(state['id'],set()).add(tuple(state['cursors']))
        palette_hashes.add(predicted['palette_sha256'])
    result = dict(schema='scummbucket-observed-event-replay-comparison/1',
                  status='observed_samples_exact' if not any(totals[k] for k in
                         ('indexed_errors','palette_byte_errors','source_background_errors')) else 'PARTIAL',
                  room_id=room_id,samples=len(rows),exact_frames=sum(r['indexed_errors']==0 for r in findings),
                  indexed_pixel_observations=len(rows)*46080,**dict(totals),
                  original_archives=scene['manifest']['sources'],room_sha256=scene['manifest']['room_sha256'],
                  indexed_report_sha256=sha256(source).hexdigest(),
                  evidence_mode='original per-frame pre-redraw state + archive-derived assets',
                  actor_state_channel_summary=channel['summary'],
                  cursor_variants={str(k):len(v) for k,v in variants.items()},
                  observed_palette_variants=len(palette_hashes),
                  palette_evidence='observed snapshots; cycle execution not independently predicted',
                  timing='observed tick identities only; native durations not inferred',
                  unsupported=['automatic object state/order','shadow/back-buffer actor drawing',
                               'unobserved actors','native script execution','SDL display-phase equality'],
                  frames=findings)
    sequence = dict(schema='scummbucket-observed-scene-sequence/1',room_id=room_id,
                    source_room_sha256=result['room_sha256'],
                    indexed_report_sha256=result['indexed_report_sha256'],frames=packets,
                    actor_evidence_phase='current-frame pre-redraw observed states')
    return result,sequence,costumes


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    for name in ('game','capture','indexed-report','output'):
        p.add_argument('--'+name,type=Path,required=True)
    p.add_argument('--room',type=int,default=7)
    p.add_argument('--package',type=Path)
    args = p.parse_args()
    if args.output.exists() or args.output.is_symlink() or args.package is not None and args.package.exists():
        p.error('Refusing existing output')
    result,sequence,costumes = compare(args.game,args.capture,args.indexed_report,args.room)
    with args.output.open('x',encoding='utf-8') as out:
        json.dump(result,out,indent=2)
    print(json.dumps({k:v for k,v in result.items() if k not in ('frames','original_archives')},indent=2))
    if args.package is not None:
        from scummbucket.observed_scene_package import export_replay_package
        print(json.dumps(export_replay_package(args.game,args.package,result,sequence,costumes),indent=2))
    raise SystemExit(0 if result['status']=='observed_samples_exact' else 2)
