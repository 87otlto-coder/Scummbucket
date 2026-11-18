import argparse
import json
import os
from pathlib import Path
import shutil
import subprocess
import time

from tools.run_room23_frames import ARCHIVES, digest
from scummbucket.scummvm_save import inspect_scummvm_save


def capture(exe, game, save, dest, scenario, dll_dir):
    if {name: digest(game / name) for name in ARCHIVES} != ARCHIVES:
        raise ValueError("Unexpected DOS archives")
    state = inspect_scummvm_save(save)
    if (state["current_room"], state["room_resource"]) != (23, 23):
        raise ValueError("Room 35 capture expects the pinned Room 23 starting conditions")
    dest.mkdir(parents=True, exist_ok=False)
    saves = dest / "saves"
    saves.mkdir()
    copied = saves / "monkey2.s01"
    shutil.copyfile(save, copied)
    save_hash = digest(save)
    if digest(copied) != save_hash:
        raise ValueError("Save copy changed")
    config = dest / "scummvm.ini"
    config.write_text(f"[scummvm]\ngfx_mode=surfacesdl\nautosave_period=0\nsavepath={saves}\n"
                      f"[monkey2]\nengineid=scumm\ngameid=monkey2\nplatform=pc\n"
                      f"language=en\nrender_mode=vga\npath={game}\n", encoding="utf8")
    command = [str(exe), f"--config={config}", f"--logfile={dest / 'runtime.log'}",
               "--debuglevel=3", "--scaler=normal", "--scale-factor=1", "--no-aspect-ratio",
               "--no-fullscreen", "--no-filtering", "--stretch-mode=center",
               "--music-driver=windows_Microsoft GS Wavetable Synth", "--save-slot=1", "monkey2"]
    env = dict(os.environ, SDL_VIDEODRIVER="dummy", SDL_AUDIODRIVER="dummy",
               SDL_RENDER_DRIVER="software", PATH=str(dll_dir) + os.pathsep + os.environ["PATH"])
    version = subprocess.check_output([str(exe), "--version"], cwd=dest, env=env,
                                      text=True, timeout=10).strip()
    meta = dict(entry="debugger_equivalent_room_entry", equivalent_command="room 35",
                injected_bit92=int(scenario == "set"), injected_bit567=0, save_state=state,
                save_sha256=save_hash, archives=ARCHIVES, exe_sha256=digest(exe),
                version=version, command=command)
    (dest / "run.json").write_text(json.dumps(meta, indent=2), encoding="utf8")
    (dest / f"room35-{scenario}.enabled").touch(exist_ok=False)
    (dest / "capture.enabled").touch(exist_ok=False)
    with (dest / "console.log").open("xb") as log:
        proc = subprocess.Popen(command, cwd=dest, env=env, stdout=log, stderr=log)
        try:
            deadline = time.monotonic() + 25
            while proc.poll() is None and time.monotonic() < deadline:
                if (dest / "present-032.bin").is_file():
                    break
                time.sleep(0.1)
        finally:
            if proc.poll() is None:
                proc.terminate()
            proc.wait(timeout=10)
    if not (dest / "present-032.bin").is_file():
        raise RuntimeError(f"Incomplete capture: {dest}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Capture controlled debugger-equivalent Room 35 entry.")
    for name in ("exe", "game", "save", "dest"):
        parser.add_argument(name, type=lambda value: Path(value).resolve())
    parser.add_argument("scenario", choices=("clear", "set"))
    parser.add_argument("--dll-dir", type=Path, default=Path("C:/msys64/ucrt64/bin"))
    capture(**vars(parser.parse_args()))
