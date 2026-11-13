# P4 Room 7 — saved-game entry validation protocol (13 November 2026)

**Status:** a controlled next experiment, **not** a natural-gameplay verification result.
The existing 87-frame debugger-equivalent Room 23→7 acceptance is independently
reported in [P4_PRIVATE_ACCEPTANCE_20261113.md](P4_PRIVATE_ACCEPTANCE_20261113.md).
The new tools are designed to retain that baseline unchanged.

## Objective and required human input

Reproduce a Room 7 capture loaded from a **gameplay-created saved game**,
rather than activating the existing debugger-equivalent `--enter-room` marker.
To establish natural gameplay entry, the operator must actually navigate to
Room 7 through normal gameplay and create a **new save slot** at that point,
retaining the original file and recording the route/session. A save copied
from a debugger jump is **not** natural-entry evidence even if the program
can load it and produces a valid capture. The toolkit cannot authenticate
the preceding gameplay route from the save bytes alone.

There are **two distinct execution tracks**:

1. **Original DOS executable in DOSBox**: use the standard copy-protection,
   difficulty, then F5/Load sequence described in
   [the original DOS boot protocol](P4_MI2_ORIGINAL_DOS_BOOT_20261113.md).
   Your existing `SAVEGAME.001` is in this format. This track is necessary to
   observe where that DOS save loads. It does **not** produce a ScummVM capture
   or automatically convert the save.
2. **Instrumented ScummVM in TOOLS**: this document's Python launcher requires
   a **ScummVM v124 save** (optionally gzip-wrapped, with `SCVM` inside).
   It validates both saved room fields and rejects `SAVEGAME.001`
   before writing outputs. Do not rename a DOS save to `monkey2.s01`; the
   formats are not interchangeable.

Use the already instrumented **private ScummVM** build in `TOOLS` only for
ScummVM-format captures; do not modify, delete or redistribute the build,
saves or original game files.

## Step 1 — safely identify the executable and private save

The newly supplied `monkey2.s01` is a valid gzip-wrapped ScummVM v124
save whose stored current room and room resource are both **23**.
It is therefore **not** suitable for direct Room 7 capture. A real
`current_room=7` save is required before using `--native-room7-save`.
See [the serialized save examination](P4_ROOM23_UPLOADED_SCUMMVM_SAVE_20261113.md).

The pinned old debugger-run `run.json` records the executable path in
`command[0]` and its SHA-256. Confirm the existing `TOOLS` file still
matches that digest and determine the path of the **new** user-created saved
game. Do not infer the Room 7 room field from a filename alone.

~~~powershell
$root = 'F:\Dev\SCUMMBUCKET'
$repo = Join-Path $root 'SOURCE\ScummBucket'
$fixture = Join-Path $root 'FIXTURE'
$prior = Get-Content -LiteralPath (Join-Path $fixture 'CAPTURES\Room7\sweep-20261110-a\run.json') -Raw | ConvertFrom-Json
$exe = [string]$prior.command[0]
if (-not (Test-Path -LiteralPath $exe -PathType Leaf)) { throw 'Pinned private executable missing' }
$actual = (Get-FileHash -LiteralPath $exe -Algorithm SHA256).Hash.ToLowerInvariant()
if ($actual -ne $prior.exe_sha256) { throw 'Private executable differs from the pinned build' }

# Provide the actual new gameplay-created save path; no placeholder is accepted.
$save = 'REPLACE_WITH_PRIVATE_SAVE_PATH'
if (-not (Test-Path -LiteralPath $save -PathType Leaf)) { throw 'Save file missing' }
~~~

## Step 2 — create a new, explicitly saved-game capture

Execute from `SOURCE\ScummBucket`. New outputs must stay in
`FIXTURE\CAPTURES\Room7`, which is deliberately outside Git.
The launcher checks original DOS archive hashes before writing,
copies the save without altering it and refuses an existing output directory.
`--native-room7-save` rejects `--enter-room` and `--walk` and stamps
the resulting `run.json` with **unverified natural-route provenance**.

~~~powershell
Set-Location $repo
$runId = 'native-save-' + [guid]::NewGuid().ToString('N')
$capture = Join-Path $fixture ('CAPTURES\Room7\' + $runId)
python -B -m tools.run_room23_frames --room 7 --native-room7-save --headless --game (Join-Path $fixture 'GAMES\MonkeyIsland2_DOS_VGA') --exe $exe --save $save --output $capture
if ($LASTEXITCODE -ne 0) { throw 'Saved-game Room 7 capture failed; inspect private capture diagnostics' }
~~~

This mode does **not** create a debugger-entry marker or research walking
marker. The private ScummVM instrumentation must observe and capture Room 7
normally. If the save was made in another room, the capture should fail
rather than silently jump to the requested room.

## Step 3 — read-only validate the real evidence

The saved-entry validator fingerprints the copied original save, checks the
original game/executable bytes when paths are supplied, checks both sets
of 87 frame binaries and their structure, matches Room 7 camera geometry
and the engine frame timer/post-cycle palette to the source trace. It creates
a new metadata-only report **only** at an explicitly supplied path.

~~~powershell
$report = Join-Path $fixture ('REPORTS\Room7\' + $runId + '-gate.json')
python -B -m tools.verify_room7_saved_entry --capture $capture --original-save $save --game (Join-Path $fixture 'GAMES\MonkeyIsland2_DOS_VGA') --exe $exe --output $report
if ($LASTEXITCODE -ne 0) { throw 'Saved-game evidence gate failed' }
~~~

The validator reports `natural_gameplay_route_verified: false` by design:
that remains a separately documented **human-observed gameplay fact**.
It reports `independent_scene_reconstruction_verified: false` until a
source-derived scene comparator is run against these **new** engine buffers.

## Step 4 — independently compare the saved-entry room image

Only after the gate above passes, create a **new**, non-overwriting output
under `FIXTURE/REPORTS/Room7` with the existing archive-backed comparator:

~~~powershell
$comparison = Join-Path $fixture ('REPORTS\Room7\' + $runId + '-scene')
python -B -m tools.compare_room7 $capture (Join-Path $fixture 'OUTPUT\Room7\native-20261110-a') $comparison
if ($LASTEXITCODE -ne 0) { throw 'Room 7 background/mask or palette comparison failed' }
~~~

This comparison establishes background, depth-mask, backend/viewport and
palette replay agreement for the *new saved-game capture*. It does **not**
independently compose all actors into the front plane, and conditional object
state, timing and visibility may differ from the 87-frame debugger baseline.
Preserve mismatches as evidence and investigate them rather than editing the
source game or labeling an unsupported layer as matched.

**Do not merge draft PR #8** on the strength of this protocol alone.
Licensing/attribution and broader entry-route coverage remain separate gates.
