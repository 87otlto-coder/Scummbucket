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


def validate_native_room7_save(args, exe, game, dest):
    """Read-only safety gate; does not authenticate how the save was created.

    The source save may be in the user's ScummVM directory. The copied save,
    generated captures and reports must never live inside the source checkout.
    """
    if not getattr(args, "native_room7_save", False):
        return
    # Canonicalize paths before containment checks (Windows 8.3 path aliases).
    exe, game, dest = (Path(p).resolve() for p in (exe, game, dest))
    if getattr(args, "room", 23) != 7 or args.save is None or args.enter_room or args.walk:
        raise ValueError(
            "--native-room7-save requires --room 7 and --save; "
            "do not use --enter-room or --walk"
        )
    fixture = game.parent.parent
    if fixture.name.upper() != "FIXTURE":
        raise ValueError("Native Room 7 capture game must be under FIXTURE/GAMES")
    if not exe.is_file() or not exe.is_relative_to(fixture.parent / "TOOLS"):
        raise ValueError("Native Room 7 capture requires an existing TOOLS executable")
    save = args.save.resolve()
    if not save.is_file() or save.stat().st_size == 0:
        raise ValueError("Native Room 7 capture requires a nonempty original save")
    if save.is_relative_to(fixture.parent / "SOURCE"):
        raise ValueError("Original save cannot reside inside SOURCE / Git")
    if not dest.is_relative_to(fixture / "CAPTURES" / "Room7"):
        raise ValueError("Capture output must remain under FIXTURE/CAPTURES/Room7")


def run(args):
    exe, game, dest = (p.resolve() for p in (args.exe, args.game, args.output))
    room = getattr(args, "room", 23)
    validate_native_room7_save(args, exe, game, dest)
    if room == 7 and args.walk == "control":
        raise ValueError("Room 7 sweep uses the normal renderer")
    if room == 23 and args.walk and (not args.save or args.enter_room):
        raise ValueError("use the Room 23 save for a walking run")
    if {name: digest(game / name) for name in ARCHIVES} != ARCHIVES:
        raise ValueError("unexpected DOS game archives")
    save_digest = digest(args.save) if args.save else None
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
        if digest(saves / "monkey2.s01") != save_digest:
            raise ValueError("Copied saved game differs from the supplied source")
        command.append("--save-slot=1")
    command.append("monkey2")
    env = os.environ.copy()
    env["PATH"] = str(args.dll_dir) + os.pathsep + env["PATH"]
    if args.headless:
        env.update(SDL_VIDEODRIVER="dummy", SDL_AUDIODRIVER="dummy", SDL_RENDER_DRIVER="software")
    meta = {"room": room, "command": command, "exe_sha256": digest(exe), "archives": ARCHIVES,
            "headless": args.headless, "debugger_equivalent_entry": args.enter_room, "save_sha256": save_digest,
            "version": subprocess.check_output([str(exe), "--version"], cwd=dest, env=env,
                                               text=True, errors="replace").strip()}
    if getattr(args, "native_room7_save", False):
        meta["entry_provenance"] = {
            "method": "loaded_private_save_no_debugger_or_injected_walk",
            "save_origin_verified": False,
            "natural_gameplay_entry_verified": False,
        }
    if args.walk:
        meta["walk"] = args.walk
        (dest / "walk.enabled").touch(exist_ok=False)
        if args.walk == "control":
            (dest / "walk-control.enabled").touch(exist_ok=False)
    (dest / "run.json").write_text(json.dumps(meta, indent=2), encoding="utf8")
    if args.enter_room:
        (dest / f"enter-room{room}.enabled").touch(exist_ok=False)
    (dest / "capture.enabled").touch(exist_ok=False)
    with (dest / "console.log").open("xb") as log:
        proc = subprocess.Popen(command, cwd=dest, env=env, stdout=log, stderr=log)
        deadline = time.monotonic() + args.timeout
        try:
            while proc.poll() is None and time.monotonic() < deadline:
                if (dest / "present-087.bin").exists() and (dest / f"scummbucket-p4-room{room}.raw.log").exists():
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
    parser.add_argument("--room", type=int, choices=(7, 23), default=23)
    parser.add_argument("--walk", choices=("normal", "control"))
    parser.add_argument("--enter-room", action="store_true")
    parser.add_argument(
        "--native-room7-save", action="store_true",
        help="Require a private Room 7 saved-game capture without debugger jump or research walk; "
             "save origin remains unverified",
    )
    parser.add_argument("--headless", action="store_true")
    parser.add_argument("--timeout", type=int, default=120)
    run(parser.parse_args())
