"""Capture a bounded, headless Woodtick doorway run from a private room 7 save."""
import argparse
import hashlib
import json
import os
import shutil
import subprocess
from pathlib import Path

def digest(path):
    checksum = hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            checksum.update(block)
    return checksum.hexdigest()


def capture(args):
    args.output.mkdir(parents=True, exist_ok=False)
    save_dir = args.output / 'saves'
    save_dir.mkdir()
    shutil.copyfile(args.save, save_dir / 'monkey2.s01')
    config = args.output / 'scummvm.ini'
    config.write_text(f'''[scummvm]
autosave_period=0
savepath={save_dir}

[monkey2]
gameid=monkey2
engineid=scumm
platform=pc
language=en
render_mode=vga
path={args.game}
''', encoding='utf-8')
    command = [str(args.exe), f'--config={config}', f'--logfile={args.output / "runtime.log"}',
               '--save-slot=1', '--gfx-mode=surfacesdl', '--no-fullscreen',
               '--scaler=normal', '--scale-factor=1', '--no-aspect-ratio', '--no-filtering', '--stretch-mode=center',
               f'--music-driver={args.driver}', '--debuglevel=1', '--debugflags=imuse']
    if args.driver != 'adlib':
        command.append('--native-mt32')
    command.append('monkey2')
    env = dict(os.environ, SDL_VIDEODRIVER=args.video_driver, SDL_AUDIODRIVER='dummy',
               PATH=f'{args.runtime_bin}{os.pathsep}{os.environ["PATH"]}')
    with (args.output / 'console.log').open('xb') as log:
        try:
            completed = subprocess.run(command, cwd=args.output, env=env, stdout=log, stderr=log,
                                       timeout=args.seconds, creationflags=subprocess.CREATE_NO_WINDOW)
            result = completed.returncode
        except subprocess.TimeoutExpired:
            result = 'capture_deadline'
    sources = {name: digest(args.game / name) for name in ('MONKEY2.000', 'MONKEY2.001')}
    manifest = {'command': command, 'archive_sha256': sources, 'exe_sha256': digest(args.exe),
                'save_sha256': digest(args.save), 'result': result, 'seconds': args.seconds}
    (args.output / 'run.json').write_text(json.dumps(manifest, indent=2), encoding='utf-8')
    print(result)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    for arg in ('exe', 'game', 'save', 'output'):
        parser.add_argument(arg, type=lambda value: Path(value).resolve())
    parser.add_argument('--driver', default='adlib', choices=('adlib', 'mt32', 'windows', 'null'))
    parser.add_argument('--video-driver', default='dummy')
    parser.add_argument('--seconds', type=int, default=52)
    parser.add_argument('--runtime-bin', type=Path, default=Path('C:/msys64/ucrt64/bin'))
    capture(parser.parse_args())
