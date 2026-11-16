"""Index closed native actor-state captures without asserting scene fidelity."""
from hashlib import sha256
import argparse
import json
from pathlib import Path

from scummbucket.actor_capture_state import parse_actor_state_record
from tools.compare_room23_frames import engine
from tools.verify_cross_room_capture import ENGINE_RE, indexed_files, parse_draw_actor


def index_capture(capture):
    capture = Path(capture)
    run_bytes = (capture/'run.json').read_bytes()
    run = json.loads(run_bytes)
    if run.get('schema') != 'scummbucket-actor-state-capture/1' or run.get('capture_mode') != 'actor_state':
        raise ValueError('Not an actor-state capture')
    if json.loads((capture/'exit.json').read_text())['returncode'] != 0:
        raise ValueError('Native recorder did not close successfully')
    if any(not (capture/name).is_file() for name in ('capture.enabled','doorway.enabled')):
        raise ValueError('Capture markers missing')
    exe = Path(run['command'][0])
    if sha256(exe.read_bytes()).hexdigest() != run['exe_sha256']:
        raise ValueError('Recorded native executable changed')
    rows = []
    previous_tick = -1
    for number, path in indexed_files(capture, ENGINE_RE):
        if number > 2400:
            raise ValueError('Indexed frame budget exceeded')
        raw = path.read_bytes()
        meta, palettes, background, front, backend = engine(raw,number)
        identities = [s.split() for s in meta['state'] if s.startswith('scene ')]
        if len(identities) != 1 or len(identities[0]) != 3:
            raise ValueError('Missing/ambiguous scene identity')
        room, tick = map(int,identities[0][1:])
        if room not in (7,12) or tick < previous_tick:
            raise ValueError('Unsupported room or tick regression')
        previous_tick = tick
        if backend[meta['top']*320:(meta['top']+144)*320] != front:
            raise ValueError('Front/backend indexed crop mismatch')
        states = [parse_actor_state_record(s) for s in meta['state'] if s.startswith('state_actor ')]
        draws = [parse_draw_actor(s) for s in meta['state'] if s.startswith('draw_actor ')]
        rows.append(dict(indexed_frame=number,room=room,tick=tick,captured_ms=meta['wall_ms'],
                         raw_sha256=sha256(raw).hexdigest(),front_sha256=sha256(front).hexdigest(),
                         background_sha256=sha256(background).hexdigest(),
                         final_palette_sha256=sha256(palettes[3]).hexdigest(),
                         depth_sha256=meta['depth_sha256'],actors=draws,actor_state_count=len(states)))
    if not any(r['actor_state_count'] for r in rows):
        raise ValueError('No actor-state channel was observed')
    return dict(schema='scummbucket-cross-room-indexed-evidence/1',
                status='actor_state_indexed_capture',capture=str(capture),
                capture_mode='actor_state',run_sha256=sha256(run_bytes).hexdigest(),
                engine_exe_sha256=run['exe_sha256'],indexed_frame_count=len(rows),
                rooms={str(room):sum(r['room']==room for r in rows) for room in sorted({r['room'] for r in rows})},
                scene_fidelity='NOT VALIDATED',association='raw engine tick identity only; no SDL phase claim',
                frames=rows)


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--capture',type=Path,required=True)
    p.add_argument('--output',type=Path,required=True)
    args = p.parse_args()
    if args.output.exists() or args.output.is_symlink():
        p.error('Refusing existing output')
    result = index_capture(args.capture)
    with args.output.open('x',encoding='utf-8') as out:
        json.dump(result,out,indent=2)
    print(json.dumps({k:v for k,v in result.items() if k!='frames'},indent=2))
