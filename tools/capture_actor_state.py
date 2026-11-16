"""Launch a private native actor-state capture; ordinary input, no game writes."""
import argparse
from hashlib import sha256
import json
import os
from pathlib import Path
import shutil
import subprocess
from uuid import uuid4

from scummbucket.scummvm_save import inspect_scummvm_save
from tools.run_room23_frames import ARCHIVES


def digest(path):
    return sha256(Path(path).read_bytes()).hexdigest()


def capture(root, exe, game, save):
    root, exe, game, save = (Path(p).resolve() for p in (root, exe, game, save))
    if not exe.is_relative_to(root/'TOOLS') or not exe.is_file():
        raise ValueError('Expected private TOOLS executable')
    if any(digest(game/n) != h for n, h in ARCHIVES.items()):
        raise ValueError('Original DOS VGA archive mismatch')
    state = inspect_scummvm_save(save)
    if state['current_room'] != 7 or state['room_resource'] != 7:
        raise ValueError('Expected original Room 7 save')
    dest = root/'FIXTURE/CAPTURES/Room7'/('actor-state-'+uuid4().hex)
    dest.mkdir(parents=True, exist_ok=False)
    saves = dest/'saves'
    saves.mkdir()
    shutil.copyfile(save, saves/'monkey2.s01')
    if digest(save) != digest(saves/'monkey2.s01'):
        raise ValueError('Copied save differs')
    ini = dest/'scummvm.ini'
    ini.write_text(f'[scummvm]\ngfx_mode=surfacesdl\nautosave_period=0\nsavepath={saves}\n'
                   f'[monkey2]\nengineid=scumm\ngameid=monkey2\nplatform=pc\nlanguage=en\n'
                   f'render_mode=vga\npath={game}\n', encoding='utf-8')
    cmd = [str(exe),f'--config={ini}',f'--logfile={dest / "runtime.log"}',
           '--save-slot=1','--scaler=normal','--scale-factor=1','--no-aspect-ratio',
           '--no-fullscreen','--no-filtering','--stretch-mode=center',
           '--debuglevel=3','--music-driver=adlib','monkey2']
    for marker in ('capture.enabled','doorway.enabled'):
        (dest/marker).touch(exist_ok=False)
    run = dict(schema='scummbucket-actor-state-capture/1',capture_mode='actor_state',
               command=cmd,exe_sha256=digest(exe),archives=ARCHIVES,
               save_sha256=digest(save),save_state=state,
               entry='loaded private save; no debugger or injected actor movement',
               actor_state_phase='before redraw gate and animateCostume',
               frame_limit=2400,input_method='ordinary game controls')
    with (dest/'run.json').open('x',encoding='utf-8') as out:
        json.dump(run,out,indent=2)
    env = os.environ.copy()
    env['PATH'] = 'C:/msys64/ucrt64/bin'+os.pathsep+env.get('PATH','')
    print(dest,flush=True)
    with (dest/'console.log').open('xb') as log:
        result = subprocess.run(cmd,cwd=dest,env=env,stdout=log,stderr=log)
    with (dest/'exit.json').open('x',encoding='utf-8') as out:
        json.dump(dict(returncode=result.returncode),out)
    if result.returncode:
        raise RuntimeError(f'Native recorder exited {result.returncode}; preserve partial evidence')
    return dest


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    for name in ('root','exe','game','save'):
        p.add_argument('--'+name,type=Path,required=True)
    a = p.parse_args()
    capture(a.root,a.exe,a.game,a.save)
