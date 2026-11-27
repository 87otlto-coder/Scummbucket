# M2 — Monkey Island 2 Special Edition music exports (Windows)

**Scope:** A practical, external-tool-based audio export path. This does not
reimplement XACT, iMUSE, MIDI synthesis, or game playback logic.

**Implementation:** [`tools/mi2se_music_export.ps1`](../tools/mi2se_music_export.ps1)
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
0:39.38. The new Jojo WAV is materially smaller than the original Jojo WAV;
verify its **actual header duration and musical structure** before assuming
the recordings are equivalent. The `_T` suffix on other remastered bank
entries appears associated with alternate/transition material, but its
playback semantics have not been verified. The exporter intentionally
does **not** combine these segments.

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
