# P4 cross-room private acceptance — 15 November 2026

Primary: original Monkey Island 2 DOS VGA. Research implementation branch:
research/p5-cross-room-reconstruction. The standing roadmap P5 remains
**audio**; this cross-room work belongs to the P4 animation milestone.

## Exact scope

Room 7 recorded-route 1,149-frame indexed reconstruction was accepted on the
earlier P4 branch. The Room 23 87-frame palette-background portable package
still needs its private acceptance run. The 15 November cross-room research
verified 1,808 scale values and 747 depth-plane selections across three
ordinary-controls Room 7→12→7 runs; full indexed Room 12 scene rendering is
still **NOT VERIFIED**. Work mode's modified C++ source passed translation-unit
syntax checks but was **not linked or run**.

This iteration provides a non-overwriting Windows build path, separate
cross-room indexed capture mode, strict raw-indexed and actor-state checking,
a source-based ordered actor compositor, and an independent comparison tool.
Only synthetic source CI was run; no private output or complete scene is
declared validated by these source-only tests.

## Implementation

- tools/build_cross_room_recorder.py: checks the original doorway executable
  digest and two pinned source checksums. Generates new UUID-named TOOLS
  source overlay and build directories. Runs Windows make; only a changed
  executable with a successful --version probe earns the new build marker.
  Original ScummVM-P4-Doorway-20261114-b source and executable are untouched.
- tools/capture_cross_room.py: requires the new independently linked build
  and creates a fresh private FIXTURE/CAPTURES/Room7/cross-room-UUID capture.
  It enables **both** doorway.enabled and capture.enabled. Uses an original
  saved entry and ordinary in-game navigation; no debugger teleport or
  synthetic walking input. Raw engine indexes, palettes, scene/tick IDs,
  ordered draw_actor rows, script opcode trace and SDL presentations are
  independently recorded where supported.
- tools/verify_cross_room_capture.py: validates R23E1 indexed buffers,
  actor row schema, explicit scene+tick association, room transition and
  timestamps. Does not assume engine and SDL frame lists are one-to-one.
  A valid capture of actors 7 and 8 is evidence of *observation*, not
  evidence of matching original scene pixels.
- scummbucket/scene_source.py: compose_actor_layers uses ordered observed
  drawing, archive COST cels, actor palette overrides, stopped limbs and
  a per-actor depth mask. A clipped nearer actor restores the **previous
  composite**, not the room's empty background.
- tools/compare_cross_room_scene.py: compares every captured Room 12
  indexed front to independent source composition. Preserves first mismatch
  and bounding box, per-frame hashes, background discrepancies and
  masking-disabled negative controls. Writes PARTIAL_INDEXED_RECONSTRUCTION
  and fails exit status if any unexplained indexed pixel differs.
- tools/p4_cross_room_acceptance.ps1: Windows PowerShell 5.1 stage runner
  with no split-if/else paste needed and no unconditional success text.
  Separate stages: Room23, Preflight, Build, Capture and Compare.

All original game archives, executable copies, source overlays and image
outputs stay outside Git in FIXTURE or TOOLS. The sole research PR #17 is
a **draft, branch-to-branch PR** for Windows source CI only; accepted P4
PR #8 remains untouched and unmerged.

## Setup: real upstream branch, never Work mode's synthetic local Git history

From Windows PowerShell (clean working tree only):

~~~powershell
$ErrorActionPreference = 'Stop'
Set-Location -LiteralPath 'F:\Dev\SCUMMBUCKET\SOURCE\ScummBucket'
if (git status --porcelain) { throw 'Uncommitted changes; do not switch' }
git fetch origin research/p5-cross-room-reconstruction
if ($LASTEXITCODE -ne 0) { throw 'Fetch failed' }
git show-ref --verify --quiet 'refs/heads/research/p5-cross-room-reconstruction'
if ($LASTEXITCODE -eq 0) {
    git switch research/p5-cross-room-reconstruction
} else {
    git switch --track origin/research/p5-cross-room-reconstruction
}
if ($LASTEXITCODE -ne 0) { throw 'Switch failed' }
git merge --ff-only origin/research/p5-cross-room-reconstruction
if ($LASTEXITCODE -ne 0) { throw 'Fast-forward failed' }
~~~

Only after the checkout is clean on the intended branch:

### Gate 1 — Room 23 historical 87-sample portable package

~~~powershell
Set-Location -LiteralPath 'F:\Dev\SCUMMBUCKET\SOURCE\ScummBucket'
& .\tools\p4_cross_room_acceptance.ps1 -Stage Room23
~~~

Expect room23_native_palette_package_verified, 87 samples and two
segments with a 12,828-ms clock discontinuity. The raw trace lacks END;
capture_complete=false is a retained limitation. If both outputs already
exist the command only re-verifies them. One existing partial output fails
closed rather than being overwritten.

### Gate 2 — build a fresh indexed actor recorder

~~~powershell
Set-Location -LiteralPath 'F:\Dev\SCUMMBUCKET\SOURCE\ScummBucket'
& .\tools\p4_cross_room_acceptance.ps1 -Stage Preflight
~~~

When read-only preflight passes:

~~~powershell
Set-Location -LiteralPath 'F:\Dev\SCUMMBUCKET\SOURCE\ScummBucket'
& .\tools\p4_cross_room_acceptance.ps1 -Stage Build
~~~

Requires the original pinned doorway build, C:/msys64/usr/bin/make.exe
and C:/msys64/ucrt64/bin. Creates new TOOLS folders only and prints the
new build_dir. Preserve its final unique folder basename for Gate 3.
If build fails, inspect its new cross-room-build.log; never overwrite
or rebuild in the original doorway source tree.

### Gate 3 — index-and-actor capture through ordinary in-game actions

~~~powershell
Set-Location -LiteralPath 'F:\Dev\SCUMMBUCKET\SOURCE\ScummBucket'
& .\tools\p4_cross_room_acceptance.ps1 -Stage Capture -BuildName 'ScummVM-P4-CrossRoom-REPLACE-WITH-REAL-UUID'
~~~

Travel from Room 7 into Room 12, down/up the stairs, back to Room 7;
quit normally. The capture writes all evidence privately under a new
FIXTURE/CAPTURES/Room7/cross-room-UUID and a distinct REPORTS directory.
A valid capture must include indexed Room 12 engine front buffers and
actual draw_actor rows for both actors 7 and 8. If the recorder omits either
actor, the verifier preserves partial evidence and exits nonzero. RGB
presentations and indexed captures are linked **by observed tick keys**,
not assumed equal in count or render phase.

### Gate 4 — verify multi-actor Room 12 source fidelity

~~~powershell
Set-Location -LiteralPath 'F:\Dev\SCUMMBUCKET\SOURCE\ScummBucket'
& .\tools\p4_cross_room_acceptance.ps1 -Stage Compare -CaptureDirectory 'F:\Dev\SCUMMBUCKET\FIXTURE\CAPTURES\Room7\cross-room-REPLACE-WITH-REAL-UUID'
~~~

This creates a fresh FIXTURE/REPORTS/P5/room12-indexed-UUID directory,
including first-frame native PNG controls and a complete JSON comparison.
An index mismatch returns nonzero and leaves the report intact. This
does not mean the capture failed; it means full composition is not yet
accepted. Investigate actor state, object layers, palette mapping, mask
ordering and within-tick phase without fitting unknown values to the
reference.

### Gate 5 — Room 34 true multi-state holdout

Do not proceed until Gate 4 is accepted. Object 358 has 16 stored states,
but source storage alone does not prove observed state selection, timing
or masking. A real state-change trace, original state image indices,
correct placement and new indexed framebuffer comparison are required.

## Acceptance boundary

CI: synthetic-only Python and PowerShell syntax checks on Windows,
without public artifacts. The exact linked executable must be separately
fingerprinted and the actual new runtime capture inspected on Windows
before Room 12 can be accepted. A scene package or source archive load
does not establish animation execution. Native DOS resource art never
belongs in the public Git repository.
