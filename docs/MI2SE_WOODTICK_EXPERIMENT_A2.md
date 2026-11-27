# MI2SE Woodtick — Experiment A2: refine early room entrances

Status: **committed, statically checked only**. The owner has not yet executed or auditioned these new A2 clips. This is a bounded follow-up to Experiment A, not a request for more iMUSE reverse engineering.

## Listening evidence

Owner compared Experiment A entrance clips (1 bar = 3.539 s earlier than the original Woodtick Village Suite) and reported:
- **Woodtick → Wally**: one bar earlier sounds right. **Keep this unchanged.**
- **Woodtick → Inn and Laundromat**: 1-bar-early results still seem about half or a whole bar late. Test **1.5 and 2 bars earlier than the original baseline**.
- **Woodtick → Carpenter**: 1-bar-early result still seems half a bar late. Test **1.5 bars earlier than the original baseline**.
- **Carpenter → Woodtick near 3:39.418** remains the previously good *exit*, not the bad *entrance*. Keep exit unchanged.
- Bar entrance was not part of Experiment A and is unchanged.

Interpret 'another 0.5 or 1 bar' **relative to the one-bar-earlier A1 previews**, hence A2 tests 1.5 and 2 bars ahead of the unmodified original suite. These are subjective listening trials, **not game-verified timings**.

## Implementation

`tools/mi2se_woodtick_entrance_a2.ps1` reads the existing `Room10Bars` suite provenance JSON, full suite WAV and referenced source WAVs from `FIXTURE`. It checks the source/suite SHA256 hashes, room length and chapter structure, and encoder availability. There are no writes to game archives, old source WAVs or the complete suite.

Produces a **single new timestamped folder** under `FIXTURE\OUTPUT\MI2SE_Music\MI2SE_ExperimentA2_Entrances_*` with eight short WAVs:

| Room | Reference | Experimental alternatives |
|---|---|---|
| Inn | Original suite excerpt | `EARLY1P5BARS_PICKUP`, `EARLY2P0BARS_PICKUP` |
| Laundromat | Original suite excerpt | `EARLY1P5BARS_PICKUP`, `EARLY2P0BARS_PICKUP` |
| Carpenter | Original suite excerpt | `EARLY1P5BARS_PICKUP` |

There are **3 reference clips + 5 candidates**, each **7 bars = 24.773 s**. The A2 reference excerpt comes from the *actual* 4:07.730 suite and is unchanged. Each candidate includes 3 bars of available Woodtick lead-in, keeps a **1-bar/3.539s** linear crossfade, and retains the incoming source's 0.442s pickup (using source start 0.0 s). It does **not** shift room exits, replace the accepted Wally one-bar version, change bass EQ, edit any underlying WAV, or extend the full suite.

## Expected candidate entrance points in original 4:07.730 suite time

| Room | Previous A1 (-1 bar) | A2 -1.5 bars | A2 -2 bars |
|---|---|---|---|
| Inn | 0:14.156 | **0:12.386** | **0:10.617** |
| Laundromat | 1:39.092 | **1:37.322** | **1:35.553** |
| Carpenter | 3:04.028 | **3:02.259** | Not requested |

Note: the Room 10Bars timeline time markers are references to the *existing full-suite clock*. The A2 candidates are just short excerpts, not edits to the full-suite timing. Use the actual per-clip listening comparison to select the next timing plan.

## Windows use

Do not delete, clean, move or stash the owner's untracked project directories. Fetch only the existing draft music branch and fast-forward; Git stops if it would overwrite an existing untracked file.

```powershell
Set-Location "F:\Dev\SCUMMBUCKET\SOURCE\ScummBucket"
$branch = "feature/m2-mi2se-music-export-20261127"
if ((git branch --show-current).Trim() -ne $branch) { throw 'Unexpected branch' }
git status --short
git fetch origin $branch
if ($LASTEXITCODE -ne 0) { throw 'Fetch failed' }
git merge --ff-only "origin/$branch"
if ($LASTEXITCODE -ne 0) { throw 'Fast-forward failed' }
$manifest = "F:\Dev\SCUMMBUCKET\FIXTURE\REPORTS\MI2SE_Music\MI2SE_CREATIVE_Woodtick_Village_Suite_Original_Room10Bars_20261127_210354_5911660.json"
powershell.exe -NoProfile -ExecutionPolicy Bypass -File ".\tools\mi2se_woodtick_entrance_a2.ps1" -SuiteManifest $manifest -ListOnly
if ($LASTEXITCODE -ne 0) { throw 'Preflight failed' }
powershell.exe -NoProfile -ExecutionPolicy Bypass -File ".\tools\mi2se_woodtick_entrance_a2.ps1" -SuiteManifest $manifest
if ($LASTEXITCODE -ne 0) { throw 'A2 rendering failed' }
```

The script reports a separate JSON provenance file in `FIXTURE\REPORTS\MI2SE_Music`. Review clip durations and SHA256. If no matching manifest exists at the stated path, supply the actual path, **do not invent or rename files**.

## Acceptance

- `-ListOnly` reports **five candidate times**, and creates no output.
- Full Windows run reports **eight 24.773 s WAVs**, three baselines and five alternatives, plus JSON.
- User compares A1 to each A2 option, especially half-bar Carpenter change.
- Good Carpenter exit at 3:39 and accepted Wally entrance are not touched.
- No claimed universal phrase timing improvement until audible owner review.

Milestone stays limited to short audio comparisons. Once an option sounds good, consider a single updated complete composition; no new research sprint.