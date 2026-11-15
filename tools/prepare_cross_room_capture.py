"""Prepare a non-overwriting ScummVM source overlay for the exact missing data.

Not a build or capture. Apply only to a separate copy of the pinned doorway
tool under TOOLS, then compile and validate on Windows. Source-lineage review
remains open. The original tool is read-only.
"""
from hashlib import sha256
import json
from pathlib import Path
from tools.instrument_room7_navigation import replace_once

def transform(engine,actor):
    engine=replace_once(engine,'Common::String sbNavigationDraw;',
                        'Common::String sbNavigationDraw, sbCrossRoomDraws;')
    engine=replace_once(engine,'    sbNavigationDraw.clear();',
                        '    sbNavigationDraw.clear();\n    sbCrossRoomDraws.clear();')
    engine=replace_once(engine,'if (sbStaged && _currentRoom == 7)',
                        'if (sbStaged && (_currentRoom == 7 || _currentRoom == 12))')
    gate='sbFrame < 2400 && _currentRoom == 7 && _game.id == GID_MONKEY2'
    engine=replace_once(engine,gate,'sbFrame < 2400 && (_currentRoom == 7 || _currentRoom == 12) && _game.id == GID_MONKEY2')
    if engine.count('if (a && a->_room == 7)')!=2:raise ValueError('Unexpected actor inventory anchors')
    engine=engine.replace('if (a && a->_room == 7)','if (a && a->_room == _currentRoom)')
    marker='            out.writeString("DATA\\n");'
    extra='''            out.writeString(Common::String::format("scene %d %u\\n", _currentRoom, sbNavigationTick));
            out.writeString(sbCrossRoomDraws);
'''
    engine=replace_once(engine,marker,extra+marker)
    marker='\textern Common::String sbNavigationDraw;'
    actor=replace_once(actor,marker,'''    extern Common::String sbCrossRoomDraws;
    if (!hitTestMode && _room == _vm->_currentRoom &&
            (_room == 7 || _room == 12)) {
        sbCrossRoomDraws += Common::String::format("draw_actor %d %d %d %d %u %u %d %u %u %u",
            _number, bcr->_actorX, bcr->_actorY, bcr->_zbuf,
            _scalex, _scaley, getFacing(), _costume, _frame, _cost.stopped);
        for (int limb = 0; limb < 16; ++limb)
            sbCrossRoomDraws += Common::String::format(" %u", _cost.curpos[limb]);
        for (int slot = 0; slot < 32; ++slot)
            sbCrossRoomDraws += Common::String::format(" %u", _palette[slot]);
        sbCrossRoomDraws += "\\n";
    }
'''+marker)
    return engine,actor

def prepare(source,dest):
    names=['engines/scumm/scumm.cpp','engines/scumm/actor.cpp']
    pins=['db3bbc6da8574cbe56e2ce54d60f35ae33dff72f2b9c62ba8c2f673b6634d769',
          'c2468483a6cd44a0a80660ce32173dd88aae6a23a9c33f06520dc21fa9337640']
    raw=[(source/n).read_bytes() for n in names]
    if [sha256(x).hexdigest() for x in raw]!=pins:raise ValueError('Doorway build source fingerprint mismatch')
    patched=transform(*(x.decode('utf8') for x in raw))
    dest.mkdir(parents=True,exist_ok=False)
    files=[]
    for name,before,after in zip(names,raw,patched):
        path=dest/name;path.parent.mkdir(parents=True,exist_ok=True)
        with path.open('x',encoding='utf8',newline='\n') as f:f.write(after)
        files.append(dict(path=name,input_sha256=sha256(before).hexdigest(),output_sha256=sha256(path.read_bytes()).hexdigest()))
    report=dict(status='SOURCE OVERLAY ONLY — BUILD AND RUNTIME VALIDATION PENDING',files=files,
        required_marker='capture.enabled',payload='Existing R23E1 plus scene and ordered draw_actor header rows',
        draw_actor_fields=['id','screen_x','draw_y','plane','scale_x','scale_y','facing','costume','logical_frame','stopped','16 cursors','32 actor palette overrides'])
    with (dest/'overlay.json').open('x',encoding='utf8') as f:json.dump(report,f,indent=2)
    return report

if __name__=='__main__':
    import argparse
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('source',type=Path);p.add_argument('destination',type=Path)
    a=p.parse_args();print(json.dumps(prepare(a.source,a.destination),indent=2))
