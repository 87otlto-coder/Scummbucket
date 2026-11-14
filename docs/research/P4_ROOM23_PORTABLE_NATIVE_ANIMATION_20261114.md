# P4 — Room 23 portable native palette-background animation

Date: 14 November 2026. Original Monkey Island 2 DOS VGA. Research branch
research/p4-engine-palette-trace. **Code-only tests passed; private F-drive
acceptance is pending.** No BigR scaling and no new ScummVM capture.

## Evidence boundary

This milestone reuses Room 7's indexed-PNG validator and segment-aware
HTML serialization for a second, different mechanism: original Room 23
background palette cycles. Room 23's previously verified native export has
87 P-mode images, the exact fixed 320x144 source index plane and source-CYCL
palette states phase-calibrated against an original SBP4 raw palette trace.
Three calibration samples selected the phase and 84 held-out samples
matched. Source trace is **incomplete** (no END) and has a documented
12,828-ms clock gap. Callback times are not verified display durations.

This package does **not** reconstruct Guybrush, objects, ZP01/ZP02 masks,
the composited engine front buffer or the RGB SDL output. It does not
simulate a complete SCUMM room and does not infer a room restart at the gap.

## New components

- scummbucket/native_animation_common.py is now shared by the Room 7
  verifier/player and the new Room 23 code. It hashes actual encoded PNG
  data, indexed pixel bytes and complete 768-byte palettes.
- scummbucket/room23_portable_animation.py validates the existing native
  export's indexed frames *again* against their manifest and the exact
  original SBP4 raw trace: hash, timer pair, post-cycle palette, timestamp,
  source archive identity, phase calibration and gap annotations.
- tools/package_room23_portable_animation.py creates two exclusive files
  alongside existing sample PNGs: play-standalone.html (all images embedded
  as verified PNG data URLs) and animation.json (completion marker last).
  It never replaces source frames, the old play.html or manifest.json.
- tools/verify_room23_portable_animation.py repeats the read-only source
  check and verifies both saved outputs exactly. No game files are
  embedded in Git; private media remain in FIXTURE.

The new browser player offers separate selectable segments on confirmed
raw-log clock discontinuities. The classifier identifies a recording gap,
not a proven gameplay change or script restart.

## Operator command: Windows PowerShell

Run exactly from the canonical repository. The raw log and native export
names are from the original Room 23 research documentation. If they do
not exist, stop rather than substituting a different run.

~~~powershell
$ErrorActionPreference = 'Stop'
Set-Location -LiteralPath 'F:\Dev\SCUMMBUCKET\SOURCE\ScummBucket'

$branch = 'research/p4-engine-palette-trace'
if ((git branch --show-current).Trim() -ne $branch) { throw 'Wrong Git branch' }
if (git status --porcelain) { throw 'Dirty working tree; inspect first' }
git fetch origin $branch
if ($LASTEXITCODE -ne 0) { throw 'Fetch failed' }
git merge --ff-only "origin/$branch"
if ($LASTEXITCODE -ne 0) { throw 'Fast-forward failed' }

$fx = 'F:\Dev\SCUMMBUCKET\FIXTURE'
$native = Join-Path $fx 'OUTPUT\Room23\native-mixed-20261110-v1'
$raw = Join-Path $fx 'CAPTURES\Room23\room23-normal-20261110-081315-043.raw.log'
foreach ($file in @((Join-Path $native 'manifest.json'), $raw)) {
    if (!(Test-Path -LiteralPath $file)) {
        throw "Missing original Room 23 source: $file"
    }
}
if ((Test-Path -LiteralPath (Join-Path $native 'play-standalone.html')) -or
    (Test-Path -LiteralPath (Join-Path $native 'animation.json'))) {
    throw 'Portable output already exists; inspect it, do not overwrite'
}

python -B -m tools.package_room23_portable_animation $native --raw-log $raw
if ($LASTEXITCODE -ne 0) { throw 'Packaging failed; preserve partial files' }

python -B -m tools.verify_room23_portable_animation $native --raw-log $raw
if ($LASTEXITCODE -ne 0) { throw 'Integrity verification failed' }

Write-Host "Preview: $(Join-Path $native 'play-standalone.html')"
Write-Host "Manifest: $(Join-Path $native 'animation.json')"
~~~

Expected status: room23_native_palette_package_verified.
Expected source count: 87 native callback images; two sections split
at the source-recorded long clock discontinuity. Output includes
capture_complete=false and the unresolved final hold.

If both new files already exist, run only the read-only verification
command. If the original native export is absent, a replacement can be
created in a *fresh* FIXTURE/OUTPUT/Room23 folder using the prior
export-room23-capture command and exact same raw log; never overwrite.

Share the new animation.json and terminal output for evidence review.
The standalone HTML embeds copyrighted game images; store it only in
private FIXTURE, not source control or public CI artifacts.

## Acceptance not yet claimed

Synthetic Windows CI covers source metadata, changed raw logs, palette
tampering, PNG inventory, clock-gap semantics, phase/holdout gating,
output collision and complete offline HTML content. It does not run
the original 87-frame private export on the operator machine.
After this acceptance, an independently validated Room 23 foreground
composition against the 87 paired raw engine-front captures is a
**separate** P4 task, not part of this palette-only milestone.
