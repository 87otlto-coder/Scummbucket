"""Read-only archive/doorway experiment; private output only, no acceptance claim."""
from pathlib import Path
from hashlib import sha256
import json
from PIL import Image, ImageChops
from scummbucket.inspector import inspect, XOR_KEY, chunks
from scummbucket.palette_probe import decode_room_background_indexed
from scummbucket.object_images import _decode_zplane
from scummbucket.classic_costume import ClassicCostume
from scummbucket.classic_scale import paint_scaled
from tools.compare_room23_frames import present
from scummbucket.scene_source import load_scene, compose_actor

def main(game, capture, dest):
    dest.mkdir(parents=True, exist_ok=False)
    inv = inspect(game)
    raw = (game/'MONKEY2.001').read_bytes()
    data = bytes(b ^ XOR_KEY for b in raw)
    room, = (r for r in inv['scene_inventory']['rooms'] if r['room_id']==12)
    bg = decode_room_background_indexed(data,room_offset=room['room_offset'],room_length=room['room_size'])
    im = bg['source']['im00_offset']
    masks = {int(n.tag[2:]):_decode_zplane(data,n,width=bg['width'],height=bg['height']) for n in chunks(data,im+8,im+int.from_bytes(data[im+4:im+8],'big'),'IM00') if n.tag.startswith('ZP')}
    link, = (r for r in inv['directory_links']['entries'] if r['directory']=='DCOS' and r['id']==1)
    guy = ClassicCostume(data[link['source_offset']:link['source_offset']+link['byte_length']])
    scene=load_scene(game,12)
    world = Image.frombytes('P',(bg['width'],bg['height']),bg['indexed_pixels'])
    world.putpalette(bg['initial_palette'])
    world.save(dest/'background.png')
    for z,m in masks.items(): Image.frombytes('L',world.size,m).save(dest/f'ZP{z:02}.png')
    ticks={}
    for line in (capture/'ticks.tsv').read_text().splitlines():
        *f,draw=line.split('\t'); f=list(map(int,f))
        ticks[f[0]]=(f, list(map(int,draw.split()[1:])) if draw else None)
    rows=[]
    for line in (capture/'presents.tsv').read_text().splitlines():
        seq,tick,ms=map(int,line.split())
        if tick not in ticks or ticks[tick][0][1]!=12: continue
        f,pose=ticks[tick]
        if pose is None: continue
        x,y,z,sx,sy,facing,cost,*positions=pose
        if cost!=1 or sx!=sy: raise ValueError('Unsupported actor')
        left,top=f[8:10]
        background=world.crop((left,top,left+320,top+144)).tobytes()
        predicted=bytearray(background)
        paint_scaled(guy,predicted,320,x,y,facing,positions,sx)
        mask=Image.frombytes('L',world.size,masks[z]).crop((left,top,left+320,top+144)).tobytes() if z else bytes(46080)
        unmasked=bytes(predicted)
        predicted=bytes(b if m else p for p,b,m in zip(predicted,background,mask))
        if predicted != compose_actor(scene,guy,pose,(left,top,320,144)):
            raise ValueError('Reusable compositor differs from exploratory implementation')
        image=Image.frombytes('P',(320,144),predicted); image.putpalette(bg['initial_palette'])
        observed=(capture/f'present-{seq:03}.bin').read_bytes()
        _,_,ref=present(observed,seq)
        # Test source palette and the known RGB565 presentation conversion separately.
        rgb=image.convert('RGB')
        quant=rgb.point(lambda v: v) # channel-specific bit replication below
        q=bytes((v>>3)*255//31 if i%3!=1 else (v>>2)*255//63 for i,v in enumerate(rgb.tobytes()))
        quant=Image.frombytes('RGB',rgb.size,q)
        candidates=[]
        for screen_y in (0,16):
            actual=ref.crop((0,screen_y,320,screen_y+144))
            diff=ImageChops.difference(quant,actual)
            channels=diff.split(); union=ImageChops.lighter(ImageChops.lighter(channels[0],channels[1]),channels[2])
            candidates.append(dict(screen_y=screen_y,errors=46080-union.histogram()[0],bbox=union.getbbox()))
        expected565=[((r>>3)<<11)|((g>>2)<<5)|(b>>3) for r,g,b in zip(*[iter(rgb.tobytes())]*3)]
        observed565=[(round(r*31/255)<<11)|(round(g*63/255)<<5)|round(b*31/255) for r,g,b in zip(*[iter(ref.crop((0,0,320,144)).tobytes())]*3)]
        diff565=bytes(255 if a!=b else 0 for a,b in zip(expected565,observed565))
        delta565=Image.frombytes('L',(320,144),diff565)
        pal=bg['initial_palette']
        palette565=[((pal[i]>>3)<<11)|((pal[i+1]>>2)<<5)|(pal[i+2]>>3) for i in range(0,768,3)]
        unmasked_errors=sum(palette565[p]!=a for p,a in zip(unmasked,observed565))
        # Wrong actor placement is a second negative control; never used to fit output.
        shifted_pose=[x+1,*pose[1:]]
        shifted=compose_actor(scene,guy,shifted_pose,(left,top,320,144))
        shifted_errors=sum(palette565[p]!=a for p,a in zip(shifted,observed565))
        first=next((i for i,d in enumerate(diff565) if d),None)
        row=dict(sequence=seq,tick=tick,pose=pose,present_sha256=sha256(observed).hexdigest(),candidates=candidates,
            rgb565_errors=diff565.count(255),rgb565_bbox=delta565.getbbox(),
            first_rgb565_difference=None if first is None else dict(x=first%320,y=first//320,expected=expected565[first],observed=observed565[first]),
            unmasked_rgb565_errors=unmasked_errors,shifted_actor_rgb565_errors=shifted_errors,
            mask_changed_indices=sum(a!=b for a,b in zip(predicted,unmasked)),predicted_indexed_sha256=sha256(predicted).hexdigest())
        rows.append(row)
        if len(rows)==1:
            image.save(dest/'candidate.png'); ref.save(dest/'reference.png'); delta565.save(dest/'rgb565-errors.png')
    summary=dict(schema='room12-cross-room-probe/0.1',status='PARTIALLY VERIFIED',
        comparison_boundary='RGB565-equivalent words from RGB readback; not original palette indices; tick/presentation phase not resolved',
        source=scene['manifest'],capture=str(capture),tick_file_sha256=sha256((capture/'ticks.tsv').read_bytes()).hexdigest(),
        presentation_index_sha256=sha256((capture/'presents.tsv').read_bytes()).hexdigest(),
        room=12,dimensions=world.size,background_sha256=sha256(bg['indexed_pixels']).hexdigest(),mask_pixels={z:m.count(255) for z,m in masks.items()},rows=rows,diagnostics=bg['diagnostics'],
        unsupported=['other actors 7 and 8','object-state composition','cursor','exact backend RGB conversion','original indexed framebuffer comparison'])
    (dest/'probe.json').write_text(json.dumps(summary,indent=2))
    print(json.dumps({k:v for k,v in summary.items() if k!='rows'}))
    print('comparisons',len(rows),'best',min((c['errors'],r['sequence'],c['screen_y'],c['bbox']) for r in rows for c in r['candidates']))

if __name__=='__main__':
    import sys
    main(*(Path(a) for a in sys.argv[1:]))
