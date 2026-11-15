"""Align observed Room 12 actor instructions with original resource operands.

This is a bounded direct-operand reader, not a SCUMM disassembler or VM.
It establishes executed sites/operands, not intra-tick animation state.
"""
from hashlib import sha256
import json
from pathlib import Path
import re
from scummbucket.inspector import inspect,_read_pair,XOR_KEY

def actor_ops(data,start,end):
    actor=data[start];p=start+1;operations=[]
    fields={1:('costume',1),2:('walk_speed',2),3:('sound',1),5:('talk_frames',2),
            6:('stand_frame',1),8:('defaults',0),12:('talk_color',1),
            18:('never_zclip',0),19:('force_zclip',1),20:('ignore_boxes',0)}
    while p<end and data[p]!=255:
        sub=data[p];p+=1
        if sub not in fields:raise ValueError(f'Unsupported actor suboperation {sub}')
        name,n=fields[sub]
        if p+n>end:raise ValueError('Truncated actor operands')
        operations.append(dict(operation=name,values=list(data[p:p+n])));p+=n
    if p>=end:raise ValueError('Unterminated actor operations')
    return dict(actor_id=actor,operations=operations)

def audit(game,capture):
    inv=inspect(game);index,resource,_,_=_read_pair(game)
    if [sha256(x).hexdigest() for x in (index,resource)]!=[r['sha256'] for r in inv['sources']]:raise ValueError('Archive changed')
    data=bytes(x^XOR_KEY for x in resource)
    room,=(r for r in inv['scene_inventory']['rooms'] if r['room_id']==12)
    scripts={data[s['source_offset']+8]:s for s in room['local_script_chunks'] if s['tag']=='LSCR'}
    log=(capture/'console.log').read_bytes();seen=set();rows=[]
    names={'o5_actorOps':0x13,'o5_animateActor':0x11,'o5_putActorInRoom':0x2d,'o5_putActor':0x01}
    for match in re.finditer(r'Script (\d+), offset 0x([0-9a-f]+): \[([0-9A-Fa-f]+)\] (\w+)\(\)',log.decode('utf8')):
        script,offset,opcode,name=match.groups();script=int(script);offset=int(offset,16);opcode=int(opcode,16)
        if script not in scripts or name not in names or (script,offset) in seen:continue
        absolute=room['room_offset']+offset-1;s=scripts[script]
        if not s['source_offset']+9<=absolute<s['source_offset']+s['byte_length']:continue
        seen.add((script,offset))
        if data[absolute]!=opcode or opcode!=names[name]:raise ValueError('Opcode/source alignment mismatch')
        p=absolute+1;end=s['source_offset']+s['byte_length']
        if name=='o5_actorOps':decoded=actor_ops(data,p,end)
        elif name=='o5_putActor':
            decoded=dict(actor_id=data[p],x=int.from_bytes(data[p+1:p+3],'little',signed=True),y=int.from_bytes(data[p+3:p+5],'little',signed=True))
        else:decoded=dict(actor_id=data[p],**{'animation' if name=='o5_animateActor' else 'room':data[p+1]})
        rows.append(dict(script=script,reported_offset=offset,archive_opcode_offset=absolute,
            operation=name,operands=decoded,script_sha256=sha256(data[s['source_offset']:end]).hexdigest()))
    if not rows:raise ValueError('No source-aligned actor sites')
    return dict(schema='room12-actor-source-audit/0.1',status='VERIFIED',boundary='Executed direct-operand sites only; not animation phase, timing, or complete actor state.',
        console_sha256=sha256(log).hexdigest(),sources=inv['sources'],sites=rows)

if __name__=='__main__':
    import argparse
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('game','capture','output'):p.add_argument(name,type=Path)
    a=p.parse_args();r=audit(a.game,a.capture)
    with a.output.open('x',encoding='utf8') as f:json.dump(r,f,indent=2)
    print('Verified source-aligned actor sites:',len(r['sites']))
