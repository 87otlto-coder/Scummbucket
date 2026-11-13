# P4 Room 7 — saved-entry palette-phase research, 13 November 2026

This checkpoint records the operator's **actual private Windows results**,
and introduces a held-out phase calibration experiment. It does not claim
that the new phase model has passed against the private engine buffers.

## Verified from the operator's terminal transcript

At research commit e819cd8, the user reran the existing Room 7 private
save capture validator and archive-background comparator. Input
monkey2-1.s01 is a gzip-wrapped ScummVM version 124 save, with current room
7, room resource 7 and 20 room objects. Save SHA-256:

    39035338ed89bdfe754f31e390f247c83095f1938aeae6877c0373ad7f72aa0d

The saved-entry capture path was:

    FIXTURE/CAPTURES/Room7/native-save-72c00ab603b64f9597b10cf952c9662e

The private report and comparator output paths were:

    FIXTURE/REPORTS/Room7/native-save-72c00ab603b64f9597b10cf952c9662e-gate.json
    FIXTURE/REPORTS/Room7/native-save-72c00ab603b64f9597b10cf952c9662e-comparison

Reported results:

| Check | Operator-observed result | Interpretation |
| --- | ---: | --- |
| Paired engine and presentation frames | 87 | Complete bounded capture |
| Indexed positions checked | 4,008,960 | 87 x 320 x 144 |
| Background differences | 0 | Independently decoded archive SMAP matches runtime back plane |
| ZP01 mask differences | 0 | Decoded mask matches runtime depth plane |
| Front vs backend differences | 0 | Engine front plane matches backend crop; not independent actor reproduction |
| Front vs archive background differences | 237,510 | Drawn scene content differs from bare background; not inherently a defect |
| Camera X | min=max=464 | Static saved scene, no new panning validation |
| Scenery actor 11 state rows | 87 | Actor runtime state recorded, not independently composed |
| Distinct final palettes | 41 | Dynamic palette observed |
| Palette trace samples | 256 | Valid sequential log, more than captured frame count |
| Palette samples paired with engine | 87 | First 87 are paired; 169 additional records remain unpaired |
| Continuous zero-counter model matches | 3/87 | **Palette timing model is unresolved** |

Original game files, the instrumented engine, the source save and its
captured copy were each rehashed and verified by the local gate.
The 256-sample raw palette log SHA-256 was:

    61cc796bce50ebd5cc91d71c25b463e146618bbd7d74e81969206e533ead5651

This evidence is from the user's provided console output, not direct
re-reading of the private engine binaries in this GitHub session.
Neither the old 3/87 model nor the new research tool establishes
generalized palette timing accuracy at this stage.

## Why a phase study is necessary

The old compare_room7.py initializes every palette cycle counter to
zero. A restored ScummVM game save may resume a different counter phase.
That is **a hypothesis**, not yet a verified explanation for the 3/87 result.
Scripts, palette overrides, timer behavior or another implementation issue
could also explain the discrepancy.

The new source module scummbucket/room7_palette_phase.py enumerates candidate
counter residues separately for each non-overlapping archive CYCL range.
It uses exactly the first 24 paired frame samples to constrain the phases,
starting from the first observed pre-cycle palette. It then predicts the
remaining 63 **held-out** post-cycle palettes using engine-observed timer
deltas. It does not fit anything to the held-out palettes.

Outputs distinguish a uniquely identified counter, multiple equivalent
candidates, an ambiguous later forecast, an impossible calibration, a
held-out palette mismatch and a determinate full-palette match. Noncycling
palette changes are reported separately. Its initial palette, timers,
and calibration prefix are all engine-observed input, so the forecast is
not equivalent to complete independent engine emulation.

## Run only this read-only experiment

On the existing local F-drive workspace, ensure the checkout is on the
research branch, clean and fast-forwarded to the new verified GitHub commit.
The following does **not** launch ScummVM, modify the save, modify any prior
capture, or overwrite an existing report:

~~~powershell
$root = 'F:\Dev\SCUMMBUCKET'
$repo = "$root\SOURCE\ScummBucket"
$fixture = "$root\FIXTURE"
$id = 'native-save-72c00ab603b64f9597b10cf952c9662e'
$capture = "$fixture\CAPTURES\Room7\$id"
$export = "$fixture\OUTPUT\Room7\native-20261110-a"
$report = "$fixture\REPORTS\Room7\$id-palette-phase-24.json"

Push-Location $repo
try {
    python -B -m tools.analyze_room7_saved_palette --capture $capture `
        --export $export --report $report --calibration-frames 24
    if ($LASTEXITCODE -ne 0) {
        Write-Warning "Palette timing is still unresolved; inspect $report"
    }
} finally {
    Pop-Location
}
~~~

The CLI writes the metadata report with exclusive creation. Exit code 0
means a determinate 63/63 held-out full-palette match; exit code 2
indicates unresolved calibration, ambiguous held-out predictions or
definite disagreement. It retains the diagnostic report in both cases.
The local private result, if supplied, will determine the next engineering
step; do not invent a pass from synthetic CI.

## Remaining scope restrictions

The saved-entry capture validates background/mask and engine-to-backend
integrity at fixed camera X=464; it does not revalidate camera scrolling,
independently composed scenery actor 11, scripted object transitions or
arbitrary saved-state variants. The earlier debugger-equivalent, 87-frame
full-front reconstruction remains a separate accepted control. Keep
private resource assets and output reports under FIXTURE and outside Git.
PR #8 remains draft pending wider review and licensing decisions.
