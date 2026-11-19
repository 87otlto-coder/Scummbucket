import argparse
import json
import os
from pathlib import Path
import shutil
import subprocess
import time

from tools.run_room23_frames import ARCHIVES, digest
from scummbucket.scummvm_save import inspect_scummvm_save


def capture(exe, game, save, dest, scenario, dll_dir, *, room=35, frame_count=32):
    if (room, scenario) not in ((24, None), (35, "clear"), (35, "set"), (35, "override")):
        raise ValueError("Unsupported room and capture scenario")
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
    meta = dict(entry="debugger_equivalent_room_entry", equivalent_command=f"room {room}",
                injected_bit92=None if room == 24 else int(scenario == "set"),
                injected_bit567=None if room == 24 else int(scenario == "override"), save_state=state,
                save_sha256=save_hash, archives=ARCHIVES, exe_sha256=digest(exe),
                version=version, command=command)
    (dest / "run.json").write_text(json.dumps(meta, indent=2), encoding="utf8")
    (dest / ("room24.enabled" if room == 24 else f"room35-{scenario}.enabled")).touch(exist_ok=False)
    (dest / "capture.enabled").touch(exist_ok=False)
    with (dest / "console.log").open("xb") as log:
        proc = subprocess.Popen(command, cwd=dest, env=env, stdout=log, stderr=log)
        try:
            deadline = time.monotonic() + 35
            while proc.poll() is None and time.monotonic() < deadline:
                if (dest / f"present-{frame_count:03}.bin").is_file():
                    break
                time.sleep(0.1)
        finally:
            if proc.poll() is None:
                proc.terminate()
            proc.wait(timeout=10)
    if not (dest / f"present-{frame_count:03}.bin").is_file():
        raise RuntimeError(f"Incomplete capture: {dest}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Capture debugger-equivalent Room 24 or controlled Room 35 entry.")
    for name in ("exe", "game", "save", "dest"):
        parser.add_argument(name, type=lambda value: Path(value).resolve())
    parser.add_argument("scenario", nargs="?", choices=("clear", "set", "override"))
    parser.add_argument("--room24", action="store_true")
    parser.add_argument("--dll-dir", type=Path, default=Path("C:/msys64/ucrt64/bin"))
    arguments = vars(parser.parse_args())
    room24 = arguments.pop("room24")
    capture(**arguments, room=24 if room24 else 35, frame_count=64 if room24 else 32)
