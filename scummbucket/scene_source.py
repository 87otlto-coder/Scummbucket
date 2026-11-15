"""Archive-derived v5 scene components; no automatic script/runtime inference.

Format references: ScummVM v2026.4.0 boxes.cpp/boxes.h, resource/room
loading, and the existing ScummBucket P4 image decoders. Experimental only.
"""
from hashlib import sha256
from pathlib import Path
from struct import unpack_from
from types import SimpleNamespace
from PIL import Image
from .inspector import inspect, _read_pair, XOR_KEY, chunks
from .palette_probe import decode_room_background_indexed
from .object_images import _decode_zplane
from .classic_scale import paint_scaled

def decode_boxes(payload):
    if len(payload)<2: raise ValueError('Truncated v5 BOXD count')
    count=int.from_bytes(payload[:2],'little')
    if count>255 or len(payload)!=2+20*count:
        raise ValueError('Unsupported v5 BOXD length')
    result=[]
    for i in range(count):
        *xy,plane,flags,scale=unpack_from('<8hBBH',payload,2+20*i)
        result.append(dict(id=i,corners=[xy[j:j+2] for j in range(0,8,2)],
                           plane=plane,flags=flags,scale_raw=scale))
    return result

def decode_scales(payload):
    if len(payload)%8: raise ValueError('Truncated v5 SCAL record')
    slots={}
    for i in range(len(payload)//8):
        s1,y1,s2,y2=unpack_from('<4H',payload,i*8)
        if s1 or y1 or s2 or y2:
            slots[i+1]=dict(scale1=s1,y1=y1,scale2=s2,y2=y2)
    return slots

def source_scale(box,slots,y):
    """Unmodified archive slot rule, not live script/save scale state."""
    raw=box['scale_raw']
    if not raw&32768:
        if not 0<=raw<=255:raise ValueError('Unsupported fixed scale')
        return raw
    s=slots[(raw&32767)+1]
    numerator=(s['scale2']-s['scale1'])*(max(0,y)-s['y1'])
    denominator=s['y2']-s['y1']
    if not denominator:raise ValueError('Degenerate scale slot')
    # C++ integer division truncates toward zero, unlike Python //.
    delta=(abs(numerator)//abs(denominator))*(-1 if (numerator<0)!=(denominator<0) else 1)
    return max(1,min(255,s['scale1']+delta))

def load_scene(game, room_id):
    game=Path(game)
    inv=inspect(game)
    if inv['status']!='success': raise ValueError('Archive inspection failed')
    index,resource,_,_=_read_pair(game)
    if [sha256(x).hexdigest() for x in (index,resource)] != [r['sha256'] for r in inv['sources']]:
        raise ValueError('Archive changed during inspection')
    room,=(r for r in inv['scene_inventory']['rooms'] if r['room_id']==room_id)
    data=bytes(x^XOR_KEY for x in resource)
    start,size=room['room_offset'],room['room_size']
    nodes=chunks(data,start+8,start+size,'ROOM')
    bg=decode_room_background_indexed(data,room_offset=start,room_length=size)
    im=bg['source']['im00_offset']
    layers=chunks(data,im+8,im+int.from_bytes(data[im+4:im+8],'big'),'IM00')
    masks={int(n.tag[2:]):_decode_zplane(data,n,width=bg['width'],height=bg['height']) for n in layers if n.tag.startswith('ZP') and n.tag[2:].isdigit()}
    boxd,=(n for n in nodes if n.tag=='BOXD')
    boxes=decode_boxes(data[boxd.offset+8:boxd.end])
    scal=[n for n in nodes if n.tag=='SCAL']
    if len(scal)>1:raise ValueError('Duplicate SCAL')
    scales=decode_scales(data[scal[0].offset+8:scal[0].end]) if scal else {}
    manifest=dict(schema='scumm-source-scene/0.1',room_id=room_id,
                  sources=inv['sources'],source_evidence='archive-decoded',
                  room_offset=start,room_length=size,
                  room_sha256=sha256(data[start:start+size]).hexdigest(),
                  dimensions=[bg['width'],bg['height']],
                  indexed_sha256=bg['pixel_indices_sha256'],palette_sha256=bg['initial_palette_sha256'],
                  masks={z:dict(sha256=sha256(m).hexdigest(),set_pixels=m.count(255)) for z,m in masks.items()},
                  walkboxes=boxes,scale_slots=scales,scene_inventory=room,
                  resources=[dict(tag=n.tag,offset=n.offset,length=n.length,sha256=sha256(data[n.offset:n.end]).hexdigest()) for n in nodes],
                  diagnostics=bg['diagnostics'],
                  runtime_state=None,playback_evidence=None,
                  unsupported=['automatic script execution','automatic object visibility','automatic actor activation','native timing'])
    return dict(manifest=manifest,background=bg['indexed_pixels'],palette=bg['initial_palette'],masks=masks,
                room_bytes=data[start:start+size])

def compose_actor(scene, costume, pose, viewport=(0,0,320,144), *, mask_enabled=True):
    """Draw one explicitly supplied draw-phase pose; does not infer actor order."""
    left,top,width,height=viewport
    sw,sh=scene['manifest']['dimensions']
    if min(left,top)<0 or min(width,height)<1 or left+width>sw or top+height>sh:
        raise ValueError('Viewport outside source scene')
    if len(pose)!=23: raise ValueError('Expected 23 draw-phase fields')
    x,y,plane,sx,sy,facing,_,*positions=pose
    if sx!=sy or not 0<=sx<=255: raise ValueError('Unsupported actor scaling')
    if plane and plane not in scene['masks']: raise ValueError('Missing requested depth plane')
    cut=(left,top,left+width,top+height)
    bg=Image.frombytes('L',(sw,sh),scene['background']).crop(cut).tobytes()
    pixels=bytearray(bg)
    # Recorded draw anchors already include camera/elevation transforms.
    paint_scaled(costume,pixels,width,x,y,facing,positions,sx)
    if plane and mask_enabled:
        mask=Image.frombytes('L',(sw,sh),scene['masks'][plane]).crop(cut).tobytes()
        pixels=bytes(b if m else p for p,b,m in zip(pixels,bg,mask))
    return bytes(pixels)



def compose_actor_layers(scene, costumes, draw_rows, viewport=(0,0,320,144), *,
                         mask_enabled=True):
    """Paint observed actors in explicitly recorded order at native scale.

    Important: masking one actor restores the *previous composite*, not the
    empty room background. An occluded nearer actor must reveal previously
    painted actors where the selected depth mask hides it.

    This is only a bounded indexed compositor; it cannot infer script state,
    object visibility, actor order, palette animation or presentation phase.
    Palette mapping comes from observed 32-slot Actor::_palette, not source
    COST palette, when the draw record includes the field.
    """
    left,top,width,height=viewport
    sw,sh=scene["manifest"]["dimensions"]
    if (min(left,top)<0 or min(width,height)<1 or
        left+width>sw or top+height>sh):
        raise ValueError("Viewport outside source scene")
    if not isinstance(draw_rows,list) or len(draw_rows)>256:
        raise ValueError("Invalid ordered actor draw list")
    if not isinstance(costumes,dict):
        raise ValueError("Need COST decoders keyed by costume ID")
    base=Image.frombytes("L",(sw,sh),scene["background"]).crop(
        (left,top,left+width,top+height)).tobytes()
    pixels=bytearray(base)
    masks={}
    for row in draw_rows:
        if not isinstance(row,dict):
            raise ValueError("Invalid recorded actor draw row")
        x,y,plane=row["screen_x"],row["draw_y"],row["plane"]
        sx,sy=row["scales"]
        facing,cost_id=row["facing"],row["costume"]
        if (type(sx) is not int or type(sy) is not int or
            sx!=sy or not 0<=sx<=255 or facing not in (0,90,180,270)):
            raise ValueError("Unsupported draw-phase actor geometry")
        if plane and plane not in scene["masks"]:
            raise ValueError("Missing requested depth plane")
        if cost_id not in costumes:
            raise ValueError(f"Missing original COST {cost_id}")
        source=costumes[cost_id]
        indices=row["cursors"]
        stopped=row["stopped"]
        if (not isinstance(indices,list) or len(indices)!=16 or
            type(stopped) is not int or not 0<=stopped<=65535 or
            any(type(n) is not int or not 0<=n<=65535 for n in indices)):
            raise ValueError("Invalid costume limb/stopped state")
        visible=[65535 if stopped&(1<<i) else n for i,n in enumerate(indices)]
        overrides=row.get("palette_override")
        if overrides is not None:
            if (not isinstance(overrides,list) or len(overrides)!=32 or
                any(type(v) is not int or not 0<=v<=255 for v in overrides)):
                raise ValueError("Unsupported live actor palette override")
            if not 1<=source.colors<=32:
                raise ValueError("Unsupported original costume palette size")
            # The ScummVM classic renderer treats 255 as a request for the
            # original COST palette slot, rather than literal index 255.
            costume=SimpleNamespace(force_right=source.force_right,
                  palette=bytes(source.palette[i] if overrides[i] == 255 else overrides[i] for i in range(source.colors)),limb=source.limb)
        else:
            costume=source
        previous=bytes(pixels)
        paint_scaled(costume,pixels,width,x,y,facing,visible,sx)
        if plane and mask_enabled:
            if plane not in masks:
                masks[plane]=Image.frombytes("L",(sw,sh),scene["masks"][plane]).crop(
                    (left,top,left+width,top+height)).tobytes()
            pixels[:]=bytes(old if m else new for old,new,m in
                            zip(previous,pixels,masks[plane]))
    return bytes(pixels)
