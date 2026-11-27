# M2 — Monkey Island 2 Special Edition music exports (Windows)

**Scope:** A practical, external-tool-based audio export path. This does not
reimplement XACT, iMUSE, MIDI synthesis, or game playback logic.

**Implementations:** [`tools/mi2se_music_export.ps1`](../tools/mi2se_music_export.ps1) for extraction and [`tools/mi2se_woodtick_crossfade.ps1`](../tools/mi2se_woodtick_crossfade.ps1) for the optional creative preview.
(Windows PowerShell 5.1). **Status: prototype; actual Windows execution of this
new script is still pending.** Earlier manual vgmstream commands and six WAV
exports were successful and are the evidence for the cue mapping below.

## Required local files

Canonical project root: `F:\Dev\SCUMMBUCKET`.

- `TOOLS\vgmstream\vgmstream-cli.exe` — third-party decoder, separately installed.
- `FIXTURE\mi2remastered\audio_extracted\MusicOriginal.xwb`
- `FIXTURE\mi2remastered\audio_extracted\MusicNew.xwb`
- `FIXTURE\mi2remastered\audio_extracted\MusicCuesOriginal.xsb`
- `FIXTURE\mi2remastered\audio_extracted\MusicCuesNew.xsb`
- `FIXTURE\REPORTS\MI2SE_Music\MI2SE_CueMap_20261124_091453.csv`
  (the earlier successfully generated full bank/stream/cue inventory)

All original Steam/game files remain untouched. Local copyrighted audio,
wavebanks and extracted WAVs **must never be committed to Git**.

The existing vgmstream companion-file mapping `.txtm`, in the
`audio_extracted` directory, was created for the previous inventory using:

```text
MusicOriginal.xwb: MusicCuesOriginal.xsb
MusicNew.xwb: MusicCuesNew.xsb
```

The exporter **does not create or change** this mapping or regenerate the
inventory. If the inventory or companion files are absent, recover them
before using the exporter. The script checks each selected stream's actual
decoder-reported name before exporting.

## Confirmed bank-to-cue mapping (user's vgmstream output)

| Music | DOS sound ID | Original XWB cue / stream | New XWB cue / stream |
| --- | ---: | --- | --- |
| Woodtick | 101 | `track101` / **2** | `mx101_SE_Woodtick_lp` / **14** |
| Bar | 103 | `track103` / **3** | `mx103_SE_Bar_lp` / **16** |
| Jojo playing piano | 162 | `track162` / **48** | `mx162_SE_MonkeyPlaying_lp` / **86** |

Original bank: 267 streams, Microsoft 4-bit ADPCM, stereo.
New bank: 263 streams, Microsoft 4-bit ADPCM, stereo.

User's successful manual WAV exports (all six uploaded to ChatGPT) substantiate
the mapping and demonstrate that both wavebanks are decodable. Both Woodtick
versions have approximately 1:50.18 duration, and both Bar versions about
0:39.38. The new Jojo WAV is materially smaller than the original Jojo WAV.
**Owner-run vgmstream now directly verifies New Jojo's one-pass length as 1:20.534** (3,551,488 samples, decoder-reported 44,099 Hz), with a loop from 0:02.659 to 1:20.534. Original Jojo is 2:35.748; its New recording is approximately 75.214 seconds shorter. The decoder's extended playback duration of 2:48.410 includes loop treatment and is not the one-pass duration. Why Jojo is shorter remains unverified. The _T suffix on other remastered bank entries may identify transition segments, but this has not been verified. The exporter intentionally keeps these separate. Verify musical structure by listening before assuming the recordings are equivalent.

## How to use the new script

Open **Windows PowerShell 5.1**:

```powershell
Set-Location "F:\Dev\SCUMMBUCKET\SOURCE\ScummBucket"

# Review exact main-loop mappings first; no audio decoded.
.\tools\mi2se_music_export.ps1 -ListOnly

# Export the confirmed trio from both banks (six candidates).
.\tools\mi2se_music_export.ps1 -SoundIds 101,103,162
```

If an execution policy prevents locally reviewed scripts from running, invoke
PowerShell with `-ExecutionPolicy Bypass` **for that process only**, without
changing machine policy.

**PowerShell 5.1 CLI acceptance note:** An owner-run
`powershell.exe -NoProfile -ExecutionPolicy Bypass -File ".\\tools\\mi2se_music_export.ps1" -SoundIds 101,103,162`
on the original PR prototype parsed the comma-separated numbers as a *single*
integer `101103162`, generated two `MissingCue` entries, and left WAVs untouched.
Microsoft documents that `powershell.exe -File` does not support reliably
passing array-valued script arguments. Commit `34ed6b31` updates the exporter
to accept sound IDs as strings and explicitly split commas/semicolons/whitespace
before strict integer conversion. **This revised parser is source-reviewed but
not yet Windows runtime-validated.** In the old local checkout, omit `-SoundIds`
to use the confirmed defaults for 101, 103, and 162. After fetching the fix,
run `-ListOnly` with `-SoundIds 101,103,162` before trying a full export.

The exporter:

1. Reads the latest `MI2SE_CueMap_*.csv`, or an explicit `-InventoryCsv`.
2. Requires exactly one `trackNNN` Original cue and exactly one
   `mxNNN_SE_*_lp` New main-loop cue per sound ID.
3. Verifies the decoder actually reports each matched stream name.
4. Exports using vgmstream's `-i` (no additional looping), `-s` and `-o`.
5. Preserves existing WAVs, including prior manually named exports, using
   the bank and stream suffix for detection. Existing files are marked
   `AlreadyPresentUnverified`; they are **not** revalidated.
6. Writes a new `FIXTURE\REPORTS\MI2SE_Music\MI2SE_Export_*.csv` with
   per-cue status and raw decoder metadata JSON.

`MissingCue`, `AmbiguousCue`, `InvalidStream` or `Failed` statuses
cause the run to end with an error **after** the report is written.
Unchanged audio goes in `FIXTURE\OUTPUT\MI2SE_Music`.
No extra top-level project directories are created.

## Remaining work

- **Run the new script on Windows and review its manifest.** This exact
  script has not been executed/tested in a real Windows shell yet.
- Confirm actual loop length and listening impressions for the new Jojo
  recording (different byte size is not itself proof of musical arrangement).
- Compare Original vs New Woodtick and Bar by ear.
- Explore `_T` transition entries and the implementation CSV timing as
  a **separate creative experiment**; a crossfade is not verified XACT/iMUSE
  transition behavior.
- Only after this smaller workflow is accepted, consider broad extraction
  of the complete named music catalogue.

### Evidence and handoff

See [M2 music work tracking — issue #23](https://github.com/87otlto-coder/Scummbucket/issues/23).
Keep game-derived waveforms and banks local; GitHub stores only code, maps
of factual stream IDs, procedures and non-copyright diagnostics.

## Creative Woodtick-to-Bar experiment (PR #24)

The separate source script tools/mi2se_woodtick_crossfade.ps1 creates a roughly 31.851-second creative crossfade using *already decoded* Woodtick 101 and Bar 103 WAVs. This is an **artistic preview, NOT a verified XACT or original DOS iMUSE transition**.

The Special Edition implementation CSV documents a shared 3.539-second bar and 0.442-second offset. The script trims five bars from each recording at that offset, overlaps one bar using FFmpeg linear acrossfade, normalizes both to 44.1 kHz stereo PCM, and creates a WAV and JSON with source SHA256 and method metadata. It refuses to overwrite either output. It does not interpret or mix the separate _T segments. No game archives are changed.

FFmpeg is an additional third-party dependency: ffmpeg.exe must be on PATH or somewhere within the existing F:\Dev\SCUMMBUCKET\TOOLS tree. The script fails with an explicit error if FFmpeg or an input WAV is absent; it does not install anything.

From Windows PowerShell 5.1, with the repository on branch feature/m2-mi2se-music-export-20261127:

    Set-Location "F:\Dev\SCUMMBUCKET\SOURCE\ScummBucket"
    .\tools\mi2se_woodtick_crossfade.ps1 -Variant Original
    .\tools\mi2se_woodtick_crossfade.ps1 -Variant New

The scripts on this PR branch have **not yet been run or auditioned on Windows**. A successful output requires actual Windows execution, an audible check of the joining bar, and confirmation that the WAV and JSON exist. A creative crossfade does not establish authentic game transition behavior.

### Concise Windows acceptance checklist

1. Run mi2se_music_export.ps1 -ListOnly; confirm six expected mappings and new report CSV (no WAV exports).
2. Run the exporter for IDs 101,103,162; confirm it preserves six prior WAVs and reports AlreadyPresentUnverified, not Exported.
3. Run each crossfade variant (if FFmpeg is installed); confirm unique WAV and JSON, approximately 31.851-second audio, no overwritten file, and no audible clicks or unnatural musical mismatch.
4. Record observed outcomes and failures in FIXTURE\REPORTS; keep game-derived WAVs out of GitHub.
