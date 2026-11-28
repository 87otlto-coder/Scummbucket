"""Rebuild the six probe objects and link against the pinned CrossRoom archives."""
import argparse
import os
import subprocess
from pathlib import Path

FILES = ('engines/scumm/scumm.cpp', 'engines/scumm/script_v5.cpp', 'engines/scumm/sound.cpp',
         'engines/scumm/imuse/imuse.cpp', 'engines/scumm/imuse/imuse_player.cpp', 'audio/midiparser.cpp')


def build(root, compiler_dir):
    compiler = compiler_dir / 'g++.exe'
    env = dict(os.environ, PATH=f'{compiler_dir}{os.pathsep}{os.environ["PATH"]}')

    def run(arguments):
        subprocess.run([str(compiler), *arguments], cwd=root, env=env, check=True)

    flags = ['-DHAVE_CONFIG_H', '-DENABLE_SCUMM=STATIC_PLUGIN', '-DWIN32', '-DSDL_BACKEND',
             '-DUSE_SDL2', '-DUNICODE', '-D_UNICODE', '-I.', '-Iengines',
             f'-I{compiler_dir.parent / "include" / "SDL2"}', '-std=gnu++11', '-fno-operator-names', '-Wno-multichar']
    dest = root / 'imuse-probe'
    dest.mkdir(exist_ok=False)
    objects = []
    for n, source in enumerate(FILES):
        obj = f'imuse-probe/{n}.o'
        run([*flags, '-c', source, '-o', obj])
        objects.append(obj)
    libraries = sorted(str(path.relative_to(root)) for path in root.rglob('lib*.a'))
    platform = sorted(str(path.relative_to(root)) for path in (root / 'backends/platform/sdl').rglob('*.o'))
    run(['-static-libgcc', '-static-libstdc++', *objects, *platform, 'engines/scumm/detection.o',
         '-Wl,--start-group', *libraries, '-Wl,--end-group',
         f'-L{compiler_dir.parent / "lib"}', '-lmingw32', '-lSDL2main', '-lSDL2',
         '-lwinmm', '-lgdi32', '-lz', '-lole32', '-luuid', '-lwinspool', '-lsapi',
         '-o', 'imuse-probe/scummvm-imuse.exe'])


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('copy', type=Path)
    parser.add_argument('--compiler-dir', type=Path, default=Path('C:/msys64/ucrt64/bin'))
    args = parser.parse_args()
    build(args.copy.resolve(), args.compiler_dir.resolve())
