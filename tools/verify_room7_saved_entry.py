"""Read-only evidence gate for a Room 7 capture loaded from an existing save.

This establishes the observed room, integrity of copied save and capture
frames, and absence of the scripted debugger-entry/walk markers. It cannot
prove that the supplied save was reached by natural game progression.
No source game bytes or images are written to this repository.
"""
import argparse
import hashlib
import json
from pathlib import Path
import re

from tools.compare_room23_frames import engine, present
from tools.run_room23_frames import ARCHIVES
from scummbucket.scummvm_save import inspect_scummvm_save

METHOD = "loaded_private_save_no_debugger_or_injected_walk"
HEX64 = re.compile(r"[0-9a-f]{64}\Z")


def sha(path):
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for buf in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(buf)
    return h.hexdigest()


def validate(capture, *, original_save=None, game=None, executable=None,
             expected_frames=87):
    capture = Path(capture).resolve()
    if (capture.parent.name != "Room7" or
            capture.parent.parent.name != "CAPTURES" or
            capture.parent.parent.parent.name != "FIXTURE"):
        raise ValueError("Capture must be in FIXTURE/CAPTURES/Room7/<new-run>")
    if not isinstance(expected_frames, int) or not 1 <= expected_frames <= 87:
        raise ValueError("Expected frame count outside 1..87")
    run = json.loads((capture / "run.json").read_text(encoding="utf8"))
    if run.get("room") != 7 or run.get("archives") != ARCHIVES:
        raise ValueError("Unexpected game edition, source hashes or room")
    if run.get("debugger_equivalent_entry") is not False or "walk" in run:
        raise ValueError("Debugger jump or injected walk is not native save entry")
    provenance = run.get("entry_provenance")
    if not isinstance(provenance, dict) or provenance.get("method") != METHOD:
        raise ValueError("Missing explicit native-save capture provenance")
    if (provenance.get("save_origin_verified") is not False or
            provenance.get("natural_gameplay_entry_verified") is not False):
        raise ValueError("Unsupported claim of verified natural gameplay origin")
    for marker in ("enter-room7.enabled", "enter-room23.enabled",
                   "walk.enabled", "walk-control.enabled"):
        if (capture / marker).exists():
            raise ValueError(f"Injected-entry marker unexpectedly present: {marker}")
    if not (capture / "capture.enabled").is_file():
        raise ValueError("Missing capture-enabled marker")
    if not isinstance(run.get("exe_sha256"), str) or not HEX64.fullmatch(run["exe_sha256"]):
        raise ValueError("Missing pinned ScummVM executable SHA-256")
    save_sha = run.get("save_sha256")
    if not isinstance(save_sha, str) or not HEX64.fullmatch(save_sha):
        raise ValueError("Saved-game fingerprint missing or malformed")
    copied_save = capture / "saves/monkey2.s01"
    if not copied_save.is_file() or sha(copied_save) != save_sha:
        raise ValueError("Copied save does not match run.json fingerprint")
    saved = inspect_scummvm_save(copied_save)
    if saved["current_room"] != 7 or saved["room_resource"] != 7:
        raise ValueError(f"Recorded save is Room {saved['current_room']}, not Room 7")
    if run.get("save_state") != saved:
        raise ValueError("Recorded saved-game state metadata differs from copied save")
    if original_save is not None and sha(Path(original_save)) != save_sha:
        raise ValueError("Original source save differs from captured copy")
    if game is not None:
        root = Path(game)
        if {name: sha(root / name) for name in ARCHIVES} != ARCHIVES:
            raise ValueError("Original DOS archive hashes differ from pinned edition")
    if executable is not None and sha(Path(executable)) != run["exe_sha256"]:
        raise ValueError("ScummVM executable differs from recorded build")

    expected = {f"{n:03}.bin" for n in range(1, expected_frames + 1)}
    for prefix in ("engine", "present"):
        found = {f.name[len(prefix) + 1:] for f in capture.glob(f"{prefix}-*.bin")}
        if found != expected:
            missing, unexpected = expected - found, found - expected
            raise ValueError(f"{prefix} frame inventory mismatch: "
                             f"missing={sorted(missing)}, unexpected={sorted(unexpected)}")

    lines = (capture / "scummbucket-p4-room7.raw.log").read_text(
        encoding="utf8").splitlines()
    begins = [line for line in lines if line.startswith("SBP4|BEGIN|")]
    if len(begins) != 1 or not begins[0].startswith("SBP4|BEGIN|7|"):
        raise ValueError("Missing or inconsistent observed Room 7 trace beginning")
    # The frame-probe records exactly expected_frames engine/present pairs,
    # but the independent palette hook may continue recording until its own
    # sample cap (256). Do not falsely reject a complete 87-frame capture
    # merely because its same-run trace contains more sequential observations.
    # Parse and validate ALL records before pairing only the captured prefix.
    samples = [line.split("|") for line in lines if line.startswith("SBP4|SAMPLE|")]
    if len(samples) < expected_frames:
        raise ValueError(
            f"Expected at least {expected_frames} palette samples for "
            f"{expected_frames} frame pairs; found {len(samples)}"
        )
    for sequence, sample in enumerate(samples, 1):
        if len(sample) != 7 or sample[:2] != ["SBP4", "SAMPLE"]:
            raise ValueError(f"Invalid palette trace sample fields at {sequence}")
        try:
            sample_id, timer, next_timer, millis = map(int, sample[2:6])
            palette = bytes.fromhex(sample[6])
        except ValueError as exc:
            raise ValueError(f"Malformed palette trace sample at {sequence}") from exc
        if sample_id != sequence:
            raise ValueError(
                f"Nonsequential palette trace sample: expected {sequence}, "
                f"got {sample_id}"
            )
        if len(palette) != 768:
            raise ValueError(f"Invalid palette length at sample {sequence}: {len(palette)}")
        if timer < 0 or next_timer < 0 or millis < 0:
            raise ValueError(f"Invalid negative timer/timestamp at sample {sequence}")

    positions, rows, palettes = [], [], set()
    previous_ms = None
    for n, line in enumerate(samples[:expected_frames], 1):
        # Pair only the captured engine/present prefix; the validated tail
        # has no corresponding frame binaries and must not be fabricated.
        try:
            observed_seq, timer, next_timer = (int(t) for t in line[2:5])
            observed_palette = bytes.fromhex(line[6])
        except ValueError as exc:
            raise ValueError(f"Invalid trace sample at frame {n}") from exc
        if observed_seq != n:
            raise ValueError(f"Nonsequential Room 7 palette trace at frame {n}")
        raw = (capture / f"engine-{n:03}.bin").read_bytes()
        display = (capture / f"present-{n:03}.bin").read_bytes()
        meta, stages, back, front, _ = engine(raw, n)
        ms, renderer, rgb = present(display, n)
        if (meta["mask_count"] != 2 or len(back) != 320 * 144 or
                len(front) != 320 * 144 or rgb.size != (320, 200)):
            raise ValueError(f"Unsupported indexed capture geometry at frame {n}")
        if meta["timer_pair"] != [timer, next_timer] or stages[1] != observed_palette:
            raise ValueError(f"Trace timer or palette mismatch at frame {n}")
        cameras = [s.split() for s in meta["state"] if s.startswith("camera ")]
        if len(cameras) != 1 or len(cameras[0]) != 9:
            raise ValueError(f"Missing unique Room 7 camera state at frame {n}")
        try:
            cx, cy, x, y, w, h, ww, wh = map(int, cameras[0][1:])
        except ValueError as exc:
            raise ValueError(f"Invalid camera state at frame {n}") from exc
        if (w, h, ww, wh) != (320, 144, 784, 144) or y != 0 or not 0 <= x <= 464:
            raise ValueError(f"Unexpected Room 7 viewport or panorama at frame {n}")
        if previous_ms is not None and ms < previous_ms:
            raise ValueError(f"Presented timestamps run backwards at frame {n}")
        previous_ms = ms
        positions.append(x)
        palettes.add(hashlib.sha256(stages[3]).hexdigest())
        rows.append({
            "frame": n, "viewport_x": x, "present_ms": ms,
            "engine_sha256": hashlib.sha256(raw).hexdigest(),
            "present_sha256": hashlib.sha256(display).hexdigest(),
            "front_indexed_sha256": hashlib.sha256(front).hexdigest(),
            "actor11_reported": any(s.startswith("actor 11 ") for s in meta["state"]),
        })

    return {
        "schema": "room7-saved-entry-validation/1",
        "status": "capture_structure_verified",
        "evidence": "engine-observed-frame-records-and-save-copy",
        "entry_method": METHOD,
        "natural_gameplay_route_verified": False,
        "independent_scene_reconstruction_verified": False,
        "frames": rows,
        "summary": {
            "frames_checked": len(rows), "indexed_positions_observed": len(rows) * 320 * 144,
            "camera_min_x": min(positions), "camera_max_x": max(positions),
            "distinct_camera_x": len(set(positions)),
            "distinct_final_palettes": len(palettes),
            "actor11_state_records": sum(r["actor11_reported"] for r in rows),
            "copied_save_sha256": save_sha,
            "saved_room": saved["current_room"],
            "save_version": saved["save_version"],
            "save_container": saved["container"],
            "original_save_matched": original_save is not None,
            "original_archives_rehashed": game is not None,
            "executed_binary_rehashed": executable is not None,
            "trace_has_end": any(s.startswith("SBP4|END|") for s in lines),
            "trace_sha256": sha(capture / "scummbucket-p4-room7.raw.log"),
            "trace_samples_total": len(samples),
            "trace_samples_paired_to_frames": expected_frames,
            "trace_samples_unpaired": len(samples) - expected_frames,
            "trace_unpaired_first_sequence": (
                expected_frames + 1 if len(samples) > expected_frames else None
            ),
            "trace_unpaired_last_sequence": (
                len(samples) if len(samples) > expected_frames else None
            ),
            "trace_unpaired_schema_sequence_checked": True,
            "trace_unpaired_engine_compared": False,
        },
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--capture", required=True, type=Path)
    parser.add_argument("--original-save", type=Path)
    parser.add_argument("--game", type=Path)
    parser.add_argument("--exe", type=Path)
    parser.add_argument("--output", type=Path,
                        help="New JSON report under FIXTURE/REPORTS/Room7; never overwrite")
    args = parser.parse_args()
    result = validate(args.capture, original_save=args.original_save,
                      game=args.game, executable=args.exe)
    if args.output:
        dest = args.output.resolve()
        fixture = args.capture.resolve().parents[2]
        if not dest.is_relative_to(fixture / "REPORTS" / "Room7"):
            parser.error("Output must reside under FIXTURE/REPORTS/Room7")
        # Exclusive creation; avoid silent loss of prior evidence.
        with dest.open("x", encoding="utf8") as out:
            json.dump(result, out, indent=2)
    print(json.dumps(result["summary"], indent=2))


if __name__ == "__main__":
    main()
