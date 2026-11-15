"""Compare original BOXD/SCAL rules with independently recorded doorway ticks."""
import argparse
from hashlib import sha256
import json
from pathlib import Path
from scummbucket.scene_source import load_scene,source_scale
from tools.room7_doorway import read_ticks

def audit(game,capture):
    raw=(capture/'ticks.tsv').read_bytes()
    ticks=read_ticks(raw.decode().splitlines())
    run=json.loads((capture/'run.json').read_bytes())
    scenes={r:load_scene(game,r)['manifest'] for r in {t['room'] for t in ticks.values()}}
    for m in scenes.values():
        for source in m['sources']:
            if run['archives'].get(Path(source['label']).name)!=source['sha256']:
                raise ValueError('Capture/archive identity mismatch')
    rows=[]
    for tick,t in ticks.items():
        m=scenes[t['room']];box=m['walkboxes'][t['walkbox']]
        scale=source_scale(box,m['scale_slots'],t['world'][1])
        rows.append(dict(tick=tick,room=t['room'],box=t['walkbox'],world=t['world'],
            expected_scale=scale,observed_scale=t['scale'],
            scale_match=t['scale']==[scale,scale],source_plane=box['plane'],
            observed_draw_plane=t['draw_plane'],
            plane_match=None if t['draw_plane'] is None else box['plane']==t['draw_plane']))
    failures=sum(not r['scale_match'] or r['plane_match'] is False for r in rows)
    return dict(schema='cross-room-navigation-audit/0.1',status='FAILED' if failures else 'VERIFIED',
        boundary='This captured route only. No general script/save override, pathfinding, or original DOS binary equivalence claim.',
        tick_sha256=sha256(raw).hexdigest(),run_sha256=sha256((capture/'run.json').read_bytes()).hexdigest(),
        rooms={r:dict(room_sha256=m['room_sha256'],scale_slots=m['scale_slots']) for r,m in scenes.items()},
        ticks=len(rows),scale_components_compared=2*len(rows),
        draw_planes_compared=sum(r['plane_match'] is not None for r in rows),failures=failures,rows=rows)

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('game','capture','output'):p.add_argument(name,type=Path)
    a=p.parse_args();r=audit(a.game,a.capture)
    with a.output.open('x',encoding='utf8') as f:json.dump(r,f,indent=2)
    print(json.dumps({k:v for k,v in r.items() if k not in ('rows','rooms')},indent=2))
    raise SystemExit(1 if r['failures'] else 0)
