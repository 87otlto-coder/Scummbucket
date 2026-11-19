from pathlib import Path
import sys

base, dest = map(Path, sys.argv[1:])
source = base / "engines/scumm"

def overlay(name, anchor, replacement):
    text = (source / name).read_text(encoding="utf8")
    if text.count(anchor) != 1:
        raise ValueError(f"Unexpected {name} anchor")
    with (dest / name).open("x", encoding="utf8") as stream:
        stream.write(text.replace(anchor, replacement))

overlay("script_v5.cpp", '\tdebug(6, "o5_getRandomNr(): %d (min: 0, max: %d)", rnd, max);', '''
    if (_currentRoom == 24 && _currentScript != 0xff && vm.slot[_currentScript].number == 200)
        warning("SB24 RNG max=%d result=%d previous=%d", max, rnd, readVar(0x4000));
\tdebug(6, "o5_getRandomNr(): %d (min: 0, max: %d)", rnd, max);''')

anchor = 'void ScummEngine::runEntryScript() {'
overlay("script.cpp", anchor, anchor + '''
    if (_game.id == GID_MONKEY2 && (_currentRoom == 24 || _currentRoom == 35)) {
        warning("SBPAL before-entry room=%d globals=%d,%d", _currentRoom,
                VAR(VAR_ENTRY_SCRIPT), VAR(VAR_ENTRY_SCRIPT2));
        for (int i = 0; i < 16; ++i)
            warning("SBPAL %d %d %d %d", i, _currentPalette[3*i],
                    _currentPalette[3*i+1], _currentPalette[3*i+2]);
    }''')

anchor = '\tif (VAR_ENTRY_SCRIPT2 != 0xFF && VAR(VAR_ENTRY_SCRIPT2))\n\t\trunScript(VAR(VAR_ENTRY_SCRIPT2), 0, 0, nullptr);'
path = dest / "script.cpp"
text = path.read_text(encoding="utf8")
if text.count(anchor) != 1:
    raise ValueError("Unexpected post-ENCD hook boundary")
text = text.replace(anchor, '''
    const bool traceEntry = _game.id == GID_MONKEY2 && (_currentRoom == 24 || _currentRoom == 35);
    if (traceEntry) {
        warning("SBPAL hook-context room=%d hook=%d mode=%d", _currentRoom,
                VAR(VAR_ENTRY_SCRIPT2), VAR(49));
        for (int i = 469; i <= 480; ++i)
            warning("SBPAL var %d %d", i, readVar(i));
    }
'''+anchor+'''
    if (traceEntry) {
        for (int i = 0; i < 16; ++i)
            warning("SBPAL after %d %d %d %d", i, _currentPalette[3*i],
                    _currentPalette[3*i+1], _currentPalette[3*i+2]);
    }''')
path.write_text(text, encoding="utf8")
