"""Extend an isolated copy of the pinned V2 build (SDL2, static SCUMM)."""
import argparse
import hashlib
from pathlib import Path

from instrument_scummvm_palette import patch_source, TARGET_RELATIVE, BACKUP_SUFFIX


def insert(text, anchor, replacement):
    if text.count(anchor) != 1:
        raise ValueError(f"ambiguous or missing anchor: {anchor!r}")
    return text.replace(anchor, replacement)


def install(original, build):
    if original.resolve() == build.resolve():
        raise ValueError("supply a separate build copy")
    core = build / TARGET_RELATIVE
    pristine = (original / (str(TARGET_RELATIVE) + BACKUP_SUFFIX)).read_bytes()
    expected = patch_source(pristine)
    if core.read_bytes() != expected or (original / TARGET_RELATIVE).read_bytes() != expected:
        raise ValueError("expected exact V2 source in both trees")
    sdl = build / "backends/graphics/surfacesdl/surfacesdl-graphics.cpp"
    src = sdl.read_text(encoding="utf8")
    if hashlib.sha256(src.encode()).hexdigest() != "fd9a3509aa52425ac928796249ca416217b19e95b09c727aafd13d6f8905913d":
        raise ValueError("unexpected SDL surface backend")
    text = core.read_text(encoding="utf8")
    text = insert(text, "namespace Scumm {", '''#include "graphics/paletteman.h"
#include "base/version.h"

unsigned sbRoom23Present = 0;
namespace Scumm {
static byte sbPhases[3][768];
static unsigned sbFrame;
static bool sbActive, sbStaged;
''')
    text = insert(text, "void ScummEngine::scummLoop_handleEffects() {",
                  '''void ScummEngine::scummLoop_handleEffects() {
    static const bool enabled = Common::FSNode(Common::Path("capture.enabled")).exists();
    sbActive = enabled && sbFrame < 87 && _currentRoom == 23 && _game.id == GID_MONKEY2 &&
        _game.version == 5 && _game.platform == Common::kPlatformDOS && !_enableEGADithering;
    sbStaged = sbActive;
    if (sbActive) {
        memcpy(sbPhases[0], _currentPalette, 768);
    }''')
    text = insert(text, "\tpalManipulate();", '''    if (sbActive)
        memcpy(sbPhases[1], _currentPalette, 768);
    palManipulate();
    if (sbActive) {
        memcpy(sbPhases[2], _currentPalette, 768);
    }''')
    # Same four operations as Cmd_Room, only in a flagged research run.
    cursor = "\tCursorMan.showMouse(_cursor.state > 0);\n}\n\n#ifdef ENABLE_HE"
    text = insert(text, cursor, cursor.replace("\n}", """
    static bool enter = Common::FSNode(Common::Path("enter-room23.enabled")).exists();
    if (enter && _game.id == GID_MONKEY2 && _game.platform == Common::kPlatformDOS &&
            _game.version == 5 && !_enableEGADithering && _currentRoom && VAR(VAR_EGO) > 0 &&
            VAR(VAR_EGO) < _numActors) {
        enter = false;
        if (_currentRoom != 23) {
            warning("Room23 reference: debugger-equivalent jump from room %u", _currentRoom);
            _actors[VAR(VAR_EGO)]->_room = 23;
            _sound->stopAllSounds();
            startScene(23, nullptr, 0);
            _fullRedraw = true;
        }
    }
}""", 1))
    end = "\t\tupdatePalette();\n\t\tdrawDirtyScreenParts();"
    text = insert(text, end, end + "\n" + ENGINE)
    src = insert(src, "static void destroySurface", "extern unsigned sbRoom23Present;\n\nstatic void destroySurface")
    src = insert(src, "\t\tSDL_RenderPresent(_renderer);", DISPLAY + "\n\t\tSDL_RenderPresent(_renderer);")
    sdl.write_text(src, encoding="utf8")
    core.write_text(text, encoding="utf8")


ENGINE = r'''
        if (sbStaged && _currentRoom == 23) {
            sbStaged = false;
            const unsigned id = ++sbFrame;
            const uint32 millis = _system->getMillis();
            VirtScreen &v = _virtscr[kMainVirtScreen];
            const Common::Path path(Common::String::format("engine-%03u.bin", id));
            Common::DumpFile out;
            if (sbRoom23Present || Common::FSNode(path).exists() || !out.open(path))
                error("Room23 capture collision or missing prior present");
            if (v.w != 320 || v.h != 144 || v.xstart != 0 || !v.backBuf ||
                    v.format.bytesPerPixel != 1 || _gdi->_numStrips < 40)
                error("Unsupported Room23 geometry");
            out.writeString(Common::String::format("R23E1 %u %u %d %d %d %d %d %d %d\n",
                id, millis, VAR(VAR_TIMER), VAR(VAR_TIMER_NEXT), v.topline - _screenTop,
                _gdi->_numZBuffer, int(_renderMode), _system->getGraphicsMode(), int(_system->getScaler())));
            out.writeString(Common::String(gScummVMFullVersion) + "\n");
            for (int i = 1; i < _numActors; ++i) {
                Actor *a = _actors[i];
                if (a && a->_room == 23)
                    out.writeString(Common::String::format("actor %d %d %d %u %u %u %u %u\n",
                        i, a->getRealPos().x, a->getRealPos().y, a->_visible, a->_costume,
                        a->_frame, a->_walkbox, a->_forceClip));
            }
            for (int i = 1; i < _numLocalObjects; ++i) {
                int n = _objs[i].obj_nr;
                if (n)
                    out.writeString(Common::String::format("object %d %d\n", n, getState(n)));
            }
            out.writeString("DATA\n");
            out.write(sbPhases, sizeof(sbPhases));
            byte pal[768];
            _system->getPaletteManager()->grabPalette(pal, 0, 256);
            out.write(pal, sizeof(pal));
            for (int y = 0; y < v.h; ++y)
                out.write(v.getBackPixels(0, y), v.w);
            for (int y = 0; y < v.h; ++y)
                out.write(v.getPixels(0, y), v.w);
            for (int z = 0; z < _gdi->_numZBuffer; ++z)
                for (int y = 0; y < v.h; ++y)
                    out.write(getMaskBuffer(0, y, z), 40);
            Graphics::Surface *surface = _system->lockScreen();
            if (!surface || surface->w != 320 || surface->h != 200 || surface->format.bytesPerPixel != 1)
                error("Expected 320x200 CLUT8 backend");
            for (int y = 0; y < surface->h; ++y)
                out.write(surface->getBasePtr(0, y), surface->w);
            _system->unlockScreen();
            out.flush();
            if (out.err())
                error("Room23 engine write failed");
            out.close();
            sbRoom23Present = id;
        }'''

DISPLAY = r'''
        if (sbRoom23Present) {
            const unsigned id = sbRoom23Present;
            int w, h;
            SDL_RendererInfo info;
            if (SDL_GetRendererOutputSize(_renderer, &w, &h) || SDL_GetRendererInfo(_renderer, &info) ||
                    w <= 0 || h <= 0 || w > 4096 || h > 4096)
                error("Unsupported SDL2 renderer");
            Common::Array<byte> rgb;
            rgb.resize(w * h * 3);
            uint32 millis = g_system->getMillis();
            if (SDL_RenderReadPixels(_renderer, nullptr, SDL_PIXELFORMAT_RGB24, rgb.data(), w * 3))
                error("SDL readback failed: %s", SDL_GetError());
            Common::Path path(Common::String::format("present-%03u.bin", id));
            Common::DumpFile out;
            if (Common::FSNode(path).exists() || !out.open(path))
                error("Cannot create Room23 present capture");
            out.writeString(Common::String::format("R23D1 %u %u %d %d %s\n", id, millis, w, h, info.name));
            out.write(rgb.data(), rgb.size());
            out.flush();
            if (out.err())
                error("Room23 renderer write failed");
            sbRoom23Present = 0;
        }'''


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("original", type=Path)
    parser.add_argument("build", type=Path)
    args = parser.parse_args()
    install(args.original, args.build)
