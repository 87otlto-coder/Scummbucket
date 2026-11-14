"""Adapt the pinned private walk build in a separate Room 7 copy."""
import argparse
from hashlib import sha256
from pathlib import Path


def install(original, build):
    changes = []
    for name, digest in (
        ("actor.cpp", "c8e8484d4f618b9e3897a21d75a5f8c46710f116c1c1c198a5a797394030f105"),
        ("scumm.cpp", "01cb5b7e563f8864e9aa0b5352c271a139e59abd703ccc4b809f63d536894053"),
    ):
        rel = Path("engines/scumm") / name
        src, dst = original / rel, build / rel
        raw = src.read_bytes()
        if src.samefile(dst) or sha256(raw).hexdigest() != digest or raw != dst.read_bytes():
            raise ValueError(f"Expected separate pinned walk sources for {rel}")
        s = dst.read_text(encoding="utf8")
        if name == "actor.cpp":
            s = s.replace("_number == 1 && _room == 23", "_number == 1 && _room == 7")
        else:
            for old, new in (
                ("_currentRoom == 23", "_currentRoom == 7"), ("_currentRoom != 23", "_currentRoom != 7"),
                ("->_room == 23", "->_room == 7"), ("->_room = 23;", "->_room = 7;"),
                ("startScene(23, nullptr", "startScene(7, nullptr"), ("BEGIN|23|", "BEGIN|7|"),
                ("room23", "room7"), ("Room23", "Room7"),
                ("v.xstart != 0", "v.xstart < 0 || v.xstart + v.w > _roomWidth"),
                ("_actors[1]->startWalkActor(280, 125, -1);",
                 "_actors[1]->startWalkActor(_roomWidth - 48, 130, -1);\n"
                 "                panCameraTo(_roomWidth - v.w / 2, 0);"),
            ):
                s = s.replace(old, new)
            s = s.replace("sbRoom7Present", "sbRoom23Present")
            marker = "            static const bool walk ="
            s = s.replace(marker, r'''            out.writeString(Common::String::format("camera %d %d %d %d %d %d %d %d\n",
                camera._cur.x, camera._cur.y, v.xstart, _screenTop, v.w, v.h, _roomWidth, _roomHeight));
            for (int i = 1; i < _numActors; ++i) {
                Actor *a = _actors[i];
                if (a && a->_room == 7)
                    out.writeString(Common::String::format("scale %d %d %d\n", i, a->_scalex, a->_scaley));
            }
            for (int i = 0; i < NUM_SCRIPT_SLOT; ++i)
                if (vm.slot[i].status != ssDead)
                    out.writeString(Common::String::format("script %d %d %d %d %u\n", i, vm.slot[i].number,
                        vm.slot[i].where, vm.slot[i].status, vm.slot[i].offs));
''' + marker)
        changes.append((dst, s))
    for dst, s in changes:
        dst.write_text(s, encoding="utf8")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("original", type=Path)
    parser.add_argument("build", type=Path)
    args = parser.parse_args()
    install(args.original, args.build)

