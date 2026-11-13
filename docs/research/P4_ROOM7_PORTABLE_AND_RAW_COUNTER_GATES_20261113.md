# Room 7 saved-entry palette acceptance — portable and raw gates

Date: 13 November 2026. Scope: original **Monkey Island 2 DOS VGA**,
ScummVM v124 saved Room 7. **Draft research only**, not general SCUMM
animation fidelity or arbitrary save compatibility.

## What the provided evidence establishes

A user-provided `monkey2-1.s01` save, SHA-256
`39035338ed89bdfe754f31e390f247c83095f1938aeae6877c0373ad7f72aa0d`,
contains Room 7 (both room fields) and six direct saved palette cycle counters
**12, 12, 26, 35, 13, 80**. The archive CYCL source defines their delays,
flags and color ranges, and exactly one compatible 16-slot 128-byte
ColorCycle block occurs in the decompressed save (offset 80203).

The private Windows capture **87 engine/present frame pairs** passed the
saved-entry gate. The archive-derived background and ZP01 mask each matched
the runtime planes with zero pixels differing; camera X was fixed at 464.
The 256-sample source trace contains 87 paired + 169 unpaired observations.

The user also supplied `play.zip`, containing 87 background-only indexed
PNG previews, report.json and play.html. A separate, read-only cross-check
predicted **87/87 exact 768-byte palettes** from saved counters without
any phase fitting, using the original PNG palette values and the report's
timer pairs. **Important:** these are ZIP PNGs hash-correlated to the
engine palette hashes *claimed by report.json*. Raw `engine-*.bin` payloads
were **not inside play.zip**. The portable result is credible bounded
corroboration, not the formal raw-engine gate.

The earlier 24/36/48-frame fitted-prefix experiments had 0 determinate
mismatches but 11/8/4 ambiguous suffix frames respectively. They are
overlapping analyses on the same capture, not independent runs. Direct
saved-counter decoding resolves ambiguity for the **one provided save**.

## Tools and evidence classification

| Tool | Inputs | Evidence obtained |
| --- | --- | --- |
| `tools.verify_room7_saved_entry` | Private frame binaries, source save, archives, instrumented ScummVM | Structural and same-run trace integrity |
| `tools.verify_room7_saved_palette_counters` | Private `engine-*.bin`, copied save, archive manifest | **Primary:** real 87-frame unfitted engine palette comparison |
| `tools.verify_room7_portable_preview` | Original `MONKEY2.001`, save, user preview ZIP | **Secondary:** original archive + save versus PNG palettes, correlated with supplied report hashes |
| `tools.compare_room7` (old report) | Raw capture and archive export | Background/mask comparison; its **3/87** palette-cycle count assumes zero saved counters and must not be mistaken for saved-state palette failure |

Both new counter paths must return an explicit status, preserve mismatches
and refuse overwriting a prior report. They read the original game data,
save and captures without modifications. No copyrighted source assets or
captured frame images are checked into Git.

## Exact private Windows gate — no new ScummVM launch

Prerequisites: a clean, updated research branch, the prior validated
capture at
`FIXTURE/CAPTURES/Room7/native-save-72c00ab603b64f9597b10cf952c9662e`,
the pinned archive export at `FIXTURE/OUTPUT/Room7/native-20261110-a`,
and the unchanged saved game.

Run the **raw engine gate first**:

~~~powershell
$root = 'F:\Dev\SCUMMBUCKET'
$repo = "$root\SOURCE\ScummBucket"
$fx = "$root\FIXTURE"
$id = 'native-save-72c00ab603b64f9597b10cf952c9662e'
$cap = "$fx\CAPTURES\Room7\$id"
$export = "$fx\OUTPUT\Room7\native-20261110-a"
$rawReport = "$fx\REPORTS\Room7\$id-saved-counters-unfitted.json"

if (Test-Path -LiteralPath $rawReport) {
    throw 'Raw report exists: do not overwrite'
}
Push-Location $repo
try {
    python -B -m tools.verify_room7_saved_palette_counters `
        --capture $cap --export $export --report $rawReport
    $rawExit = $LASTEXITCODE
    if ($rawExit -notin @(0, 2)) { throw "Raw gate crashed: $rawExit" }
    Write-Host "RAW GATE EXIT: $rawExit; REPORT: $rawReport"
} finally {
    Pop-Location
}
~~~

Expected: output reports all 87 paired raw engine palettes, saved counter
values, total exact matches and the first mismatch (if any). **Do not
predeclare a pass before this private command has been executed.**

The separate **portable ZIP gate** can be run on the same files. Supply
the actual local `play.zip` path; a different report filename avoids
collisions:

~~~powershell
$save = "$fx\GAMES\MonkeyIsland2_DOS_VGA\monkey2-1.s01"
$original = "$fx\GAMES\MonkeyIsland2_DOS_VGA\MONKEY2.001"
$zip = (Read-Host 'Full local path to play.zip').Trim('"')
$portableReport = "$fx\REPORTS\Room7\$id-portable-saved-preview.json"
if (Test-Path -LiteralPath $portableReport) {
    throw 'Portable report exists: do not overwrite'
}
Push-Location $repo
try {
    python -B -m tools.verify_room7_portable_preview `
        --archive-001 $original --save $save `
        --preview-zip $zip --report $portableReport
    $portableExit = $LASTEXITCODE
    if ($portableExit -notin @(0, 2)) { throw "Portable gate crashed: $portableExit" }
    Write-Host "PORTABLE GATE EXIT: $portableExit; REPORT: $portableReport"
} finally {
    Pop-Location
}
~~~

Do not rerun the game or produce new captures merely to repeat a metadata
test. If a report file already exists, inspect or use a distinct new
filename rather than overwriting it.

## Next independent reconstruction milestone

The saved-entry frames have **constant actor state and fixed camera X=464**.
They make an excellent palette-state regression but **do not independently
prove animated scenery composition, Guybrush's saved costume pose or
camera motion in normal gameplay**. The preview PNGs contain only
background pixels. The reported 2,730 foreground-altered pixels per frame
remain to be independently composed from archive costumes and matching
saved actor state. The existing debugger-equivalent full-front 87-frame
zero-mismatch result is a **different** capture.

Follow-up should preserve the raw entry's captured scene state, identify
the exact costume limb cursors for actors 1 and 11 from the save/runtime,
and compare against private raw front buffers. Do not use engine front
pixels as reconstruction inputs or assume missing `walk 1` metadata.
Keep PR #8 draft and do not merge without explicit approval.
