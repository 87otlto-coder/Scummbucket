"""Recover cross-room metadata acceptance from an existing private capture.

No ScummVM launch, make, game modifications, FFmpeg, image export, deletion
or overwriting of original capture/report files. Missing reports are
generated from the previously recorded raw traces, in-place. Existing
report files are *not overwritten* and are treated as preserved evidence.
"""
import argparse
from hashlib import sha256
import json
from pathlib import Path
import re
import sys

from tools.analyze_room7_script_trace import analyze as analyze_scripts
from tools.verify_cross_room_capture import verify as verify_indices
from tools.run_room23_frames import ARCHIVES, digest


CAPTURE_NAME = re.compile(r"cross-room-[0-9a-f]{32}\Z")


def recover(root, capture):
    root=Path(root).resolve()
    capture=Path(capture).resolve()
    fixture=root/"FIXTURE"
    expected=fixture/"CAPTURES"/"Room7"
    if capture.parent!=expected or not CAPTURE_NAME.fullmatch(capture.name):
        raise ValueError("Refusing capture outside the canonical private Room7/cross-room-UUID directory")
    if not capture.is_dir() or capture.is_symlink():
        raise ValueError("Private cross-room capture is missing or is a symlink")
    run=json.loads((capture/"run.json").read_text(encoding="utf-8"))
    if (run.get("capture_mode")!="cross_room" or
        run.get("indexed_rooms")!=[7,12] or
        not run.get("script_trace")):
        raise ValueError("Not the instrumented cross-room opcode+indexed run")
    if not all((capture/name).is_file() for name in ("doorway.enabled","capture.enabled")):
        raise ValueError("Required dual capture markers absent")
    game=fixture/"GAMES"/"MonkeyIsland2_DOS_VGA"
    if run.get("archives")!=ARCHIVES or any(
        digest(game/name)!=expected_hash for name,expected_hash in ARCHIVES.items()):
        raise ValueError("Recorded game archive hashes disagree with original DOS VGA inputs")
    command=run.get("command")
    if not isinstance(command,list) or not command:
        raise ValueError("Original ScummVM command missing from run.json")
    original_exe=Path(command[0]).resolve()
    if (not original_exe.is_file() or
        not original_exe.parent.parent==root/"TOOLS" or
        not original_exe.parent.name.startswith("ScummVM-P4-CrossRoom-") or
        digest(original_exe)!=run.get("exe_sha256")):
        raise ValueError("Recorded cross-room executable is absent or changed")
    linked=json.loads((original_exe.parent/"cross-room-build.json").read_text(encoding="utf-8"))
    if (linked.get("exe_sha256")!=run["exe_sha256"] or
        linked.get("status")!="linked_executable_version_checked_not_runtime_capture" or
        (original_exe.parent/"cross-room-exe.sha256").read_text(encoding="ascii").strip()!=run["exe_sha256"]):
        raise ValueError("Recorded build provenance does not match fingerprint")
    report=fixture/"REPORTS"/"Room7"/capture.name
    if not (report/"doorway.json").is_file() or not (report/"decoded.txt").is_file():
        raise ValueError("Previous doorway/video report incomplete: preserve files and investigate")
    results={}
    # Process both independently, even if one fails. Each validator writes a
    # separate, exclusive JSON acceptance record; never rerender the video.
    stages=(("script", "script_trace.json", analyze_scripts),
            ("indexed", "cross-room-indexed.json", verify_indices))
    for label,filename,action in stages:
        target=report/filename
        if target.exists():
            try:
                evidence=json.loads(target.read_text(encoding="utf-8"))
                # Existing report never silently replaced or presumed genuine.
                if (evidence.get("capture")!=str(capture) or
                    (label=="script" and evidence.get("engine_exe_sha256")!=run["exe_sha256"])):
                    raise ValueError("Existing report provenance differs")
                results[label]=dict(status="preexisting_report_preserved",
                                    report=str(target),
                                    source_status=evidence.get("status"))
            except (ValueError,KeyError,UnicodeDecodeError) as exc:
                results[label]=dict(status="FAILED_EXISTING_REPORT",error=str(exc),
                                    report=str(target))
        else:
            try:
                evidence=action(capture,report)
                if not target.is_file():
                    raise ValueError("Verifier returned without creating its exclusive evidence report")
                results[label]=dict(status="verified_in_this_run",
                                    report=str(target),
                                    source_status=evidence.get("status"),
                                    **({"opcode_observations":evidence.get("opcode_observations")}
                                       if label=="script" else
                                       {"indexed_frame_count":evidence.get("indexed_frame_count"),
                                        "room12_actor_draw_counts":evidence.get("room12_actor_draw_counts")}))
            except Exception as exc:
                results[label]=dict(status="FAILED",error=f"{type(exc).__name__}: {exc}",
                                    report=str(target))
    complete=(results.get("script",{}).get("source_status")=="opcode_trace_observed" and
              results.get("indexed",{}).get("source_status")=="indexed_capture_with_actor7_8_observed")
    return dict(status=("postcapture_evidence_complete_scene_fidelity_pending"
                        if complete else "postcapture_evidence_incomplete"),
                capture=str(capture),original_exe_sha256=run["exe_sha256"],
                old_video_report_preserved=True,
                original_raw_capture_untouched=True,
                **results)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root",type=Path,required=True)
    parser.add_argument("--capture",type=Path,required=True)
    args=parser.parse_args()
    result=recover(args.root,args.capture)
    print(json.dumps(result,indent=2))
    return 0 if result["status"]=="postcapture_evidence_complete_scene_fidelity_pending" else 2


if __name__=="__main__":
    raise SystemExit(main())
