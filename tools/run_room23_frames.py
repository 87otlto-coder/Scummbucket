"""Launch the isolated frame build in a new private capture directory."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import time

ARCHIVES = {
    "MONKEY2.000": "cde7aa8980317e3a750fbb3b49884cdddaf1ff3d4231a0c840b22cceed9033f1",
    "MONKEY2.001": "ad045372e0d49626503bb50fca29a687ec8e01ef75d9b8bca702a366d143819e",
}


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def run(args):
    exe, game, dest = (p.resolve() for p in (args.exe, args.game, args.output))
    if {name: digest(game / name) for name in ARCHIVES} != ARCHIVES:
        raise ValueError("unexpected DOS game archives")
    dest.mkdir(parents=True, exist_ok=False)
    saves = dest / "saves"
    saves.mkdir()
    config = dest / "scummvm.ini"
    config.write_text(f"[scummvm]\ngfx_mode=surfacesdl\nautosave_period=0\nsavepath={saves}\n"
                      f"[monkey2]\nengineid=scumm\ngameid=monkey2\nplatform=pc\n"
                      f"language=en\nrender_mode=vga\npath={game}\n", encoding="utf8")
    command = [str(exe), f"--config={config}", f"--logfile={dest / 'runtime.log'}",
               "--debuglevel=3", "--scaler=normal", "--scale-factor=1", "--no-aspect-ratio",
               "--no-fullscreen", "--no-filtering", "--stretch-mode=center", f"--music-driver={args.music_driver}"]
    if args.save:
        shutil.copyfile(args.save, saves / "monkey2.s01")
        command.append("--save-slot=1")
    command.append("monkey2")
    env = os.environ.copy()
    env["PATH"] = str(args.dll_dir) + os.pathsep + env["PATH"]
    if args.headless:
        env.update(SDL_VIDEODRIVER="dummy", SDL_AUDIODRIVER="dummy", SDL_RENDER_DRIVER="software")
    meta = {"command": command, "exe_sha256": digest(exe), "archives": ARCHIVES,
            "headless": args.headless, "debugger_equivalent_entry": args.enter_room, "save_sha256": digest(args.save) if args.save else None,
            "version": subprocess.check_output([str(exe), "--version"], cwd=dest, env=env,
                                               text=True, errors="replace").strip()}
    (dest / "run.json").write_text(json.dumps(meta, indent=2), encoding="utf8")
    if args.enter_room:
        (dest / "enter-room23.enabled").touch(exist_ok=False)
    (dest / "capture.enabled").touch(exist_ok=False)
    with (dest / "console.log").open("xb") as log:
        proc = subprocess.Popen(command, cwd=dest, env=env, stdout=log, stderr=log)
        deadline = time.monotonic() + args.timeout
        try:
            while proc.poll() is None and time.monotonic() < deadline:
                if (dest / "present-087.bin").exists() and (dest / "scummbucket-p4-room23.raw.log").exists():
                    time.sleep(1)
                    break
                time.sleep(0.2)
        finally:
            if proc.poll() is None:
                proc.terminate()
            proc.wait()
    if not (dest / "present-087.bin").exists():
        raise SystemExit(f"Incomplete capture in {dest}. See runtime.log and console.log.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("exe", "game", "output"):
        parser.add_argument("--" + name, type=Path, required=True)
    parser.add_argument("--dll-dir", type=Path, default=Path("C:/msys64/ucrt64/bin"))
    parser.add_argument("--music-driver", default="auto")
    parser.add_argument("--save", type=Path)
    parser.add_argument("--enter-room", action="store_true")
    parser.add_argument("--headless", action="store_true")
    parser.add_argument("--timeout", type=int, default=120)
    run(parser.parse_args())
