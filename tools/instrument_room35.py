from pathlib import Path
import sys
src,dst=map(Path,sys.argv[1:])
s=src.read_text(encoding='utf8')
s=s.replace('(_currentRoom == 7 || _currentRoom == 12)', '_currentRoom == 35')
anchor='\tCursorMan.showMouse(_cursor.state > 0);'
assert s.count(anchor)==1
s=s.replace(anchor, anchor+'''
    static bool sb35Entered = false;
    static bool sb35Logged = false;
    const bool sb35Clear = Common::FSNode(Common::Path("room35-clear.enabled")).exists();
    const bool sb35Set = Common::FSNode(Common::Path("room35-set.enabled")).exists();
    const bool sb35Override = Common::FSNode(Common::Path("room35-override.enabled")).exists();
    if (!sb35Logged) {
        sb35Logged = true;
        warning("SB35 loop room=%d markers=%d,%d", _currentRoom, sb35Clear, sb35Set);
    }
    if (!sb35Entered && (int(sb35Clear) + int(sb35Set) + int(sb35Override) == 1) && _currentRoom == 23 && _game.id == GID_MONKEY2) {
        sb35Entered = true;
        warning("SB35 inherited room=%d resource=%d b92=%d b567=%d", _currentRoom, _roomResource,
                readVar(0x8000 | 92), readVar(0x8000 | 567));
        writeVar(0x8000 | 567, sb35Override);
        warning("SB35 injected b92=%d b567=%d", sb35Set, sb35Override);
        writeVar(0x8000 | 92, sb35Set);
        _actors[VAR(VAR_EGO)]->_room = 35;
        _sound->stopAllSounds();
        startScene(35, nullptr, 0);
        _fullRedraw = true;
        warning("SB35 entry room=%d resource=%d b92=%d b567=%d", _currentRoom, _roomResource,
                readVar(0x8000 | 92), readVar(0x8000 | 567));
    }''')
anchor='            out.writeString(sbCrossRoomDraws);'
assert s.count(anchor)==1
s=s.replace(anchor,'''            out.writeString(Common::String::format("room35 %d %d %d %d\\n",
                _currentRoom, _roomResource, readVar(0x8000 | 92), readVar(0x8000 | 567)));
            for (int i = 1; i < _numLocalObjects; ++i)
                if (_objs[i].obj_nr)
                    out.writeString(Common::String::format("position %d %d %d\\n",
                        _objs[i].obj_nr, _objs[i].x_pos, _objs[i].y_pos));
            for (int i = 0; i < 2; ++i)
                out.writeString(Common::String::format("cycle %d %d %d %d %d %d\\n", i + 1,
                    _colorCycle[i].delay, _colorCycle[i].counter, _colorCycle[i].flags,
                    _colorCycle[i].start, _colorCycle[i].end));
'''+anchor)
with dst.open('x', encoding='utf8') as f:
    f.write(s)
