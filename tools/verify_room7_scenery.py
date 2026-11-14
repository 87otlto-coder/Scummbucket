"""Compare the pinned debugger-jump sweep with archive scenery alone.

Run python -m tools.verify_room7_scenery F:/Dev/SCUMMBUCKET/FIXTURE.
Expected zero differences at frames 36 through 81. Guybrush omitted.
"""
from pathlib import Path
import json, hashlib
from PIL import Image
from tools.compare_room23_frames import engine
from scummbucket.inspector import inspect, XOR_KEY
from scummbucket.classic_costume import ClassicCostume, compose

def compare(fixture):
    game = fixture / 'GAMES/MonkeyIsland2_DOS_VGA'
    link, = (r for r in inspect(game)['directory_links']['entries'] if r['directory']=='DCOS' and r['id']==142 and r['room_id']==7 and r['status']=='linked')
    start = link['source_offset']
    raw = (game/'MONKEY2.001').read_bytes()
    chunk = bytes(v ^ XOR_KEY for v in raw[start:start+link['byte_length']])
    if hashlib.sha256(chunk).hexdigest() != '7ef3e98fb9cd824782b0cf7e93d9e7f3c059354557ec7e08d714eda9425a7c5f':
        raise ValueError('Unexpected costume 142')
    costume = ClassicCostume(chunk)
    report = json.loads((fixture/'REPORTS/Room7/sweep-20261110-a/report.json').read_bytes())
    with Image.open(fixture/'OUTPUT/Room7/native-20261110-a/background.png') as world:
        if hashlib.sha256(world.tobytes()).hexdigest() != '843f5d1d81ed8bb8f7353a0c5b3c52d2229505becbd47a411b3cd4314b5bccfc':
            raise ValueError('Unexpected indexed world')
        for row in report['frames']:
            seq = row['id']
            raw = (fixture/f'CAPTURES/Room7/sweep-20261110-a/engine-{seq:03}.bin').read_bytes()
            if hashlib.sha256(raw).hexdigest() != row['engine_sha256']:
                raise ValueError(f'Capture hash mismatch at {seq}')
            meta, _, back, front, _ = engine(raw, seq)
            actor, = (s.split() for s in meta['state'] if s.startswith('actor 11 '))
            x = row['viewport_xy'][0]
            bg = world.crop((x,0,x+320,144)).tobytes()
            if bg != back:
                raise ValueError(f'Background mismatch at {seq}')
            predicted, _ = compose(costume,bg,320,int(actor[2])-x,int(actor[3]),180,[0]+[65535]*15)
            yield dict(frame=seq, mismatches=sum(a!=b for a,b in zip(predicted,front)))

if __name__ == '__main__':
    import sys
    print(json.dumps(list(compare(Path(sys.argv[1])))))
