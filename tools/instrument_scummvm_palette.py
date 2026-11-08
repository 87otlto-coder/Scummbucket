"""Install/remove a guarded, opt-in palette trace hook in pinned ScummVM source.

Targets ScummVM v2026.4.0 engines/scumm/scumm.cpp only. Does not compile,
execute, or alter commercial game data. Refuses unrecognized source versions.
"""
from __future__ import annotations

import argparse
import hashlib
import os
from pathlib import Path
import sys

PINNED_TAG = "v2026.4.0"
PINNED_CPP_BLOB = "d1baa70b008c425f5b2b6693509e738d81e5af19"
TARGET_RELATIVE = Path("engines/scumm/scumm.cpp")
BACKUP_SUFFIX = ".scummbucket-p4-original"
MARKER = "SCUMMBUCKET_P4_PALETTE_TRACE_V1"
ANCHOR = ("void ScummEngine::scummLoop_handleEffects() {\n"
          "\tif (_game.version >= 4 && _game.heversion <= 62)\n"
          "\t\tcyclePalette();\n"
          "\tpalManipulate();\n")

HOOK = r'''void ScummEngine::scummLoop_handleEffects() {
	// SCUMMBUCKET_P4_PALETTE_TRACE_V1: private, opt-in instrumentation.
	// Run only on original DOS MI2 VGA and only when the environment variable
	// SCUMMBUCKET_PALETTE_TRACE_PATH points to a NEW writable file.
	static std::FILE *sbP4Trace = nullptr;
	static bool sbP4Attempted = false;
	static unsigned sbP4Count = 0;
	const bool sbP4Eligible = _game.id == GID_MONKEY2 && _game.version == 5 &&
		_game.platform == Common::kPlatformDOS && _currentRoom == 23 &&
		!_enableEGADithering;
	if (sbP4Trace && !sbP4Eligible) {
		std::fprintf(sbP4Trace, "SBP4|END|%u|room_exit\n", sbP4Count);
		std::fclose(sbP4Trace);
		sbP4Trace = nullptr;
	}
	if (sbP4Eligible && !sbP4Attempted) {
		sbP4Attempted = true;
		const char *path = std::getenv("SCUMMBUCKET_PALETTE_TRACE_PATH");
		if (path && *path) {
			std::FILE *existing = std::fopen(path, "rb");
			if (existing) {
				std::fclose(existing);
				warning("ScummBucket P4: trace output exists; refusing to overwrite");
			} else {
				sbP4Trace = std::fopen(path, "wb");
				if (!sbP4Trace)
					warning("ScummBucket P4: cannot open requested trace output");
			}
		}
		if (sbP4Trace) {
			std::fprintf(sbP4Trace, "SBP4|BEGIN|23|%u|",
				static_cast<unsigned>(_system->getMillis()));
			for (unsigned k = 0; k < 768; ++k)
				std::fprintf(sbP4Trace, "%02x", static_cast<unsigned>(_currentPalette[k]));
			std::fputc('\n', sbP4Trace);
			std::fflush(sbP4Trace);
		}
	}
	if (_game.version >= 4 && _game.heversion <= 62)
		cyclePalette();
	// Capture immediately AFTER cyclePalette() and BEFORE palManipulate().
	if (sbP4Eligible && sbP4Trace) {
		++sbP4Count;
		const int sbTimer = VAR_TIMER != 0xFF ? VAR(VAR_TIMER) : -1;
		const int sbTimerNext = VAR_TIMER_NEXT != 0xFF ? VAR(VAR_TIMER_NEXT) : -1;
		std::fprintf(sbP4Trace, "SBP4|SAMPLE|%u|%d|%d|%u|",
			sbP4Count, sbTimer, sbTimerNext,
			static_cast<unsigned>(_system->getMillis()));
		for (unsigned k = 0; k < 768; ++k)
			std::fprintf(sbP4Trace, "%02x", static_cast<unsigned>(_currentPalette[k]));
		std::fputc('\n', sbP4Trace);
		if (sbP4Count == 256) {
			std::fprintf(sbP4Trace, "SBP4|END|256|limit\n");
			std::fclose(sbP4Trace);
			sbP4Trace = nullptr;
		} else {
			std::fflush(sbP4Trace);
		}
	}
	palManipulate();
'''

INCLUDE_ANCHOR = '#include "common/config-manager.h"\n'
INCLUDE_REPLACE = ('// SCUMMBUCKET_P4_PALETTE_TRACE_V1\n'
                   '#include <cstdio>\n#include <cstdlib>\n'
                   '#include "common/config-manager.h"\n')


class PatchError(ValueError):
    pass


def git_blob_sha(content: bytes) -> str:
    return hashlib.sha1(b"blob " + str(len(content)).encode("ascii") +
                        b"\0" + content).hexdigest()


def patch_source(raw: bytes) -> bytes:
    """Return patched source only if source blob and exact anchors are pinned."""
    newline = b"\r\n" if b"\r\n" in raw else b"\n"
    source = raw.replace(b"\r\n", b"\n")
    if git_blob_sha(source) != PINNED_CPP_BLOB:
        raise PatchError("SOURCE_VERSION_MISMATCH: expected ScummVM v2026.4.0 "
                         f"scumm.cpp Git blob {PINNED_CPP_BLOB}; got {git_blob_sha(source)}")
    content = source.decode("utf-8")
    if content.count(ANCHOR) != 1 or content.count(INCLUDE_ANCHOR) != 1:
        raise PatchError("SOURCE_ANCHOR_MISMATCH: pinned palette hook anchors not unique")
    patched = content.replace(ANCHOR, HOOK, 1).replace(INCLUDE_ANCHOR, INCLUDE_REPLACE, 1)
    binary = patched.encode("utf-8")
    return binary.replace(b"\n", newline) if newline == b"\r\n" else binary


def apply_patch(scummvm_root: Path, *, check: bool = False, restore: bool = False) -> str:
    target = scummvm_root / TARGET_RELATIVE
    backup = target.with_name(target.name + BACKUP_SUFFIX)
    if not target.is_file() or target.is_symlink() or backup.is_symlink():
        raise PatchError(f"SOURCE_MISSING_OR_SYMLINK: {target}")
    if restore:
        if not backup.is_file():
            raise PatchError("BACKUP_MISSING: cannot restore without original backup")
        original = backup.read_bytes()
        if git_blob_sha(original.replace(b"\r\n", b"\n")) != PINNED_CPP_BLOB:
            raise PatchError("BACKUP_INVALID: original backup has unexpected version")
        if target.read_bytes() != patch_source(original):
            raise PatchError("PATCHED_SOURCE_CHANGED: refusing to erase further edits")
        os.replace(backup, target)
        return f"RESTORED: {target}"
    raw = target.read_bytes()
    if MARKER.encode() in raw:
        raise PatchError("ALREADY_INSTRUMENTED: restore first; no double patch")
    patched = patch_source(raw)
    if backup.exists():
        raise PatchError(f"BACKUP_COLLISION: {backup}")
    if check:
        return f"PATCH_APPLICABLE: {target} ({PINNED_TAG})"
    with backup.open("xb") as f:
        f.write(raw)
    try:
        with target.open("wb") as f:
            f.write(patched)
    except OSError:
        os.replace(backup, target)
        raise
    return f"PATCH_APPLIED: {target} (original backup: {backup})"


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("scummvm_root", type=Path, help="Source checkout of ScummVM v2026.4.0")
    action = p.add_mutually_exclusive_group(required=True)
    action.add_argument("--check", action="store_true", help="Check pinned source anchors; do not modify")
    action.add_argument("--apply", action="store_true", help="Patch source, retaining non-overwriting backup")
    action.add_argument("--restore", action="store_true", help="Restore original backup")
    args = p.parse_args(argv)
    try:
        print(apply_patch(args.scummvm_root, check=args.check, restore=args.restore))
        return 0
    except (PatchError, OSError, UnicodeError) as exc:
        print(f"ERROR {type(exc).__name__}: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
