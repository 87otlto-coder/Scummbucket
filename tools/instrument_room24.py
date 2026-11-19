from pathlib import Path
import sys
src,dst=map(Path,sys.argv[1:])
s=src.read_text(encoding='utf8')
s=s.replace('(_currentRoom == 7 || _currentRoom == 12)', '_currentRoom == 24')
anchor='\tCursorMan.showMouse(_cursor.state > 0);'
if s.count(anchor) != 1: raise ValueError('Unexpected pinned ScummVM source')
s=s.replace(anchor, anchor+'''
    static bool sb24Entered = false;
    static const bool enabled24 = Common::FSNode(Common::Path("room24.enabled")).exists();
    if (!sb24Entered && enabled24 && _currentRoom == 23 && _game.id == GID_MONKEY2) {
        sb24Entered = true;
        warning("SB24 inherited room=%d resource=%d b92=%d b567=%d", _currentRoom, _roomResource,
                readVar(0x8000 | 92), readVar(0x8000 | 567));
        _actors[VAR(VAR_EGO)]->_room = 24;
        _sound->stopAllSounds();
        startScene(24, nullptr, 0);
        _fullRedraw = true;
        warning("SB24 entry room=%d resource=%d b92=%d b567=%d", _currentRoom, _roomResource,
                readVar(0x8000 | 92), readVar(0x8000 | 567));
    }''')
anchor='            out.writeString(sbCrossRoomDraws);'
assert s.count(anchor)==1
s=s.replace(anchor,'''            out.writeString(Common::String::format("room24 %d %d %d %d\\n",
                _currentRoom, _roomResource, readVar(0x8000 | 92), readVar(0x8000 | 567)));
            for (int i = 1; i < _numLocalObjects; ++i)
                if (_objs[i].obj_nr)
                    out.writeString(Common::String::format("position %d %d %d\\n",
                        _objs[i].obj_nr, _objs[i].x_pos, _objs[i].y_pos));
            for (int i = 0; i < 8; ++i)
                out.writeString(Common::String::format("cycle %d %d %d %d %d %d\\n", i + 1,
                    _colorCycle[i].delay, _colorCycle[i].counter, _colorCycle[i].flags,
                    _colorCycle[i].start, _colorCycle[i].end));
'''+anchor)
with dst.open('x', encoding='utf8') as f:
    f.write(s)
