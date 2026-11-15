# P4 cross-room first runtime capture: recovered post-processing gate

15 November 2026. Original Monkey Island 2 DOS VGA.
Capture ID: cross-room-e4deddf716114bc9907d5d99e1b85232.
**Status:** doorway/video verification passed; opcode/indexed post-processing
was blocked by validator mode mismatch. Original indexed actor evidence
is NOT YET accepted.

## Raw recording preservation

The operator ran the new independently linked ScummVM 2026.4.0
cross-room build at
TOOLS/ScummVM-P4-CrossRoom-767b677319ce4691953ca06dcf67811c
(source-preserving; executable SHA-256
9f958b151bd4cfde56bf744e867fb37b9907a7ebef8263a2e1047ec9a171d9db).

It created the original capture privately at
FIXTURE/CAPTURES/Room7/cross-room-e4deddf716114bc9907d5d99e1b85232.
The doorway/video verifier completed before a later acceptance-mode error:
"Verified 1227 presentations and 472 engine ticks".
It created the corresponding FIXTURE/REPORTS/Room7/cross-room-e4... report.

The operator uploaded the **report ZIP**, not the raw CAPTURES directory.
The uploaded ZIP SHA-256 is
1735c790be77282fa52e3bf868adc73efe7afd37b2936eae361b42f56ee3ae9d.
It passed its complete ZIP CRC check. The report contains 1,227 indexed-by-time
RGB PNG files, doorway.json, an FFV1 MKV, framehash, ffconcat and video log;
**no engine-*.bin, no present-*.bin, no run.json, no console.log and no
draw_actor records**.

The uploaded doorway.json has 472 continuous numbered engine ticks:
228 in Room 7, 244 in Room 12. Transitions:
7->12 at ticks 149/150; 12->7 at ticks 393/394.
It has 1,227 presentations spanning reported wall clock milliseconds
1,573 to 50,478. A final SDL presentation can reference tick 473 after
the last completed tick 472; this is explicitly permitted by the original
doorway verifier and is not invented as a new engine tick.

Independent post-upload audit:
- Every one of the 1,227 RGB PNGs was decoded and its pixels and timestamp
  compared against the supplied decoded.txt: 0 differences.
- The actual FFV1 MKV was separately decoded with system FFmpeg into
  RGB24 framehashes, independently of the original recording machine.
  All 1,227 frame SHA-256 values and presentation timestamps reproduced:
  0 mismatches.
- These are meaningful **presentation fidelity** checks, but do not
  establish original indexed Room 12 framebuffer correctness.

## Exact cause of post-processing failure

The cross-room launcher wrote run.json with
capture_mode=cross_room and indexed_rooms=[7,12] and enabled both
doorway.enabled and capture.enabled. The prior
tools/analyze_room7_script_trace.py required capture_mode=doorway *exactly*
and threw "Not a script-tracing doorway capture" after video verification
but before its opcode trace and indexed actor validation.

That was an integration-contract bug, **not a demonstrated recorder
failure**. The opcode analyzer now accepts either doorway or cross_room
only with the appropriate script_trace flag, and requires both marker
files and [7,12] for cross_room. Its existing exact room transition
tests and debug-channel evidence requirements remain in force.
Fixture-free Windows tests cover both modes and missing markers.

tools/recover_cross_room_capture.py performs the two unfinished
post-processing gates from the **existing** F-drive raw capture
independently, verifying original game archive and cross-room build
fingerprints before doing anything. Both reports are exclusive:
script_trace.json and cross-room-indexed.json. It does not open ScummVM,
rewrite the original raw capture, re-render FFV1, overwrite any report
or treat parsed indices as full Room 12 scene fidelity.

## Recovery command (Windows PowerShell 5.1)

Run this once from the canonical clean P5 research checkout:

~~~powershell
$ErrorActionPreference = 'Stop'
Set-Location -LiteralPath 'F:\Dev\SCUMMBUCKET\SOURCE\ScummBucket'
$branch='research/p5-cross-room-reconstruction'
if ((git branch --show-current).Trim() -ne $branch) { throw 'Wrong Git branch' }
if (git status --porcelain) { throw 'Dirty source checkout; do not overwrite' }
git fetch origin $branch
if ($LASTEXITCODE -ne 0) { throw 'Git fetch failed' }
git merge --ff-only "origin/$branch"
if ($LASTEXITCODE -ne 0) { throw 'Fast-forward failed' }
$capture='F:\Dev\SCUMMBUCKET\FIXTURE\CAPTURES\Room7\cross-room-e4deddf716114bc9907d5d99e1b85232'
& .\tools\p4_cross_room_acceptance.ps1 -Stage Recover -CaptureDirectory $capture
if ($LASTEXITCODE -ne 0) { throw 'Recovery stage invocation failed' }
~~~

The recover tool prints separate script and indexed statuses. If one
fails, it still attempts the other and retains a structured error.
If a report already exists, the tool checks original capture and build
provenance before treating it as preserved evidence; it never replaces
it or claims it was freshly reverified.

**Acceptance for this capture:** script status
opcode_trace_observed, and indexed status
indexed_capture_with_actor7_8_observed, with positive original indexed
Room 7 and Room 12 counts. Full-scene indexed equality is **not** proved.

If recovered, advance to a new, exclusive comparison report:

~~~powershell
Set-Location -LiteralPath 'F:\Dev\SCUMMBUCKET\SOURCE\ScummBucket'
& .\tools\p4_cross_room_acceptance.ps1 -Stage Compare -CaptureDirectory 'F:\Dev\SCUMMBUCKET\FIXTURE\CAPTURES\Room7\cross-room-e4deddf716114bc9907d5d99e1b85232'
~~~

The indexed compositor is expected to expose further unknowns. On any
nonzero difference count it reports PARTIAL_INDEXED_RECONSTRUCTION,
preserves data and returns nonzero. Only a complete zero-error comparison
across the represented Room 12 engine frames can justify acceptance
for this specific recorded route. Room 34 remains the later holdout.

Do not include original game archives, binaries, actor captures or frames
in Git or public CI artifacts. P4 draft PR #8 and cross-room draft PR #17
remain unmerged.
