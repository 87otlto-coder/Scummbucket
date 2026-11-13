# ScummBucket workspace migration — SOURCE / TOOLS / FIXTURE

**Root: F:\Dev\SCUMMBUCKET**. Exactly three top-level folders, with no extras without user approval.

| Relative location | Contents |
|---|---|
| SOURCE\ScummBucket | Git checkout; source code, tools owned by project, tests, config, research docs |
| TOOLS\ScummVM-P4-Trace | Instrumented external ScummVM source, compiler outputs and scummvm.exe |
| FIXTURE\GAMES\MonkeyIsland2_DOS_VGA | Copy of original DOS VGA MONKEY2.000, MONKEY2.001 and other same-edition files |
| FIXTURE\CAPTURES\Room23 | Raw engine traces, including incomplete recordings |
| FIXTURE\REFERENCE | Reference recordings, screenshots and trusted baselines (when available) |
| FIXTURE\OUTPUT | Generated PNGs, GIFs, sprite sheets and other exported data |
| FIXTURE\REPORTS\Room23 | Imported traces, comparisons and forensic JSON reports |
| FIXTURE\REPORTS\Migration | Copy-and-verification manifest |

Keep system-wide MSYS2 in C:\msys64. Original game files, engine traces and copyright-sensitive resources stay **outside Git**.

## Migration scope

Previously used locations: C:\Users\87otl\ScummBucket (source + outputs); C:\Users\87otl\ScummVM-P4-Trace (compiled experimental engine); D:\old\mi2 (game files). The user created F:\Dev\SCUMMBUCKET with SOURCE, TOOLS and FIXTURE top-level folders.

The repository updates cannot directly move files on the user's Windows computer. A separate user-run PowerShell helper makes **verified copies only**. It never deletes the old source files or automatically overwrites different destination content. It includes a preview and a detailed manifest. Existing paths in older historical evidence reports remain evidence of where the original experiments ran.

## Step 1: pull from the OLD repository (PowerShell)

~~~powershell
cd "C:\Users\87otl\ScummBucket"
git switch research/p4-engine-palette-trace
git pull --ff-only origin research/p4-engine-palette-trace
~~~

Review any uncommitted edits before proceeding. The script copies the working repository, including its .git history, preserving tracked file bytes.

## Step 2: preview, then explicitly apply

First preview without creating destination files:

~~~powershell
powershell -NoProfile -ExecutionPolicy Bypass -File ".\tools\migrate_workspace.ps1"
~~~

It prints the old/new paths and fingerprints the original MI2 edition. If any source differs, supply -OldRepo, -OldEngine, -OldGame or -Root with its correct path.

When the preview is correct, run:

~~~powershell
powershell -NoProfile -ExecutionPolicy Bypass -File ".\tools\migrate_workspace.ps1" -Apply
~~~

The script copies and verifies:

- Git source checkout to SOURCE\ScummBucket. It excludes the repository's old exports/reports, obvious game/archive/media files and ephemeral build/cache output from the code copy.
- Compiled third-party ScummVM checkout into TOOLS\ScummVM-P4-Trace, including scummvm.exe and the patched C++ source. It verifies both SHA256 fingerprints and the source commit.
- Original MI2 game folder into FIXTURE\GAMES\MonkeyIsland2_DOS_VGA, verifying **every copied original game file** and the previously validated MONKEY2.001 SHA256 (ad045372e0d49626503bb50fca29a687ec8e01ef75d9b8bca702a366d143819e).
- Old exports files ending in .raw.log to FIXTURE\CAPTURES\Room23; other old exports to FIXTURE\OUTPUT\LegacyExports, and reports to FIXTURE\REPORTS\LegacyRepoReports. Relative filenames are retained and destination collisions with differing bytes fail.
- A unique FIXTURE\REPORTS\Migration\workspace-copy-*.json verification manifest, with old paths, new paths, commit IDs, fingerprints, copied-file counts, and originals_deleted=false.

A destination folder that already exists is never bulk-overwritten. If interrupted, the partially copied folder is preserved; on rerun, the script checks critical Git and source files rather than replacing them. Resolve unexpected files manually.

**Scope:** This helper classifies old output inside the known repository exports/reports directories. Other stray assets outside those directories are not silently moved and must be inventoried separately. No proprietary game bytes or private traces enter Git.

## Step 3: verify from the NEW source folder

~~~powershell
cd "F:\Dev\SCUMMBUCKET\SOURCE\ScummBucket"
git status --short
git branch --show-current
python -m unittest discover -s tests -p "test_room23_capture_research.py" -v
Test-Path "F:\Dev\SCUMMBUCKET\TOOLS\ScummVM-P4-Trace\scummvm.exe"
Test-Path "F:\Dev\SCUMMBUCKET\FIXTURE\GAMES\MonkeyIsland2_DOS_VGA\MONKEY2.001"
~~~

The expected branch is research/p4-engine-palette-trace; the two Test-Path checks must return True. Inspect the migration manifest under FIXTURE\REPORTS\Migration.

For the known initial incomplete capture (if it was present in the old exports folder), reproduce the analysis using a new, non-overwriting report filename:

~~~powershell
python -m scummbucket analyze-room23-palette-log "F:\Dev\SCUMMBUCKET\FIXTURE\GAMES\MonkeyIsland2_DOS_VGA" --raw-log "F:\Dev\SCUMMBUCKET\FIXTURE\CAPTURES\Room23\room23-normal-20261108-215059-863.raw.log" --output "F:\Dev\SCUMMBUCKET\FIXTURE\REPORTS\Room23\post-migration-normal-phase-check.json" --json
~~~

Expected evidence: 180/180 matches, 172 held-out predictions, status=incomplete because its genuine END record is missing. Exit code 2 is deliberate for that artifact, not a migration failure.

## Step 4: check runtime from the new folders

ScummVM's configured game path may still reference D:\old\mi2; explicitly add or change the patched ScummVM game's path to the copied folder, without deleting the original. The helper cannot edit that UI setting.

~~~powershell
cd "F:\Dev\SCUMMBUCKET\SOURCE\ScummBucket"
powershell -NoProfile -ExecutionPolicy Bypass -File ".\tools\run_scummvm_palette_capture.ps1" -Mode normal
~~~

Raw files now go under FIXTURE\CAPTURES\Room23 and JSON reports under FIXTURE\REPORTS\Room23. System-wide MSYS2 DLLs remain at C:\msys64\ucrt64\bin. There is no need to compile ScummVM again solely because it was copied, although runtime launch still needs testing.

After validating the new paths, the next P4 experiment is a true 60-unit Room 23 trace. Enter room 23, reopen the debugger, set scumm_vars[19] 60, read back 60, then continue. Check the report for real 60/60 callbacks.

**Acceptance:** Git HEAD and tracked file hashes match, game archives match byte-for-byte, experimental executable and hook source match, captures/reports are preserved, tests run, and the copied engine launches. Do not retire old locations until separately approved.
