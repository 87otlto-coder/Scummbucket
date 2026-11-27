# MI2SE Experiment A — earlier room entrances (short A/B comparisons)

Status: **committed and statically checked, not yet executed or auditioned on the owner's Windows PC**. This is a bounded creative experiment based on the real 4:07.730 Woodtick Village Suite. It does not alter native music resources, modify the existing full composition or attempt iMUSE event replay.

## Why

User listening feedback: Woodtick transitions feel too late on entry, sometimes too early on exit, and strong bass/piano can clash. **Woodtick → Carpenter entrance at ~3:07 is also wrong**, even though **Carpenter → Woodtick exit at ~3:39.418–3:42.957 sounded right**. Keep those two directions distinct. The Work audio analysis measured all ten 3.539-second crossfades and showed short perceptual delays and bass imbalance, but **did not prove a universal two-bar entrance error**.

To avoid overcorrecting or more engine research, experiment A tests only the entrance timing and the 0.442s omitted beginning of room audio. Leave bass EQ, exit length, looping, other transitions and full-suite timing out of scope.

## Inputs

`tools/mi2se_woodtick_entrance_ab.ps1` requires the already exported **10-bar Original-bank suite and its matching provenance JSON** plus the existing six decoded source WAV files, all in ScummBucket's `FIXTURE` subdirectories. It checks SHA256 hashes of the full suite and six referenced source WAVs against the provenance, checks chapter IDs, room durations, source availability and encoder installation.

Default suite manifest discovery requires exactly one matching `MI2SE_CREATIVE_Woodtick_Village_Suite_Original_Room10Bars_*.json` under `FIXTURE\REPORTS\MI2SE_Music`. When uncertain, pass `-SuiteManifest` with the exact path; never silently select the wrong version. This session's analysed manifest was named `MI2SE_CREATIVE_Woodtick_Village_Suite_Original_Room10Bars_20261127_210354_5911660.json`.

## What is rendered

Four pairs (eight WAV files), one for each of these **Woodtick→room entrances**:

| Cue | Room | Original overlap starts | Candidate overlap starts |
|---:|---|---:|---:|
| 152 | Inn | 0:17.695 | 0:14.156 |
| 110 | Laundromat | 1:42.631 | 1:39.092 |
| 104 | Wally | 2:25.099 | 2:21.560 |
| 111 | Carpenter | 3:07.567 | 3:04.028 |

The Bar entrance is excluded from this particular trial because the analysis found a comparatively balanced bass handoff and recommended retaining its timing for comparison. The **Carpenter→Woodtick exit at ~3:39** is completely excluded and must remain the unchanged musical reference.

Each pair spans the same six-bar, **21.234s** listening window relative to the original suite: two bars before the original transition starts and four bars after it. The baseline WAV is taken directly from the original suite via a lossless PCM trim. The candidate re-renders exactly that same duration using Woodtick and the selected room sources:

- Baseline: the original 1-bar crossfade begins at the documented suite transition time; room audio starts from source **0.442s**.
- Candidate: the 1-bar crossfade begins **one bar (3.539s) earlier**; room audio starts from source **0.000s**. The room is at full fade gain at the original transition start.
- Source pickup at 0..0.442s is present in the candidate, **but may be hard to hear** because it falls at the beginning of the fade.
- Baseline and candidate are separate files; neither changes the actual full Woodtick suite or its 3:39 reference exit. This is a **listening comparison**, not a validated fix or game-authentic transition.

Export location is a new timestamped subdirectory under `FIXTURE\OUTPUT\MI2SE_Music\MI2SE_ExperimentA_Entrances_*`; a SHA256/duration/clip metadata JSON is written separately under `FIXTURE\REPORTS\MI2SE_Music`. Existing sources remain read-only. `ffmpeg -n` refuses overwrites; no copyrighted assets go into Git.

## Windows commands

Do **not** remove, reset or stash the previously reported untracked directories `docs/research/`, `scummbucket.egg-info/`, `scummbucket/`, `tests/`, `tools/__pycache__/`.

```powershell
Set-Location "F:\Dev\SCUMMBUCKET\SOURCE\ScummBucket"
$branch = "feature/m2-mi2se-music-export-20261127"
if ((git branch --show-current).Trim() -ne $branch) { throw "Unexpected branch" }
git status --short
git fetch origin $branch
if ($LASTEXITCODE -ne 0) { throw "Fetch failed" }
git merge --ff-only "origin/$branch"
if ($LASTEXITCODE -ne 0) { throw "Fast-forward failed" }
$manifest = 'F:\Dev\SCUMMBUCKET\FIXTURE\REPORTS\MI2SE_Music\MI2SE_CREATIVE_Woodtick_Village_Suite_Original_Room10Bars_20261127_210354_5911660.json'
powershell.exe -NoProfile -ExecutionPolicy Bypass -File '.\tools\mi2se_woodtick_entrance_ab.ps1' -SuiteManifest $manifest -ListOnly
if ($LASTEXITCODE -ne 0) { throw "Preflight failed" }
powershell.exe -NoProfile -ExecutionPolicy Bypass -File '.\tools\mi2se_woodtick_entrance_ab.ps1' -SuiteManifest $manifest
if ($LASTEXITCODE -ne 0) { throw "Render failed" }
```

If the manifest is named differently on the user's PC, pass the actual path explicitly. **Do not rename or overwrite it.** The script checks contents and SHA256s.

## Acceptance / follow-up

- `-ListOnly` prints four suite times and four candidate starts, with no outputs written.
- Full run exports 8 separately named clips and a result JSON. Each clip duration ~21.234s, with hashes and no overwrite.
- Listener compares matched `*_BASELINE.wav` vs `*_EARLY1BAR_PICKUP.wav` for each room independently, noting whether each entrance feels earlier and more natural. We must not decide based solely on analysis proxies.
- Leave Carpenter→Woodtick good exit untouched. If Woodtick→Carpenter remains wrong, adjust it separately later.
- No user-visible playback, waveform or sound-quality claims until Windows output is actually produced and auditioned.

Related [draft PR #24](https://github.com/87otlto-coder/Scummbucket/pull/24) and [music issue #23](https://github.com/87otlto-coder/Scummbucket/issues/23).