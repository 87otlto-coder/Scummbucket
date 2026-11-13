"""Extend a separate copy of the verified Room 23 frame build."""
import argparse
import hashlib
from pathlib import Path

from instrument_room23_frames import insert


def install(original, build):
    files = ["engines/scumm/scumm.cpp", "engines/scumm/actor.cpp"]
    hashes = ["f4fefc19826d255dbf898cf01a8d3032705d46453438ed0db57408b89262b5c1",
              "00c5ba483234ce607a626d150f7f78642267a7d0dbbf9d0a8746ed755385e4be"]
    sources = []
    for name, expected in zip(files, hashes):
        old, new = original / name, build / name
        source = new.read_text(encoding="utf8")
        if (old.samefile(new) or source != old.read_text(encoding="utf8") or
                hashlib.sha256(source.encode()).hexdigest() != expected):
            raise ValueError(f"expected independent copies of pinned {name}")
        sources.append(source)
    core, actor = sources
    core = insert(core, "static unsigned sbFrame;", """static unsigned sbFrame;
int sbWalkPlane = -1;
bool sbWalkControl;""")
    core = insert(core, "            for (int i = 1; i < _numLocalObjects;", r'''            static const bool walk = Common::FSNode(Common::Path("walk.enabled")).exists();
            if (walk) {
                if (VAR(VAR_EGO) != 1)
                    error("Room23 walk requires Guybrush as ego");
                Actor *a = _actors[1];
                out.writeString(Common::String::format("walk %d %d %d %d %d", sbWalkPlane,
                    sbWalkControl, a->_moving, a->getFacing(), a->_cost.animCounter));
                for (int limb = 0; limb < 16; ++limb)
                    out.writeString(Common::String::format(" %u", a->_cost.curpos[limb]));
                out.writeString("\n");
            }
            for (int i = 1; i < _numLocalObjects;''')
    core = insert(core, "            sbRoom23Present = id;", """            sbRoom23Present = id;
            if (walk && id == 5) {
                sbWalkControl = Common::FSNode(Common::Path("walk-control.enabled")).exists();
                _actors[1]->startWalkActor(280, 125, -1);
            }""")
    actor = insert(actor, "\tbcr->_drawTop = 0x7fffffff;", """    extern int sbWalkPlane;
    extern bool sbWalkControl;
    if (_number == 1 && _room == 23) {
        sbWalkPlane = bcr->_zbuf;
        if (sbWalkControl)
            bcr->_zbuf = 0;
    }
\tbcr->_drawTop = 0x7fffffff;""")
    for name, source in zip(files, (core, actor)):
        (build / name).write_text(source, encoding="utf8")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("original", type=Path)
    parser.add_argument("build", type=Path)
    args = parser.parse_args()
    install(args.original, args.build)
