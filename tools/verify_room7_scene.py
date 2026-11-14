"""Usage: python -m tools.verify_room7_scene FIXTURE NEW_OUTPUT_DIRECTORY.

Pinned MI2 original DOS debugger-equivalent sweep. ZP01 negative control and
per-frame indexed comparisons are written to manifest.json. Expected 87 exact
frames, 778 unmasked mismatches. No natural-entry or other-route coverage.
"""
from pathlib import Path
import json, hashlib
from PIL import Image
from tools.compare_room23_frames import engine
from scummbucket.inspector import inspect, XOR_KEY
from scummbucket.classic_costume import ClassicCostume, compose, apply_depth
from scummbucket.classic_scale import paint_scaled
from scummbucket.palette_probe import prepare_cycles, advance_palette

def compare(fixture, dest):
    dest.mkdir(parents=True, exist_ok=False)
    game = fixture / 'GAMES/MonkeyIsland2_DOS_VGA'
    link, = (r for r in inspect(game)['directory_links']['entries'] if r['directory']=='DCOS' and r['id']==142 and r['room_id']==7 and r['status']=='linked')
    start = link['source_offset']
    raw = (game/'MONKEY2.001').read_bytes()
    chunk = bytes(v ^ XOR_KEY for v in raw[start:start+link['byte_length']])
    if hashlib.sha256(chunk).hexdigest() != '7ef3e98fb9cd824782b0cf7e93d9e7f3c059354557ec7e08d714eda9425a7c5f':
        raise ValueError('Unexpected costume 142')
    costume = ClassicCostume(chunk)
    guy_link, = (r for r in inspect(game)['directory_links']['entries'] if r['directory']=='DCOS' and r['id']==1)
    off = guy_link['source_offset']
    guy = ClassicCostume(bytes(v ^ XOR_KEY for v in raw[off:off+guy_link['byte_length']]))
    report = json.loads((fixture/'REPORTS/Room7/sweep-20261110-a/report.json').read_bytes())
    with Image.open(fixture/'OUTPUT/Room7/native-20261110-a/ZP01.png') as mask_image:
        mask = mask_image.convert('1')
    with Image.open(fixture/'OUTPUT/Room7/native-20261110-a/background.png') as world:
        if hashlib.sha256(world.tobytes()).hexdigest() != '843f5d1d81ed8bb8f7353a0c5b3c52d2229505becbd47a411b3cd4314b5bccfc':
            raise ValueError('Unexpected indexed world')
        manifest = json.loads((fixture/'OUTPUT/Room7/native-20261110-a/manifest.json').read_bytes())
        cycles, problems = prepare_cycles(manifest['scene']['palette_cycles'])
        if problems:
            raise ValueError(problems)
        palette = None
        for row in report['frames']:
            seq = row['id']
            raw = (fixture/f'CAPTURES/Room7/sweep-20261110-a/engine-{seq:03}.bin').read_bytes()
            if hashlib.sha256(raw).hexdigest() != row['engine_sha256']:
                raise ValueError(f'Capture hash mismatch at {seq}')
            meta, palettes, back, front, _ = engine(raw, seq)
            actor, = (s.split() for s in meta['state'] if s.startswith('actor 11 '))
            x = row['viewport_xy'][0]
            bg = world.crop((x,0,x+320,144)).tobytes()
            if bg != back:
                raise ValueError(f'Background mismatch at {seq}')
            predicted, _ = compose(costume,bg,320,int(actor[2])-x,int(actor[3]),180,[0]+[65535]*15)
            guy_actor, = (s.split() for s in meta['state'] if s.startswith('actor 1 '))
            walk, = (s.split() for s in meta['state'] if s.startswith('walk 1 '))
            scale, = (s.split() for s in meta['state'] if s.startswith('scale 1 '))
            positions = list(map(int,walk[-16:]))
            facing = int(walk[4])
            if int(guy_actor[6]) == 2 and int(walk[3]):
                positions = guy.drawn_walk_positions(2,facing,positions)
            scenery = predicted
            predicted = bytearray(predicted)
            paint_scaled(guy,predicted,320,int(guy_actor[2])-x,int(guy_actor[3]),facing,positions,int(scale[2]))
            unmasked = sum(a!=b for a,b in zip(predicted,front))
            if int(walk[1]) == 1:
                predicted = apply_depth(predicted,scenery,mask.crop((x,0,x+320,144)).tobytes())
            if palette is None:
                palette = bytearray(palettes[0])
            advance_palette(palette, cycles, delta=max(meta['timer_pair']))
            if palette != palettes[3]:
                raise ValueError(f'Final palette mismatch at {seq}')
            image = Image.frombytes('P',(320,144),bytes(predicted))
            image.putpalette(bytes(palette))
            name = f'frame-{seq:03}.png'
            image.save(dest/name)
            yield dict(file=name,time_ms=row['present_ms'],camera_x=x,reference_sha256=row['engine_sha256'],indexed_sha256=hashlib.sha256(predicted).hexdigest(),unmasked=unmasked,frame=seq, mismatches=sum(a!=b for a,b in zip(predicted,front)))

if __name__ == '__main__':
    import sys
    dest = Path(sys.argv[2])
    rows = list(compare(Path(sys.argv[1]),dest))
    from scummbucket.room23_export import PLAYER
    from scummbucket.standalone_preview import render_standalone_preview
    (dest/'preview.html').write_text(render_standalone_preview(dest, rows, PLAYER), encoding='utf8')
    report = dict(entry='debugger-equivalent Room 23 save jump', frames=rows,
                  archive_inputs=['DCOS[1]', 'DCOS[142]', 'Room 7 SMAP, ZP01, CYCL'],
                  observed_inputs=['camera, actor state, initial palette, timer and presentation timestamps'])
    (dest/'manifest.json').write_text(json.dumps(report,indent=2))
    print('Frames:',len(rows),'mismatches:',sum(r['mismatches'] for r in rows))
    if len(rows)!=87 or any(r['mismatches'] for r in rows):
        raise SystemExit(1)
