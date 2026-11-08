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
MARKER = "SCUMMBUCKET_P4_PALETTE_TRACE_V2"
LEGACY_MARKER = "SCUMMBUCKET_P4_PALETTE_TRACE_V1"
LOG_FILENAME = "scummbucket-p4-room23.raw.log"
ANCHOR = ("void ScummEngine::scummLoop_handleEffects() {\n"
          "\tif (_game.version >= 4 && _game.heversion <= 62)\n"
          "\t\tcyclePalette();\n"
          "\tpalManipulate();\n")

LEGACY_HOOK = r'''void ScummEngine::scummLoop_handleEffects() {
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
				sbP4Trace = std::fopen(path, "wbx");
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

HOOK = r'''void ScummEngine::scummLoop_handleEffects() {
	// SCUMMBUCKET_P4_PALETTE_TRACE_V2: standalone instrumented engine only.
	// ScummVM deliberately bans C stdio/getenv from engine code.
	// This opt-in research build writes one fixed file in its working directory.
	static Common::DumpFile sbP4Trace;
	static bool sbP4Attempted = false;
	static unsigned sbP4Count = 0;
	const bool sbP4Eligible = _game.id == GID_MONKEY2 && _game.version == 5 &&
		_game.platform == Common::kPlatformDOS && _currentRoom == 23 &&
		!_enableEGADithering;

	if (sbP4Trace.isOpen() && !sbP4Eligible) {
		const Common::String ending = Common::String::format("SBP4|END|%u|room_exit\n", sbP4Count);
		sbP4Trace.write(ending.c_str(), static_cast<uint32>(ending.size()));
		sbP4Trace.flush();
		sbP4Trace.close();
	}

	if (sbP4Eligible && !sbP4Attempted) {
		sbP4Attempted = true;
		const Common::Path path("scummbucket-p4-room23.raw.log");
		if (Common::FSNode(path).exists()) {
			warning("ScummBucket P4: trace file already exists; refusing to overwrite");
		} else if (!sbP4Trace.open(path)) {
			warning("ScummBucket P4: failed to open trace output in engine working directory");
		} else {
			char paletteHex[1536];
			const char hexDigits[] = "0123456789abcdef";
			for (unsigned k = 0; k < 768; ++k) {
				const byte value = _currentPalette[k];
				paletteHex[k * 2] = hexDigits[value >> 4];
				paletteHex[k * 2 + 1] = hexDigits[value & 15];
			}
			const Common::String beginning = Common::String::format("SBP4|BEGIN|23|%u|",
				static_cast<unsigned>(_system->getMillis()));
			sbP4Trace.write(beginning.c_str(), static_cast<uint32>(beginning.size()));
			sbP4Trace.write(paletteHex, 1536);
			sbP4Trace.write("\n", 1);
			sbP4Trace.flush();
		}
	}

	if (_game.version >= 4 && _game.heversion <= 62)
		cyclePalette();

	// Capture immediately AFTER cyclePalette() and BEFORE palManipulate().
	if (sbP4Eligible && sbP4Trace.isOpen()) {
		++sbP4Count;
		const int sbTimer = VAR_TIMER != 0xFF ? VAR(VAR_TIMER) : -1;
		const int sbTimerNext = VAR_TIMER_NEXT != 0xFF ? VAR(VAR_TIMER_NEXT) : -1;
		const Common::String sample = Common::String::format("SBP4|SAMPLE|%u|%d|%d|%u|",
			sbP4Count, sbTimer, sbTimerNext,
			static_cast<unsigned>(_system->getMillis()));
		sbP4Trace.write(sample.c_str(), static_cast<uint32>(sample.size()));
		char paletteHex[1536];
		const char hexDigits[] = "0123456789abcdef";
		for (unsigned k = 0; k < 768; ++k) {
			const byte value = _currentPalette[k];
			paletteHex[k * 2] = hexDigits[value >> 4];
			paletteHex[k * 2 + 1] = hexDigits[value & 15];
		}
		sbP4Trace.write(paletteHex, 1536);
		sbP4Trace.write("\n", 1);
		if (sbP4Count == 256) {
			const Common::String ending("SBP4|END|256|limit\n");
			sbP4Trace.write(ending.c_str(), static_cast<uint32>(ending.size()));
			sbP4Trace.flush();
			sbP4Trace.close();
		} else {
			sbP4Trace.flush();
		}
	}
	palManipulate();
'''

INCLUDE_ANCHOR = '#include "common/config-manager.h"\n'
LEGACY_INCLUDE_REPLACE = ('// SCUMMBUCKET_P4_PALETTE_TRACE_V1\n'
                          '#include <cstdio>\n#include <cstdlib>\n'
                          '#include "common/config-manager.h"\n')
INCLUDE_REPLACE = ('// SCUMMBUCKET_P4_PALETTE_TRACE_V2\n'
                   '#include "common/file.h"\n'
                   '#include "common/config-manager.h"\n')


class PatchError(ValueError):
    pass


def git_blob_sha(content: bytes) -> str:
    return hashlib.sha1(b"blob " + str(len(content)).encode("ascii") +
                        b"\0" + content).hexdigest()


def patch_source(raw: bytes, *, legacy: bool = False) -> bytes:
    """Produce the exact pinned hook; legacy exists only for safe v1 upgrades."""
    newline = b"\r\n" if b"\r\n" in raw else b"\n"
    source = raw.replace(b"\r\n", b"\n")
    if git_blob_sha(source) != PINNED_CPP_BLOB:
        raise PatchError("SOURCE_VERSION_MISMATCH: expected ScummVM v2026.4.0 "
                         f"scumm.cpp Git blob {PINNED_CPP_BLOB}; got {git_blob_sha(source)}")
    content = source.decode("utf-8")
    if content.count(ANCHOR) != 1 or content.count(INCLUDE_ANCHOR) != 1:
        raise PatchError("SOURCE_ANCHOR_MISMATCH: pinned palette hook anchors not unique")
    selected_hook = LEGACY_HOOK if legacy else HOOK
    selected_include = LEGACY_INCLUDE_REPLACE if legacy else INCLUDE_REPLACE
    patched = content.replace(ANCHOR, selected_hook, 1)
    patched = patched.replace(INCLUDE_ANCHOR, selected_include, 1)
    binary = patched.encode("utf-8")
    return binary.replace(b"\n", newline) if newline == b"\r\n" else binary


def _read_pinned_backup(backup: Path) -> bytes:
    if not backup.is_file():
        raise PatchError(f"BACKUP_MISSING: original source backup not found: {backup}")
    original = backup.read_bytes()
    if git_blob_sha(original.replace(b"\r\n", b"\n")) != PINNED_CPP_BLOB:
        raise PatchError("BACKUP_INVALID: original backup has unexpected version")
    return original


def _replace_using_temporary(target: Path, patched: bytes) -> None:
    """Avoid leaving partially overwritten C++ source if a write fails."""
    temporary = target.with_name(target.name + ".scummbucket-p4-staging")
    if temporary.exists() or temporary.is_symlink():
        raise PatchError(f"PATCH_STAGING_COLLISION: {temporary}")
    try:
        with temporary.open("xb") as f:
            f.write(patched)
        os.replace(temporary, target)
    except OSError:
        if temporary.exists():
            temporary.unlink()
        raise


def apply_patch(scummvm_root: Path, *, check: bool = False, restore: bool = False) -> str:
    target = scummvm_root / TARGET_RELATIVE
    backup = target.with_name(target.name + BACKUP_SUFFIX)
    if not target.is_file() or target.is_symlink() or backup.is_symlink():
        raise PatchError(f"SOURCE_MISSING_OR_SYMLINK: {target}")

    raw = target.read_bytes()
    if restore:
        original = _read_pinned_backup(backup)
        if raw not in (patch_source(original), patch_source(original, legacy=True)):
            raise PatchError("PATCHED_SOURCE_CHANGED: refusing to erase further edits")
        os.replace(backup, target)
        return f"RESTORED: {target}"

    if MARKER.encode() in raw:
        original = _read_pinned_backup(backup)
        if raw != patch_source(original):
            raise PatchError("PATCHED_SOURCE_CHANGED: v2 source differs from generated hook")
        if check:
            return f"PATCH_ALREADY_CURRENT: {target}"
        raise PatchError("ALREADY_INSTRUMENTED: v2 hook is already installed")

    if LEGACY_MARKER.encode() in raw:
        original = _read_pinned_backup(backup)
        if raw != patch_source(original, legacy=True):
            raise PatchError("PATCHED_SOURCE_CHANGED: legacy v1 source differs from generated hook")
        if check:
            return f"UPGRADE_APPLICABLE: {target} (v1 -> v2)"
        _replace_using_temporary(target, patch_source(original))
        return f"PATCH_UPGRADED_V1_TO_V2: {target} (original backup preserved: {backup})"

    patched = patch_source(raw)
    if backup.exists():
        raise PatchError(f"BACKUP_COLLISION: {backup}")
    if check:
        return f"PATCH_APPLICABLE: {target} ({PINNED_TAG})"
    with backup.open("xb") as f:
        f.write(raw)
    try:
        _replace_using_temporary(target, patched)
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
