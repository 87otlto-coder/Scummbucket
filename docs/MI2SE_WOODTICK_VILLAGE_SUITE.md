# Woodtick — The Complete Village Suite (M2 creative arrangement)

**Status:** first 8-bar-room version has **successfully rendered on the owner's Windows machine** (manifest verifies 212.340091 s, 37,456,870 bytes) and its WAV and manifest were uploaded to the conversation. Owner's listening feedback: interior room themes end slightly too soon. A second revision extends rooms to 10 bars by default; **that revision is committed but not yet rendered or auditioned on Windows**. All audio outputs remain outside GitHub. Source: `tools/mi2se_woodtick_village_suite.ps1`.

## Intent

Create one full-length listening composition incorporating **all five Woodtick locations**, with a distinct Woodtick interlude between each, rather than a simple two-song transition. Preserve original source recordings, perform bar-aligned editing, and report inputs, durations, hashes and failures honestly. **This is a creative medley, NOT a reverse-engineered or observed DOS iMUSE / Special Edition XACT musical transition sequence.**

## Edition

**First pass: `MusicOriginal.xwb` only**, the *Special Edition's recorded Original bank*, not original DOS hardware MIDI. The previous owner-validated 101/103 exports prove this decoder/input path works. In the remastered New bank, the Inn 152 has `mx152_SE_Inn_lp` **stream 41**, `mx152_SE_InnLargo_lp` **stream 219**, and additional `_T` streams whose roles are not yet established; the script deliberately refuses to guess, produce a 'New' suite, or mix two soundtrack versions. Investigate that variant after the Original suite is heard.

All cue numbers are grounded in the uploaded `MI2_MUSIC_IMPLEMENTATION.csv`, which records identical **Bar-sync, 3.539s/bar and 0.442s offset** for sound IDs **101, 103, 104, 110, 111, 152**. Their location association derives from the descriptive New-bank names already seen for 101 (Woodtick), 103 (Bar), 104 (Cartographer), 110 (Laundry), 152 (Inn), and 111 (**Woodshop**, New-bank main stream 147). **Carpenter 111 is supported by its descriptive remastered cue name**, although no independent listener identity comparison is reported. The script checks each Original XWB's numeric cue name against its existing inventory and live vgmstream metadata; it cannot prove the location label from that numeric name alone. `-ListOnly` also prints up to four descriptive New-bank candidate cue names per ID (plus candidate counts) to help establish these assignments, especially sound 111, and to expose the Inn's multiple `_T` variants without decoding them.

## Original 8-bar room version (owner successfully rendered, one-bar crossfade at each join)

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

## Extended room version — owner's listening feedback, 27 November 2026

Owner listened to the first ~3:32 composition and said **the smaller rooms end slightly too early**, and would benefit from more music—even modest looping. The **default is now 10 bars per interior room**, rather than eight. No new looping is required: each existing decoded recording is long enough to supply ten contiguous bars starting at the known 0.442 s bar offset. This avoids prematurely truncating each theme and avoids speculative loop re-entry artifacts.

- Inn, Bar, Laundry, Wally and Carpenter: **10 bars each** (35.390 s excerpt each; previously 8 bars / 28.312 s).
- Woodtick opening (6 bars), four Woodtick bridges (4 bars each) and closing reprise (8 bars) are **unchanged**.
- Each room gains **7.078 seconds** of recorded music, of which both additional bars occur before the outgoing crossfade.
- Total duration increases by 10 bars / **35.390 seconds**, from **3:32.340** to **4:07.730**.
- `-RoomBars 8` reproduces the first version; `-RoomBars 10` is the new default; `-RoomBars 11` gives maximum supported contiguous-bars experimental extension (expected **4:25.425**) if each source passes the duration check. These are **not true loops**; introducing authentic looping needs observed or decoded loop boundaries and a dedicated test.
- Output filenames now contain `Room10Bars` (or selected count) plus a timestamp, so the accepted 8-bar version is never overwritten. The JSON records `InteriorRoomBars` and the contiguous excerpt method.

| # | Suite chapter | Bars | New start (mm:ss.sss) |
|---:|---|---:|---|
| 1 | Woodtick opening | 6 | 0:00.000 |
| 2 | Inn | 10 | 0:17.695 |
| 3 | Woodtick return | 4 | 0:49.546 |
| 4 | Bar | 10 | 1:00.163 |
| 5 | Woodtick return | 4 | 1:32.014 |
| 6 | Laundromat | 10 | 1:42.631 |
| 7 | Woodtick return | 4 | 2:14.482 |
| 8 | Wally | 10 | 2:25.099 |
| 9 | Woodtick return | 4 | 2:56.950 |
| 10 | Carpenter | 10 | 3:07.567 |
| 11 | Woodtick closing | 8 | 3:39.418 |

**Known source lengths from the owner's successful v1 manifest:** Inn 152 stream 6 **39.383 s**, Bar 103 stream 3 **39.383 s**, Laundry 110 stream 5 **39.383 s**, Wally 104 stream 4 **42.920 s**, Carpenter 111 stream 14 **41.154 s**. The new ten-bar slice requires **0.442 + 10 × 3.539 = 35.832 s** per source, within each confirmed length. For 11 bars, 39.371 s is needed, leaving very little margin in the Inn/Bar/Laundry WAVs, so 10 is the safer default.

### Produce the extended 4:07 version

Safely fetch the existing PR branch only after checking branch and tracking status. Your previously reported five untracked directories are ScummBucket-owned work: **do not delete, clean, stash or overwrite them**. Then:

```powershell
Set-Location "F:\Dev\SCUMMBUCKET\SOURCE\ScummBucket"
$branch = "feature/m2-mi2se-music-export-20261127"
if ((git branch --show-current).Trim() -ne $branch) { throw "Wrong branch" }
git status --short
git fetch origin $branch
if ($LASTEXITCODE -ne 0) { throw "Fetch failed" }
git merge --ff-only "origin/$branch"
if ($LASTEXITCODE -ne 0) { throw "Fast-forward failed" }
powershell.exe -NoProfile -ExecutionPolicy Bypass -File ".\tools\mi2se_woodtick_village_suite.ps1" -ListOnly -StreamOverrides '110=5;152=6' -RoomBars 10
if ($LASTEXITCODE -ne 0) { throw "Preflight failed" }
powershell.exe -NoProfile -ExecutionPolicy Bypass -File ".\tools\mi2se_woodtick_village_suite.ps1" -StreamOverrides '110=5;152=6' -RoomBars 10
if ($LASTEXITCODE -ne 0) { throw "Render failed" }
```

Acceptance requires the new WAV and JSON; `ffprobe`-confirmed runtime near **247.730 s** and listener judgment that the Inn, Bar, Laundry, Wally and Carpenter now complete their phrases more naturally. Avoid marking new revision as passed based solely on static code review.
