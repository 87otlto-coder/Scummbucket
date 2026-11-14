"""Build the doorway recorder in a new copy of the verified navigation tool."""
import argparse
import os
from pathlib import Path
import shutil
import subprocess

from tools.instrument_room7_navigation import replace_once
from tools.run_room23_frames import digest

BASE = "ScummVM-P4-Room7-Navigation-20261114-a"
BUILD = "ScummVM-P4-Doorway-20261114-b"
PINS = {
    "engines/scumm/scumm.cpp": "d5996ee9028a673074601fe66e6566859fc47cce7fc64a7df8b137aee68478ce",
    "engines/scumm/actor.cpp": "027600e2ce95790f212c6ebd97aa56bc0181fd047c1be920dcd93e412cfe4aaf",
    "backends/graphics/surfacesdl/surfacesdl-graphics.cpp":
        "da8ebb2659ec7ddcd5013824e896334670d1e5c9ec755cd63cae05fdb101c566",
}


def build(root):
    base = root / "TOOLS" / BASE
    dest = base.with_name(BUILD)
    for name, expected in PINS.items():
        if digest(base / name) != expected:
            raise ValueError(f"Unexpected navigation source {name}")
    shutil.copytree(base, dest, ignore=shutil.ignore_patterns(".git"))
    engine, actor, backend = [dest / name for name in PINS]
    s = engine.read_text(encoding="utf8")
    s = replace_once(s, "unsigned sbRoom23Present = 0;", """unsigned sbRoom23Present = 0;
unsigned sbDoorTick;
bool sbDoorEnabled;""")
    s = replace_once(s, "++sbNavigationTick;", """++sbNavigationTick;
    static const bool doorway = Common::FSNode(Common::Path("doorway.enabled")).exists();
    if (sbNavigationTick <= 2400 && doorway && _game.id == GID_MONKEY2 && _currentRoom == 7)
        sbDoorEnabled = true;
    sbDoorTick = sbNavigationTick;
    if (sbDoorTick > 2400)
        sbDoorEnabled = false;""")
    marker = "CursorMan.showMouse(_cursor.state > 0);"
    # The saved game may first be restored partway through the first loop.
    s = replace_once(s, marker + "\n\n}", marker + r'''
    if (sbNavigationTick <= 2400 && doorway && _game.id == GID_MONKEY2 && _currentRoom == 7)
        sbDoorEnabled = true;
    if (sbDoorEnabled) {
        static Common::DumpFile ticks;
        if (!ticks.isOpen()) {
            Common::Path file("ticks.tsv");
            if (Common::FSNode(file).exists() || !ticks.open(file))
                error("Cannot create doorway ticks");
        }
        Actor *a = _actors[1];
        ticks.writeString(Common::String::format("%u\t%d\t%d\t%d\t%d\t%u\t%d\t%d\t%d\t%d\t%u\t%u\t%s\n",
            sbDoorTick, _currentRoom, a->_room, a->getRealPos().x, a->getRealPos().y,
            a->_walkbox, camera._cur.x, camera._cur.y, _virtscr[kMainVirtScreen].xstart,
            _screenTop, a->_scalex, a->_scaley, sbNavigationDraw.c_str()));
        ticks.flush();
        if (ticks.err())
            error("Doorway tick write failed");
    }
}''')
    engine.write_text(s, encoding="utf8")
    s = actor.read_text(encoding="utf8")
    actor.write_text(replace_once(s, "!hitTestMode && _number == 1 && _room == 7",
                                  "!hitTestMode && _number == 1 && _room == _vm->_currentRoom"),
                     encoding="utf8")
    s = backend.read_text(encoding="utf8")
    s = replace_once(s, "extern unsigned sbRoom23Present;",
                     "extern unsigned sbRoom23Present, sbDoorTick;\nextern bool sbDoorEnabled;")
    s = replace_once(s, "if (sbRoom23Present) {\n            const unsigned id = sbRoom23Present;",
                     """static unsigned nextDoorPresent;
        if ((sbDoorEnabled && nextDoorPresent < 4800) || sbRoom23Present) {
            const unsigned id = sbDoorEnabled ? ++nextDoorPresent : sbRoom23Present;""")
    s = replace_once(s, "            sbRoom23Present = 0;", r'''            if (sbDoorEnabled) {
                static Common::DumpFile index;
                if (!index.isOpen()) {
                    Common::Path file("presents.tsv");
                    if (Common::FSNode(file).exists() || !index.open(file))
                        error("Cannot create doorway presentation index");
                }
                index.writeString(Common::String::format("%u\t%u\t%u\n", id, sbDoorTick, millis));
                index.flush();
                if (index.err())
                    error("Doorway presentation index write failed");
            }
            sbRoom23Present = 0;''')
    backend.write_text(s, encoding="utf8")
    env = dict(os.environ, PATH="C:/msys64/ucrt64/bin;C:/msys64/usr/bin;" + os.environ["PATH"])
    with (dest / "doorway-build.log").open("xb") as log:
        subprocess.run(["C:/msys64/usr/bin/make.exe", "-j4"], env=env, cwd=dest,
                       stdout=log, stderr=subprocess.STDOUT, check=True)
    with (dest / "doorway-exe.sha256").open("x") as out:
        out.write(digest(dest / "scummvm.exe") + "\n")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("root", type=Path)
    build(parser.parse_args().root.resolve())
