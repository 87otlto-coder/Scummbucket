"""Add a read-only costume-142 limb snapshot to a *copy* of the Room 7 build.

Use only after tools/instrument_room7.py has produced and built its pinned
Room 7 source tree. The existing capture records actor 11's position, but
not actor 11's animated limb cursors. Never patch the canonical checkout
or overwrite a capture; Work must choose a fresh TOOLS build path.
"""
import argparse
from pathlib import Path


ANCHOR = "            for (int i = 1; i < _numLocalObjects;"
WALK_GUARD = 'static const bool walk = Common::FSNode(Common::Path("walk.enabled")).exists();'
CAMERA_GUARD = 'out.writeString(Common::String::format("camera %d %d %d %d %d %d %d %d'
SNAPSHOT = r'''            // Research-only, frame-synchronous scenery actor 11 state.
            // The original Room 7 sweep records a walk row for actor 1 only.
            if (walk && _currentRoom == 7 && _numActors > 11) {
                Actor *scenery = _actors[11];
                if (scenery && scenery->_room == 7) {
                    out.writeString(Common::String::format("costume11 %d %d %d %d %d",
                        scenery->_costume, scenery->getFacing(), scenery->_scalex,
                        scenery->_scaley, scenery->_cost.animCounter));
                    for (int limb = 0; limb < 16; ++limb) {
                        out.writeString(Common::String::format(" %u %u %u",
                            scenery->_cost.curpos[limb], scenery->_cost.start[limb],
                            scenery->_cost.end[limb]));
                    }
                    out.writeString("\n");
                }
            }
'''


def instrument(source: str) -> str:
    if source.count(ANCHOR) != 1:
        raise ValueError("expected one pinned Room 7 frame-state insertion point")
    if source.count(WALK_GUARD) != 1 or source.count(CAMERA_GUARD) != 1:
        raise ValueError("expected existing Room 7 walk and camera instrumentation")
    if "costume11 " in source:
        raise ValueError("costume11 snapshot already present; refuse to patch again")
    return source.replace(ANCHOR, SNAPSHOT + ANCHOR, 1)


def install(original: Path, copy: Path) -> None:
    relative = Path("engines/scumm/scumm.cpp")
    src, dst = original / relative, copy / relative
    if not src.is_file() or not dst.is_file():
        raise ValueError("expected existing independent Room 7 source copies")
    if src.samefile(dst) or src.read_bytes() != dst.read_bytes():
        raise ValueError("source copies differ; no overwrites or unexpected patches allowed")
    old = dst.read_text(encoding="utf-8")
    updated = instrument(old)
    # Only the copied build's ScummVM C++ source is changed.
    dst.write_text(updated, encoding="utf-8")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("original_room7_build", type=Path)
    parser.add_argument("fresh_room7_copy", type=Path)
    args = parser.parse_args()
    install(args.original_room7_build, args.fresh_room7_copy)
