# Woodtick — Experiment A3: Carpenter entrance only

**Status:** code committed to draft PR #24; timing math checked against the known 10-bar suite chapter starts; **not yet executed on Windows or auditioned**.

## Owner's accepted listening findings

- **Inn:** `T02_Inn_EARLY2P0BARS_PICKUP.wav` sounds best (2 bars = 7.078 s before the original suite entrance).
- **Laundromat:** `T06_Laundromat_EARLY2P0BARS_PICKUP.wav` sounds best (2 bars = 7.078 s early).
- **Wally:** A1 one-bar-earlier entrance sounds right (3.539 s before original). Preserve.
- **Carpenter:** A2 `T10_Carpenter_EARLY1P5BARS_PICKUP.wav` may still start slightly late. A3 tests **1.75 and 2 bars early** from the original baseline.
- **Carpenter→Woodtick exit** 3:39.418–3:42.957 previously sounded right and must remain unchanged. Do not confuse entrance and exit.
- **Bar:** not evaluated in A/A2; keep its original entrance unless later evidence warrants otherwise.

## Why limit Carpenter at 2 bars early?

The original 4:07.730 suite has **Wally→Woodtick returning at 2:56.950–3:00.489**, followed by **Woodtick→Carpenter starting at 3:07.567**. Shifting that Carpenter entrance 2 bars earlier places it at **3:00.489**, precisely when the preceding Wally fade finishes. Moving it earlier would overlap two independent fades or cut into Wally's return; do not do this as a small timing adjustment.

Unlike the previous A2 Carpenter preview (which used the isolated original Woodtick WAV for the entire lead-in), **A3 uses the actual existing full-suite mix up to the proposed new Carpenter handoff**. This preserves the Wally→Woodtick overlap and then fades into Carpenter without changing the original full-suite recording.

## A3 output

`tools/mi2se_woodtick_carpenter_a3.ps1` validates the exact original-bank Room10Bars suite manifest, source hashes and section order, then makes **three 24.773-second listening clips** under a unique timestamped `FIXTURE\OUTPUT\MI2SE_Music\MI2SE_ExperimentA3_Carpenter_*` directory:

| WAV | Entrance start on original suite clock |
|---|---:|
| `T10_Carpenter_BASELINE.wav` | 3:07.567 (original suite clip) |
| `T10_Carpenter_EARLY1P75BARS_PICKUP.wav` | 3:01.374 |
| `T10_Carpenter_EARLY2P00BARS_PICKUP.wav` | 3:00.489 |

All clips cover original-suite window **2:56.950–3:21.723**. Candidate input begins at Carpenter source 0.0s, has a 1-bar 3.539-second linear overlap, and uses the original suite itself as its outgoing audio. The preceding Wally fade is preserved, and the Carpenter exit at 3:39 is outside the clip. Each output is probed, duration-checked and SHA256 recorded in a separate timestamped JSON manifest under `FIXTURE\REPORTS\MI2SE_Music`. No preexisting files are overwritten.

## Windows PowerShell 5.1 commands

Protect existing untracked directories, and never `git clean`/`reset`/`stash` without the owner's explicit request. Only fast-forward the current development branch, retaining the existing original game banks and accepted suite WAV.

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
powershell.exe -NoProfile -ExecutionPolicy Bypass -File '.\tools\mi2se_woodtick_carpenter_a3.ps1' -SuiteManifest $manifest -ListOnly
if ($LASTEXITCODE -ne 0) { throw 'Preflight failed' }
powershell.exe -NoProfile -ExecutionPolicy Bypass -File '.\tools\mi2se_woodtick_carpenter_a3.ps1' -SuiteManifest $manifest
if ($LASTEXITCODE -ne 0) { throw 'A3 render failed' }
```

## Acceptance

1. A3 `-ListOnly` prints 3:01.374 and 3:00.489 Carpenter candidate start times.
2. Windows run exports three WAV clips and provenance with correct ~24.773s durations and hashes.
3. Owner listens alongside the previously preferred A2 Carpenter -1.5 bars version, and decides whether -1.75 or -2 bars feels more natural.
4. Stop iteration when this entrance is accepted and consider one complete mix using accepted entrance shifts. Note that earlier entrances necessarily reduce Woodtick's isolated interlude exposure unless section lengths are rebalanced; preserve the previously correct Carpenter exit and describe any new time shifts.

This is a creative editing experiment, **not verification of actual MI2 Special Edition XACT or DOS iMUSE behavior**, and does not change ScummBucket's extraction roadmap.