"""Adapt a fresh copy of the pinned Room 7 tool for ordinary player input."""
from hashlib import sha256
from pathlib import Path


def replace_once(source, before, after):
    if source.count(before) != 1:
        raise ValueError(f"Unexpected source near {before[:60]}")
    return source.replace(before, after)


def install(original, copy):
    patches = {}
    for name, digest in {
        "actor.cpp": "b5442b20567d675b02c77e12b9cb66b4632a8d5f56c04ac0606f8ae8afd5dc63",
        "scumm.cpp": "7fbbe0546f4ddfbccdd992c54552cc1a189fb5f911a9a944d1700e21a1a86a2d",
    }.items():
        rel = Path("engines/scumm") / name
        src, dst = original / rel, copy / rel
        if src.samefile(dst) or sha256(src.read_bytes()).hexdigest() != digest or src.read_bytes() != dst.read_bytes():
            raise ValueError(f"Need a separate unmodified Room 7 build copy for {name}")
        s = src.read_text(encoding="utf8")
        if name == "actor.cpp":
            marker = "if (bcr->drawCostume(_vm->_virtscr"
            s = replace_once(s, marker, """extern Common::String sbNavigationDraw;
    if (!hitTestMode && _number == 1 && _room == 7) {
        sbNavigationDraw = Common::String::format("draw %d %d %d %d %d %d %d",
            bcr->_actorX, bcr->_actorY, bcr->_zbuf, _scalex, _scaley, getFacing(), _costume);
        for (int limb = 0; limb < 16; ++limb)
            sbNavigationDraw += Common::String::format(" %u", _cost.curpos[limb]);
    }
    """ + marker)
        else:
            s = replace_once(s, "static unsigned sbFrame;", "Common::String sbNavigationDraw;\nstatic unsigned sbFrame, sbNavigationTick;")
            marker = "void ScummEngine::scummLoop(int delta) {"
            s = replace_once(s, marker, marker + "\n    ++sbNavigationTick;\n    sbNavigationDraw.clear();")
            start = s.index("            static const bool walk =")
            end = s.index("            for (int i = 1; i < _numLocalObjects", start)
            s = s[:start] + '''            Actor *ego = _actors[1];
            out.writeString(Common::String::format("navigation %u %d %d %d %d %d %d\\n",
                sbNavigationTick, ego->_moving, ego->getFacing(),
                ego->getElevation(),
                ego->_ignoreBoxes, ego->_cost.animCounter, getClass(1, kObjectClassNeverClip)));
            if (!sbNavigationDraw.empty())
                out.writeString(sbNavigationDraw + "\\n");
''' + s[end:]
            start = s.index("            if (walk && id == 5)")
            s = s[:start] + s[s.index("            }", start) + 13:]
            start = s.index("    static bool enter =")
            s = s[:start] + s[s.index("\n}", start):]
            s = replace_once(s, "sbFrame < 87", "sbFrame < 2400")
        patches[dst] = s
    for path, source in patches.items():
        path.write_text(source, encoding="utf8")


if __name__ == "__main__":
    import sys
    install(*map(Path, sys.argv[1:]))
