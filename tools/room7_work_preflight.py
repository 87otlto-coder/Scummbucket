"""Read-only preflight for the limited-usage Room 7 P3/P4 work session.

No project files, game archives, or captures are created or altered.
Runs without third-party Python dependencies. Results are machine-readable JSON.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import sys


EXPECTED = {
    "MONKEY2.000": "cde7aa8980317e3a750fbb3b49884cdddaf1ff3d4231a0c840b22cceed9033f1",
    "MONKEY2.001": "ad045372e0d49626503bb50fca29a687ec8e01ef75d9b8bca702a366d143819e",
}
FRAME_COUNT = 87
EXPECTED_BRANCH = "research/p4-engine-palette-trace"


def file_digest(path: Path) -> str:
    sha = hashlib.sha256()
    with path.open("rb") as stream:
        for buf in iter(lambda: stream.read(1024 * 1024), b""):
            sha.update(buf)
    return sha.hexdigest()


def summarize_report(data: dict, *, expected_frames: int = FRAME_COUNT) -> dict:
    """Summarize existing evidence, without claiming independent actor fidelity."""
    rows = data.get("frames")
    if not isinstance(rows, list):
        raise ValueError("missing frames array")
    if len(rows) != expected_frames:
        raise ValueError(f"expected {expected_frames} frames; received {len(rows)}")
    if any(row.get("id") != i for i, row in enumerate(rows, 1)):
        raise ValueError("frame IDs are not consecutive from 1")
    if data.get("schema") != "room7-sweep/1":
        raise ValueError("unexpected Room 7 report schema")
    if data.get("run", {}).get("room") != 7:
        raise ValueError("not a Room 7 run")
    if data.get("run", {}).get("archives") != EXPECTED:
        raise ValueError("pinned game archive digests differ")
    camera = []
    for row in rows:
        xy = row.get("viewport_xy")
        if not isinstance(xy, list) or len(xy) != 2:
            raise ValueError(f"invalid viewport coordinates for frame {row['id']}")
        camera.append(xy[0])
    fields = ("background", "mask", "front_vs_backend")
    mismatches = {}
    for field in fields:
        mismatches[field] = sum(row.get(field, {}).get("pixels", 0) for row in rows)
    return {
        "frames": len(rows),
        "camera_min_x": min(camera),
        "camera_max_x": max(camera),
        "camera_distinct_x": len(set(camera)),
        "palette_replay_matches": sum(row.get("scheduler_matches") is True for row in rows),
        "mismatch_counts": mismatches,
        "front_vs_background_observations": sum(
            row.get("front_vs_background", {}).get("pixels", 0) for row in rows
        ),
        "debugger_equivalent_entry": data["run"].get("debugger_equivalent_entry"),
        "first_engine_sha256": rows[0].get("engine_sha256"),
        "last_engine_sha256": rows[-1].get("engine_sha256"),
    }


def git_info(repo: Path) -> dict:
    def run(*args: str) -> str:
        result = subprocess.run(
            ["git", "-C", str(repo), *args],
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, check=False
        )
        if result.returncode:
            raise RuntimeError(result.stderr.strip() or "Git command failed")
        return result.stdout.strip()

    return {
        "branch": run("branch", "--show-current"),
        "head": run("rev-parse", "HEAD"),
        "dirty": bool(run("status", "--porcelain")),
        "origin": run("remote", "get-url", "origin"),
    }


def inspect(root: Path, *, hash_frames: bool = False) -> dict:
    results = {
        "schema": "room7-work-preflight/1",
        "root": str(root),
        "status": "blocked",
        "checks": [],
    }

    def note(severity: str, code: str, detail: str) -> None:
        results["checks"].append(dict(severity=severity, code=code, detail=detail))

    for directory in ("SOURCE", "TOOLS", "FIXTURE"):
        if not (root / directory).is_dir():
            note("error", "LAYOUT_MISSING", f"missing required {directory} directory")
    if root.is_dir():
        extra = sorted(
            child.name for child in root.iterdir()
            if child.is_dir() and child.name not in ("SOURCE", "TOOLS", "FIXTURE")
        )
        if extra:
            note("warning", "LAYOUT_EXTRA", f"other top-level directories found: {extra}")

    repo = root / "SOURCE" / "ScummBucket"
    if repo.is_dir() and (repo / ".git").exists():
        try:
            state = git_info(repo)
            results["git"] = state
            if state["branch"] != EXPECTED_BRANCH:
                note("warning", "GIT_BRANCH", f"working branch is {state['branch']!r}")
            if state["dirty"]:
                note("warning", "GIT_DIRTY", "working tree not clean; do not fast-forward automatically")
        except (RuntimeError, OSError) as exc:
            note("error", "GIT_UNAVAILABLE", str(exc))
    else:
        note("error", "GIT_MISSING", f"repository absent: {repo}")

    game = root / "FIXTURE" / "GAMES" / "MonkeyIsland2_DOS_VGA"
    for name, expected in EXPECTED.items():
        path = game / name
        if not path.is_file():
            note("error", "ARCHIVE_MISSING", f"missing {path}")
        else:
            actual = file_digest(path)
            if actual != expected:
                note("error", "ARCHIVE_MISMATCH", f"{name}: SHA-256 {actual}")
            else:
                note("info", "ARCHIVE_VERIFIED", f"{name}: {actual}")

    output = root / "FIXTURE" / "OUTPUT" / "Room7" / "native-20261110-a"
    for name in ("manifest.json", "background.png", "ZP01.png"):
        if not (output / name).is_file():
            note("warning", "PANORAMA_MISSING", f"missing {output / name}")

    report = root / "FIXTURE" / "REPORTS" / "Room7" / "sweep-20261110-a" / "report.json"
    rows = []
    if report.is_file():
        try:
            data = json.loads(report.read_text(encoding="utf-8"))
            results["sweep"] = summarize_report(data)
            rows = data["frames"]
            if any(results["sweep"]["mismatch_counts"].values()):
                note("error", "SWEEP_BASELINE_MISMATCH", "existing background/mask/backend comparison is nonzero")
            if results["sweep"]["palette_replay_matches"] != FRAME_COUNT:
                note("error", "PALETTE_BASELINE_MISMATCH", "palette replay does not match every sample")
            if results["sweep"]["camera_min_x"] != 0 or results["sweep"]["camera_max_x"] != 464:
                note("warning", "CAMERA_RANGE", "camera endpoints differ from prior research")
            if results["sweep"]["debugger_equivalent_entry"] is not True:
                note("warning", "ENTRY_MODE", "this sweep may not be the documented debugger-equivalent run")
        except (OSError, ValueError, KeyError, TypeError) as exc:
            note("error", "REPORT_INVALID", str(exc))
    else:
        note("warning", "REPORT_MISSING", f"private report absent: {report}")

    capture = root / "FIXTURE" / "CAPTURES" / "Room7" / "sweep-20261110-a"
    if capture.is_dir():
        for prefix in ("engine", "present"):
            files = sorted(capture.glob(f"{prefix}-[0-9][0-9][0-9].bin"))
            results[f"{prefix}_frame_count"] = len(files)
            if len(files) != FRAME_COUNT:
                note("warning", "CAPTURE_INCOMPLETE", f"{prefix}: expected {FRAME_COUNT}, found {len(files)}")
        if rows and hash_frames and len(list(capture.glob("engine-[0-9][0-9][0-9].bin"))) == FRAME_COUNT:
            mismatched = []
            for row in rows:
                path = capture / f"engine-{row['id']:03}.bin"
                if file_digest(path) != row["engine_sha256"]:
                    mismatched.append(row["id"])
            if mismatched:
                note("error", "CAPTURE_HASH_MISMATCH", f"engine frames with wrong hash: {mismatched}")
            else:
                note("info", "CAPTURE_HASH_VERIFIED", f"{FRAME_COUNT} engine frame digests matched")
    else:
        note("warning", "CAPTURE_MISSING", f"paired source binaries absent: {capture}")

    if (repo / "tests" / "test_classic_costume.py").is_file():
        note("info", "TESTS_PRESENT", "Room 23 COST regression present")
    else:
        note("warning", "TESTS_MISSING", "Room 23 COST regression not found")
    errors = sum(row["severity"] == "error" for row in results["checks"])
    warnings = sum(row["severity"] == "warning" for row in results["checks"])
    results["status"] = "blocked" if errors else ("partial" if warnings else "ready")
    return results


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path("F:/Dev/SCUMMBUCKET"))
    parser.add_argument("--hash-frames", action="store_true",
                        help="SHA-256 each private engine frame against the existing report")
    args = parser.parse_args(argv)
    result = inspect(args.root.resolve(), hash_frames=args.hash_frames)
    print(json.dumps(result, indent=2))
    return 2 if result["status"] == "blocked" else 0


if __name__ == "__main__":
    sys.exit(main())
