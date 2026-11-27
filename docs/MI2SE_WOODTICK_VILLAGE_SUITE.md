# Woodtick — The Complete Village Suite (M2 creative arrangement)

**Status:** committed Windows PowerShell 5.1 prototype, not yet run or auditioned on owner's machine. The rendered WAV will be produced **locally**, never uploaded to GitHub. Source: `tools/mi2se_woodtick_village_suite.ps1`.

## Intent

Create one full-length listening composition incorporating **all five Woodtick locations**, with a distinct Woodtick interlude between each, rather than a simple two-song transition. Preserve original source recordings, perform bar-aligned editing, and report inputs, durations, hashes and failures honestly. **This is a creative medley, NOT a reverse-engineered or observed DOS iMUSE / Special Edition XACT musical transition sequence.**

## Edition

**First pass: `MusicOriginal.xwb` only**, the *Special Edition's recorded Original bank*, not original DOS hardware MIDI. The previous owner-validated 101/103 exports prove this decoder/input path works. In the remastered New bank, the Inn 152 is represented by multiple `mx152_SE_Inn_lp_T02` etc. entries and their roles are not yet established; the script deliberately refuses to guess, produce a 'New' suite, or mix two soundtrack versions. Investigate that variant after the Original suite is heard.

All cue numbers are grounded in the uploaded `MI2_MUSIC_IMPLEMENTATION.csv`, which records identical **Bar-sync, 3.539s/bar and 0.442s offset** for sound IDs **101, 103, 104, 110, 111, 152**. Their location association derives from the descriptive New-bank names already seen for 101 (Woodtick), 103 (Bar), 104 (Cartographer), 110 (Laundry), 152 (Inn), and the presumed 111 (Carpenter/Woodsmith). **Carpenter 111 is a working identification awaiting local cue-name/aural confirmation**, not independent verification. The script checks each Original XWB's numeric cue name against its existing inventory and live vgmstream metadata; it cannot prove the location label from that numeric name alone. `-ListOnly` also prints up to four descriptive New-bank candidate cue names per ID (plus candidate counts) to help establish these assignments, especially sound 111, and to expose the Inn's multiple `_T` variants without decoding them.

## Sequence (one-bar crossfade at each join)

| # | Location | Cue | Section bars | Original source bar | Approximate suite start |
|---:|---|---:|---:|---:|---:|
| 1 | Woodtick opening | 101 | 6 | 0 | 0:00.000 |
| 2 | Inn | 152 | 8 | 0 | 0:17.695 |
| 3 | Woodtick interlude | 101 | 4 | 6 | 0:42.468 |
| 4 | Bar | 103 | 8 | 0 | 0:53.085 |
| 5 | Woodtick interlude | 101 | 4 | 10 | 1:17.858 |
| 6 | Laundromat | 110 | 8 | 0 | 1:28.475 |
| 7 | Woodtick interlude | 101 | 4 | 14 | 1:53.248 |
| 8 | Wally | 104 | 8 | 0 | 2:03.865 |
| 9 | Woodtick interlude | 101 | 4 | 18 | 2:28.638 |
| 10 | Carpenter | 111 | 8 | 0 | 2:39.255 |
| 11 | Woodtick closing | 101 | 8 | 22 | 3:04.028 |

**Calculated total:** 70 section bars minus 10 overlapped bars = **60 × 3.539 = 212.340 s (3:32.340)**. A four-bar Woodtick return has one bar blended entering, two clean standalone bars, and one bar blended leaving. Opening and ending have short gentle fades. Source Woodtick is traversed progressively via bar offsets 0, 6, 10, 14, 18, and 22—not restarted from the beginning each time.

## Windows run instructions (on draft PR #24 branch)

Before fetching, confirm no local modifications; do not discard uncommitted work. This only fetches the existing development branch, does not touch main or game inputs.

```powershell
Set-Location "F:\Dev\SCUMMBUCKET\SOURCE\ScummBucket"
git status --short
git branch --show-current
git fetch origin feature/m2-mi2se-music-export-20261127
git merge --ff-only origin/feature/m2-mi2se-music-export-20261127
powershell.exe -NoProfile -ExecutionPolicy Bypass -File ".\tools\mi2se_woodtick_village_suite.ps1" -ListOnly
powershell.exe -NoProfile -ExecutionPolicy Bypass -File ".\tools\mi2se_woodtick_village_suite.ps1"
```

**Only run `git merge --ff-only` if the branch shown is exactly `feature/m2-mi2se-music-export-20261127` and working tree is clean.** Otherwise switch/reconcile safely rather than modifying unrelated work. Execution-policy bypass is limited to the child process.

Dependencies: `TOOLS\vgmstream\vgmstream-cli.exe`, installed FFmpeg and adjacent ffprobe.exe, `FIXTURE\mi2remastered\audio_extracted\MusicOriginal.xwb`, and the existing `FIXTURE\REPORTS\MI2SE_Music\MI2SE_CueMap_*.csv`. The six IDs must each appear exactly once as `trackNNN` in that inventory. No extra top-level folder is created.

The script verifies the bank's live stream name; decodes only missing WAVs to `FIXTURE\OUTPUT\MI2SE_Music`; probes every source WAV to ensure the planned excerpt fits; runs FFmpeg (44.1kHz stereo PCM, bar-aligned linear crossfades) to a **timestamped, non-overwriting** `MI2SE_CREATIVE_Woodtick_Village_Suite_Original_*.wav`; verifies its duration to ±0.1 seconds; and writes a matching provenance JSON under `FIXTURE\REPORTS\MI2SE_Music` with chapters, SHA256, sources and ffmpeg path. If a step fails, do not silently substitute silence, truncate, pad, or hide errors.

## Acceptance still required

- Local `-ListOnly` resolves all **six** original cue IDs and prints 11 planned chapters.
- The full run extracts missing 104/110/111/152 WAVs (if absent), preserves previous 101/103 WAVs, and reports their real names, sizes and sample durations.
- Rendered WAV lasts ~3:32.340 and manifest JSON exists; outputs must not be committed to Git.
- Audition: every location theme is actually correct, especially sound 111 (Carpenter); Woodtick breaks are noticeable; join points are pleasant and without discontinuities. If not, revise the musical arrangement before declaring success.
- New-bank edition and authentic `_T` transition behavior are separate future investigations, not features in this version.

Related: [draft PR #24](https://github.com/87otlto-coder/Scummbucket/pull/24) and [music handoff #23](https://github.com/87otlto-coder/Scummbucket/issues/23).
## 27 November Windows preflight: duplicate Original cue (unresolved)

Owner successfully fetched and fast-forwarded this PR branch through commit `33ebc67`. Their initial safety check reported **local working-tree changes**; nevertheless the manual fast-forward completed. Future procedures must inspect `git status --short` and protect those changes—**never discard/stash/overwrite without owner's approval**.

The initial owner-run `-ListOnly` preflight and subsequent full-run attempt both stopped **before decoding** at `Expected exactly one original cue track110. Found 2.` This is a legitimate ambiguity in `MusicOriginal.xwb`'s cue inventory, not a decoder failure. Since the script rejected it during source selection, neither attempt created the full composition WAV. There may be further duplicates after ID 110; the previous preflight terminated on the first ambiguity.

**Hotfix on the same draft PR branch:** `tools/mi2se_woodtick_village_suite.ps1` now inventories **all six original IDs**, prints every matching Original stream index and all descriptive New-bank cue names, and identifies all unresolved cases at once before any decode/render. Duplicate CSV rows referencing the same stream are not treated as multiple audio variants, but **distinct original stream indexes are not automatically conflated**. A `-StreamOverrides` *single string* parameter can explicitly select a verified stream index for one or more ambiguous IDs, e.g. `-StreamOverrides '110=123;152=234'` (these numbers are **illustrative only, NOT actual known streams**). Invalid choices are rejected. Resolved candidate list is included in the final provenance JSON.

This change has been source-reviewed on GitHub but **not yet Windows-tested**. Read-only local diagnostic without fetching any code:

```powershell
Set-Location "F:\Dev\SCUMMBUCKET\SOURCE\ScummBucket"
$csv = "F:\Dev\SCUMMBUCKET\FIXTURE\REPORTS\MI2SE_Music\MI2SE_CueMap_20261124_091453.csv"
$inventory = Import-Csv -LiteralPath $csv
foreach ($id in @(101,103,104,110,111,152)) {
    Write-Host "`nSOUND $id" -ForegroundColor Cyan
    $inventory | Where-Object { $_.Bank -eq 'MusicOriginal.xwb' -and $_.CueName -ceq "track$id" } |
        Format-Table Bank,Stream,CueName -AutoSize
    $inventory | Where-Object { $_.Bank -eq 'MusicNew.xwb' -and $_.CueName -match ("^mx{0}_SE_" -f $id) } |
        Format-Table Bank,Stream,CueName -AutoSize
}
git status --short
```

After seeing the exact duplicate stream IDs, investigate whether `track110` contains Laundry A and Laundry B or just duplicated inventory entries. Do not choose the first arbitrarily. Depending on the evidence, either select the one supported by listening/metadata or revise the suite to present both intentional variants, with their distinct stream provenance. Acknowledged pending acceptance: no full suite output yet.
