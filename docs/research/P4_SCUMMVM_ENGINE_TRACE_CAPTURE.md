# P4 — Capture actual Room 23 palette/timer samples from ScummVM

**Status:** Instrumentation patcher and strict trace importer implemented and tested with synthetic fixtures. The inserted C++ code has been compiled and exercised in a standalone mock SCUMM engine, **not yet compiled into the full ScummVM application or run against real Monkey Island 2 gameplay**. No engine-derived trace exists yet. The established Room 23 GIF remains a **synthetic** replay reference.

## Source and capture contract

Pinned external source: **ScummVM `v2026.4.0`**, `engines/scumm/scumm.cpp` Git blob SHA-1 `d1baa70b008c425f5b2b6693509e738d81e5af19`. ScummVM code is third-party GPL; the project stores only our small patch *generator*, not a fork, game archive or binary. If upstream source differs, the patcher refuses to modify it. The normal ScummVM installation is not patched.

The ScummVM code path for SCUMM v5 is:

- `scummLoop(int delta)` puts the engine delta into `VAR_TIMER` before script processing;
- `cyclePalette()` derives its increment as `max(VAR(VAR_TIMER), VAR(VAR_TIMER_NEXT))`, checks cycle delays and conditionally rotates entries;
- `scummLoop_handleEffects()` calls `cyclePalette()` and then `palManipulate()`.

The injected hook, in that *second* function, captures `_currentPalette` immediately **before the first `cyclePalette()` call in Room 23** and after each such call, but **before `palManipulate()`**. It also reads the actual `VAR_TIMER`, `VAR_TIMER_NEXT` values and `_system->getMillis()` on every call. The hook does not interfere with cycle logic or modify the source/game archives.

It is opt-in via the `SCUMMBUCKET_PALETTE_TRACE_PATH` environment variable and limited to original **DOS Monkey Island 2**, SCUMM v5, room **23**, non-EGA-dithered renderer. It records at most **256 consecutive calls**; it closes the log with `END|256|limit`, or with `END|N|room_exit` when the game leaves the room. It refuses to overwrite an existing raw log. It writes no raw game files, scripts, sound or images, only the active 768-byte RGB palette per sample and timer values. The trace is private and must not be committed.

**Limitations:** The clock observations are timestamps from ScummVM's `OSystem::getMillis()` at the call site, not guaranteed presentation/vsync timestamps. The first palette may already have been altered by entry scripts or debugger room-jumping; our comparer reports `TRACE_INITIAL_PALETTE_MISMATCH` rather than inventing a baseline. Consecutive calls can be affected by room scripts. A successful trace comparison still does not establish exact display-frame scheduling or composition. A developer build (or compatible instrumentation) is necessary: the stock ScummVM debugger does not emit these RGB arrays.

## Stage 1 — prepare a separate ScummVM source checkout (Windows)

This is an **additional source checkout**, not the existing ScummBucket folder. Use a separate directory, and **do not replace your installed ScummVM executable**.

```powershell
$scummvm = "C:\Users\87otl\ScummVM-P4-Trace"
git clone https://github.com/scummvm/scummvm.git "$scummvm"
git -C "$scummvm" checkout --detach v2026.4.0
git -C "$scummvm" rev-parse HEAD

Push-Location "C:\Users\87otl\ScummBucket"
git fetch origin
git switch research/p4-engine-palette-trace
git pull --ff-only origin research/p4-engine-palette-trace

python tools/instrument_scummvm_palette.py "$scummvm" --check
python tools/instrument_scummvm_palette.py "$scummvm" --apply
Pop-Location
```

`--apply` creates `engines/scumm/scumm.cpp.scummbucket-p4-original`, never silently overwrites that backup, and refuses already-modified source. `--restore` restores the original **only if the patched file still exactly matches our generated patch**; it will not erase subsequent manual changes.

**Compile the patched source** using the upstream ScummVM Windows build instructions from [ScummVM's compiling documentation](https://wiki.scummvm.org/index.php?title=Compiling_ScummVM). The generator does **not** compile ScummVM and does not install an executable. The complete native Windows build and third-party dependencies must be handled through the upstream build workflow. The code was syntax-checked with a C++11 standalone harness, but a complete ScummVM build remains an explicit acceptance check. Please record any compiler errors without silently altering or weakening the trace hook.

## Stage 2 — capture the private engine log

Use the **compiled patched executable**, not your existing system ScummVM shortcut. Keep the game set to VGA with EGA dithering off; try natural room entry, or use the debugger's `room 23` command but record that it was a debugger jump. When Room 23 is active, remain there long enough to record 256 palette calls, or leave the room normally. Quitting the process *before* either closing condition may leave an incomplete log; import deliberately fails in that case.

```powershell
$stamp = Get-Date -Format 'yyyyMMdd-HHmmss'
$raw = "C:\Users\87otl\ScummBucket\exports\room23-scummvm-$stamp.raw.log"
$env:SCUMMBUCKET_PALETTE_TRACE_PATH = $raw

# Replace with the actual path to YOUR patched build's executable:
& "C:\path\to\patched-build\scummvm.exe"

Remove-Item Env:SCUMMBUCKET_PALETTE_TRACE_PATH
Get-Item "$raw"
Get-Content "$raw" -Tail 1
```

A valid completed log ends with either `SBP4|END|256|limit` or `SBP4|END|N|room_exit`. This text format is an ephemeral interchange: never treat the hex palette bytes as a game source file or infer animation timing from their line count. The importer checks every line and detects missing END records.

## Stage 3 — import the log and compare actual palette states

Use the same ScummBucket checkout and the **exact authorized** `MONKEY2.001` file used by ScummVM. For the previously fingerprinted original DOS VGA sample, its expected SHA-256 was `ad045372e0d49626503bb50fca29a687ec8e01ef75d9b8bca702a366d143819e`.

```powershell
Push-Location "C:\Users\87otl\ScummBucket"
$scummvm = "C:\Users\87otl\ScummVM-P4-Trace"
$engineCommit = (git -C "$scummvm" rev-parse HEAD).Trim().ToLowerInvariant()
$resource = "D:\old\mi2\MONKEY2.001"
$trace = "C:\Users\87otl\ScummBucket\reports\room23-engine-trace-$stamp.json"
$report = "C:\Users\87otl\ScummBucket\reports\room23-engine-verify-$stamp.json"

python -m scummbucket import-scummvm-palette-log "$raw" `
  --resource-file "$resource" --engine-commit "$engineCommit" `
  --expected-source-sha256 "ad045372e0d49626503bb50fca29a687ec8e01ef75d9b8bca702a366d143819e" `
  --output "$trace"

python -m scummbucket verify-palette-trace "D:\old" --room 23 `
  --trace "$trace" --output "$report" --json
Pop-Location
```

The importer computes the **real file SHA-256**, records the raw log fingerprint, validates fixed-width RGB bytes, contiguous sample sequence, bounded counters, monotonic clock stamps, final END count and 256-sample cap. It produces `verify-palette-trace` schema 0.1 and uses exclusive-create output; errors remain visible. The existing verifier independently reads the original archive, checks the source SHA, the original CLUT, then compares every 768-byte RGB palette against a model advanced by the **actual captured timer values**. Do not assume success: the first mismatch and diagnostics are research evidence.

The user can upload just the generated JSON trace and JSON verification report. The original game archives, patched executable and source extraction files need not be uploaded or committed. Trace palette contents are derived from gameplay; they remain private.

## Implemented tests and open checks

The synthetic bridge tests cover pinning and no-double-patch behavior, backup safety, CRLF handling, 256 samples, missing END and malformed records, integer/timer bounds, source hash comparison, non-overwrite, sample timestamps and malformed log failures. The injected C++ hook was separately compiled/executed in a mock C++11 engine and its output parsed successfully.

**Still outstanding:** Full ScummVM Windows compile, natural-entry versus debugger-jump comparison, real capture, real `verify-palette-trace` results and reconciliation of any `CLUT` / runtime cycle differences. These must remain explicitly unverified until we obtain actual trace evidence.
