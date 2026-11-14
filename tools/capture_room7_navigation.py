"""Launch the private navigation build from a verified save. Quit normally to finish."""
import argparse
import json
import os
from pathlib import Path
import shutil
import subprocess
from types import SimpleNamespace
from uuid import uuid4

from tools.run_room23_frames import ARCHIVES, digest, validate_native_room7_save


def add_script_trace_flags(cmd):
    """Enable SCUMM's legacy debugC channels without suppressing debug() output.

    Scumm::debugC(DEBUG_OPCODES, ...) forwards to global debug(), which returns
    immediately if --debug-channels-only is set. Do not silently lose traces.
    """
    if "--debug-channels-only" in cmd:
        raise ValueError("SCUMM opcode trace is incompatible with --debug-channels-only")
    if not cmd or not cmd[-1] == "monkey2":
        raise ValueError("Expected monkey2 target last in doorway launch command")
    return [*cmd[:-1], "--debugflags=SCRIPTS,OPCODES", "--dump-scripts", cmd[-1]]


def capture(root, build, *, doorway=False, script_trace=False):
    if script_trace and not doorway:
        raise ValueError("Script trace requires the continuous doorway capture")
    fixture = root / "FIXTURE"
    game = fixture / "GAMES/MonkeyIsland2_DOS_VGA"
    save = game / "monkey2-1.s01"
    exe = root / "TOOLS" / build / "scummvm.exe"
    dest = fixture / "CAPTURES/Room7" / (("doorway-" if doorway else "navigation-") + uuid4().hex)
    args = SimpleNamespace(native_room7_save=True, room=7, save=save, enter_room=False, walk=None)
    state = validate_native_room7_save(args, exe, game, dest)
    if digest(save) != "39035338ed89bdfe754f31e390f247c83095f1938aeae6877c0373ad7f72aa0d":
        raise ValueError("Unexpected Room 7 save")
    if any(digest(game / name) != expected for name, expected in ARCHIVES.items()):
        raise ValueError("Unexpected DOS VGA archives")
    if doorway and digest(exe) != (exe.parent / "doorway-exe.sha256").read_text().strip():
        raise ValueError("Doorway build digest mismatch")
    dest.mkdir(exist_ok=False)
    if script_trace:
        (dest / "dumps").mkdir(exist_ok=False)
    saves = dest / "saves"
    saves.mkdir()
    shutil.copyfile(save, saves / "monkey2.s01")
    if digest(saves / "monkey2.s01") != digest(save):
        raise ValueError("Save copy differs")
    ini = dest / "scummvm.ini"
    ini.write_text(f"[scummvm]\ngfx_mode=surfacesdl\nautosave_period=0\nsavepath={saves}\n"
                   f"[monkey2]\nengineid=scumm\ngameid=monkey2\nplatform=pc\nlanguage=en\n"
                   f"render_mode=vga\npath={game}\n", encoding="utf8")
    cmd = [str(exe), f"--config={ini}", f"--logfile={dest / 'runtime.log'}", "--save-slot=1",
           "--scaler=normal", "--scale-factor=1", "--no-aspect-ratio", "--no-fullscreen",
           "--no-filtering", "--stretch-mode=center", "--debuglevel=3", "--music-driver=auto", "monkey2"]
    if script_trace:
        cmd = add_script_trace_flags(cmd)
    (dest / "run.json").write_text(json.dumps(dict(command=cmd, exe_sha256=digest(exe),
        archives=ARCHIVES, save=state, input_method="ordinary game controls",
        **({"script_trace": "SCUMM SCRIPTS and OPCODES debug channels; private script dumps"} if script_trace else {}),
        **({"capture_mode": "doorway", "limit_ticks": 2400, "limit_presents": 4800}
        if doorway else {"limit_room_frames": 2400})),
        indent=2), encoding="utf8")
    (dest / ("doorway.enabled" if doorway else "capture.enabled")).touch(exist_ok=False)
    env = os.environ.copy()
    env["PATH"] = "C:/msys64/ucrt64/bin" + os.pathsep + env["PATH"]
    print(dest, flush=True)
    with (dest / "console.log").open("xb") as log:
        subprocess.run(cmd, env=env, cwd=dest, stdout=log, stderr=log, check=True)
    if doorway:
        from tools.room7_doorway import finish
        report = fixture / "REPORTS/Room7" / dest.name
        finish(root, dest, report)
        if script_trace:
            from tools.analyze_room7_script_trace import analyze
            analyze(dest, report)
        return report
    if not (dest / "engine-001.bin").is_file() or b"\nnavigation " not in (
            dest / "engine-001.bin").read_bytes().partition(b"\nDATA\n")[0]:
        raise ValueError("Navigation hook did not produce a frame")
    from tools.analyze_room7_navigation import analyze
    analyze(fixture, dest, fixture / "REPORTS/Room7" / dest.name)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--build", default="ScummVM-P4-Room7-Navigation-20261114-a")
    args = parser.parse_args()
    capture(args.root.resolve(), args.build)
