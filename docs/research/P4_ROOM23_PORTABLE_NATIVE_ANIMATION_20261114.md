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
  source archive identity, phase calibration and gap annotations. The
  historical manifest contains **two further CYCL observations** (whether
  source colors reinitialized, and how many cycling indices changed across
  the gap). These are recalculated with the **original game CLUT and CYCL**
  after checking archive hashes; comparing timestamp-only gap records would
  incorrectly reject the verified historical export.
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
$game = Join-Path $fx 'GAMES\MonkeyIsland2_DOS_VGA'
foreach ($file in @((Join-Path $native 'manifest.json'), $raw,
                    (Join-Path $game 'MONKEY2.000'),
                    (Join-Path $game 'MONKEY2.001'))) {
    if (!(Test-Path -LiteralPath $file)) {
        throw "Missing original Room 23 source: $file"
    }
}
if ((Test-Path -LiteralPath (Join-Path $native 'play-standalone.html')) -or
    (Test-Path -LiteralPath (Join-Path $native 'animation.json'))) {
    throw 'Portable output already exists; inspect it, do not overwrite'
}

python -B -m tools.package_room23_portable_animation $native --raw-log $raw --game $game
if ($LASTEXITCODE -ne 0) { throw 'Packaging failed; preserve partial files' }

python -B -m tools.verify_room23_portable_animation $native --raw-log $raw --game $game
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


## 14 November follow-up: source-backed clock-gap compatibility correction

The first private Windows attempt advanced the repository to b4f7281 but
did not package the preview: its PowerShell else statement was submitted as
a separate command and rejected. The subsequent verifier, correctly run
against the existing historical export and original SBP4 trace, failed at
"Export gap annotations do not match original raw log" because the new
code compared a timing-only gap record with the original research's
**enriched** gap record. The user independently confirmed:

- Original raw log hash matches the historical export and has 87 samples.
- The discontinuity is sample 27/28, 12,828 milliseconds.
- Historical clock gap includes
  source_cycle_colors_reinitialized_at_first_post_gap_sample=false and
  changed_cycling_indices_across_gap=14.
- Neither animation.json nor play-standalone.html existed after that
  attempt. Do not invent a successful package or overwrite old evidence.

The original source research's compare_room23_palette_capture derives
those fields from the original archive CLUT, the CYCL index ranges and the
two actual neighboring SBP4 palettes. The corrected portable verifier
**recomputes** both from the pinned original DOS VGA game archive, verifies
source CYCL and CLUT against the old manifest, and rejects any discrepancy.
It does not strip fields, edit the original trace/manifest or silently accept
the old manifest's extras. The corrected package/verify CLI needs
--game pointing to the read-only original game directory when these
source-derived annotations are present.

**PowerShell 5.1 warning:** send each control-flow statement as a complete
block. Do not submit a standalone else after a previous if has already
completed. The command above deliberately has no else and never prints
a success message after a failed exit code.

The corrected source code and fixture-free CI tests are a separate gate
from actual private success. Only the operator's new package and its
read-only verifier output can complete this checkpoint.
