# P4 Room 23 — Windows capture runbook (ScummVM v2026.4.0)

**Status, 2026-11-08:** The first actual MSYS2 UCRT64 build of the V1 hook reached the SCUMM engine compiler, then failed because `common/forbidden.h` blocks `FILE`, `fprintf`, `fopen`, `fclose`, `fputc`, and `getenv` in engine code. The V2 hook now uses ScummVM-native `Common::DumpFile`; guarded in-place V1-to-V2 upgrades are supported. **The corrected V2 full Windows compile and real engine capture are not yet verified.** Game assets remain outside Git.

This runbook uses a separate experimental ScummVM checkout so the original ScummVM installation and original game archives stay untouched.

## 1. Windows PowerShell — clone, pin and instrument

Requires Git and Python available in PowerShell. Commands work regardless of the starting PowerShell directory:

~~~powershell
cd "C:\Users\87otl\ScummBucket"
git fetch origin
git switch research/p4-engine-palette-trace
git pull --ff-only origin research/p4-engine-palette-trace

python -m unittest discover -s tests -p "test_engine_trace_bridge.py" -v
python -m unittest discover -s tests -p "test_palette_trace.py" -v

powershell -NoProfile -ExecutionPolicy Bypass -File ".\tools\setup_scummvm_trace.ps1"
~~~

This script clones ScummVM v2026.4.0 into C:\Users\87otl\ScummVM-P4-Trace, checks both the exact tag commit and the original C++ blob fingerprint, and installs only the guarded palette hook, retaining an original-source backup. It can also **upgrade the failed V1 hook to V2 in an existing checkout**, if source and backup match the exact generated files; no new clone is needed. An existing different checkout is refused, not overwritten.

Expected in a fresh checkout: `PATCH_APPLICABLE`, `PATCH_APPLIED`, and the pinned commit SHA. Expected when repairing the V1 compile failure: `UPGRADE_APPLICABLE`, then `PATCH_UPGRADED_V1_TO_V2`. If V2 is already present, expect `PATCH_ALREADY_CURRENT`. Stop if tests or source guards fail.

## 2. MSYS2 UCRT64 terminal — minimal SCUMM-only build

Install [MSYS2](https://www.msys2.org/) if needed. Open the **MSYS2 UCRT64** terminal, not ordinary PowerShell or the MSYS2 MSYS terminal. Follow the [MSYS2 update instructions](https://www.msys2.org/), typically by running pacman -Syu, restarting the terminal if prompted, then completing updates.

Run:

~~~bash
pacman -S --needed base-devel git mingw-w64-ucrt-x86_64-gcc mingw-w64-ucrt-x86_64-SDL2 mingw-w64-ucrt-x86_64-pkgconf

bash /c/Users/87otl/ScummBucket/tools/build_scummvm_trace_msys2.sh /c/Users/87otl/ScummVM-P4-Trace
~~~

The build script checks UCRT64, the compiler, SDL2, and presence of our source hook. It runs ScummVM's own configure script (only the SCUMM engine) and make -j 4, then checks that the compiled scummvm.exe exists. No existing executable is replaced.

**Windows compilation has not been run by the assistant.** If it fails, capture the earliest compiler or linker error so the exact dependency or source incompatibility can be resolved. Do not disable the source pinning or silently modify hook logic.

## 3. Windows PowerShell — actual default-cadence palette capture

The original MI2 files are expected under D:\old\mi2 (both MONKEY2.000 and MONKEY2.001). The helper verifies that MONKEY2.001 has SHA-256 ad045372e0d49626503bb50fca29a687ec8e01ef75d9b8bca702a366d143819e before launch.

~~~powershell
cd "C:\Users\87otl\ScummBucket"
powershell -NoProfile -ExecutionPolicy Bypass -File ".\tools\run_scummvm_palette_capture.ps1" -Mode normal
~~~

The helper launches the patched exe, sets the private trace output environment variable, and adds the standard MSYS2 UCRT64 DLL directory to the process PATH.

In the patched ScummVM window:

- Add/start the original DOS VGA MI2 game directory if needed.
- From a room other than 23, open the debugger (normally Ctrl+Alt+D).
- Enter these two debugger commands, in order: **scumm_vars[19] 6**, then **room 23**.
- The room-jump command itself exits the debugger. Do not type continue afterward.
- Stay in Room 23 for at least 256 callbacks (nominally about 26 seconds), or move to another nonzero room and allow another engine update to close the trace. Then quit the patched ScummVM.

The corrected V2 engine writes a single file named `scummbucket-p4-room23.raw.log` **in the experimental ScummVM checkout's working directory** using `Common::DumpFile` (no `getenv`/C stdio). Before launch the PowerShell helper refuses an existing file; after ScummVM exits it moves the raw log into a uniquely timestamped gitignored export location, preserving even incomplete attempts. It then checks for a complete raw log, imports the exact palette samples, and runs the strict model comparator.

Each run gets new, non-overwriting outputs:

- exports/room23-normal-TIMESTAMP.raw.log
- reports/room23-normal-TIMESTAMP.trace.json
- reports/room23-normal-TIMESTAMP.verify.json

If no hook log appears, the eligible engine/capture conditions may not have been reached. If the log lacks an END record, it remains evidence of an incomplete run, not a success.

## 4. Repeat at the experimental 60-unit interval

Use a **new patched ScummVM process** for the second log:

~~~powershell
cd "C:\Users\87otl\ScummBucket"
powershell -NoProfile -ExecutionPolicy Bypass -File ".\tools\run_scummvm_palette_capture.ps1" -Mode stress
~~~

Open the debugger from a different room and enter **scumm_vars[19] 60** followed by **room 23**. At approximately one callback per second, collecting all 256 samples takes roughly 4.3 minutes. For a shorter stress capture, return to the debugger after several updates, enter **room 22** and allow a subsequent nonzero-room engine update to close the logger with a room_exit END record. Then exit the patched game.

The earlier 1-Hz debugger test showed that the engine timer override persisted and the water animation became visually abrupt. This experiment now records the **actual ordered RGB palettes**, including transitional timer pairs.

## Result handling and limitations

- The first V1 compile failed on forbidden standard-library APIs; that cause is now addressed in V2 but the new full build needs verification. Preserve the **first new** error if one appears.
- A failed import or mismatch in palette comparison is a research finding, not something to hide or fix by changing the expected data.
- The capture is limited to DOS VGA Monkey Island 2, Room 23; it does not include final layered compositing, object or actor movement.
- The captured initial palette may differ from the static room CLUT after script execution; our verifier reports an explicit initial-state mismatch.
- Engine timestamps are callback times, not guaranteed display/vsync times.
- No original proprietary game archive, patched engine binary or raw trace should be committed.

See [engine capture protocol](P4_SCUMMVM_ENGINE_TRACE_CAPTURE.md), [scheduler evidence](P4_ROOM23_SCHEDULER_SWEEP.md), [pinned patcher](../../tools/instrument_scummvm_palette.py), [trace importer](../../scummbucket/engine_trace_import.py), [upstream source](https://github.com/scummvm/scummvm/tree/v2026.4.0) and [official MSYS2 packages](https://packages.msys2.org/).
