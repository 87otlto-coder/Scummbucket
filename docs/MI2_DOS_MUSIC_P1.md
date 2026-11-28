# MI2 DOS music in the P1 pipeline

The [static iMUSE checkpoint](https://github.com/87otlto-coder/Scummbucket/blob/a02d80e6985976308217fe15a246b3d3bd1c7ac2/docs/MI2_DOS_IMUSE_INVENTORY.md) established the sound inventory and script 96 handoff. This integration is based on P1 commit a08ec9c. The music module consumes P1's DSOU and DSCR links plus the exact decoded resource bytes that P1 validated in the same read. The P1 inspector and existing extraction entry points retain their interfaces. The previous standalone tool remains on its research branch.

```powershell
Set-Location F:\Dev\SCUMMBUCKET\SOURCE\ScummBucket-Music
$root = 'F:\Dev\SCUMMBUCKET'
$out = Join-Path $root "FIXTURE\OUTPUT\MI2-DOS-Music-$([guid]::NewGuid())"
python -m scummbucket music "$root\FIXTURE\mi2.zip" --output-dir $out --export 2 11 101 103 151 162 --woodtick-trace
python -m unittest discover -s tests
```

The CLI also accepts a game folder or a MONKEY2.000 path. The new output directory contains inventory.json and control_map.json. Selected IDs export complete decoded SOUN and rendition chunks, MIDI and detailed event maps where supported, and WAV for supported Sound Blaster PCM. The optional Woodtick report is a static reference. A separate runtime probe verifies actual playback.

## Native audio classification

| Rendition | Confirmed in supplied MI2 DOS archive | Output |
| --- | --- | --- |
| SPK | All 65 contain MDhd, MThd and MTrk. The parser accepts all 65 as SMF format 2, including small sound effects and longer cues such as 151 and 162. The MIDI carries note timing, and the SPK rendition can contain device-specific events. | Whole SPK chunk and byte-exact MIDI. An authentic waveform requires speaker-driver synthesis. |
| SBL | All eight contain AUhd and AUdt. AUhd contains three metadata bytes of unresolved meaning. AUdt contains one VOC type-1 block with codec 0, unsigned 8-bit mono PCM and a VOC time constant. | Whole SBL chunk and unresampled PCM WAV. Unknown child layouts, codecs and additional block types remain explicitly unsupported. |

ScummVM setup in `engines/scumm/scumm.cpp` selects `IMuseDriver_PCSpk` for MI2's speaker path. `engines/scumm/imuse/drivers/pcspk.cpp` maps the MIDI stream to speaker notes and instrument behavior. `engines/scumm/sound.cpp` handles SBL sample playback and describes the analogous WVhd/WVdt envelope from other titles. `audio/decoders/voc.cpp` maps the time constants. The WAV exporter follows ScummVM's sample-rate mapping and preserves sample bytes, including when the RIFF container needs a pad byte.

The final inventory has 199 resources, with 196 MIDI-containing IDs, 401 MIDI renditions and eight PCM renditions. ZIP and loose-file inputs produced identical control maps and static transition traces. The initial integration reproduced all 68 standalone exports and reports except the inventory, which now includes P1 provenance. All eight WAV sample payloads were independently compared to the native resource bytes.

The default suite ran 198 tests with eight skips. Enabling the private MI2 fixture exposed one existing Room 23 palette error, missing `counter_delta` in the first frame. The unchanged P1 baseline reproduced the same error. The fixture-enabled run had two skips. Palette code is outside this change.

## Live probe reproduction

The probe uses the existing ScummVM CrossRoom build and native room 7 save. It invokes original doorway script 200 once, one second after identifying an active Woodtick player. If a different save lacks Woodtick audio, the probe can start sound 101 and records that as fixture setup. It leaves the script arguments, random track choice, command queue and MIDI playback unmodified.

```powershell
Set-Location F:\Dev\SCUMMBUCKET\SOURCE\ScummBucket-Music
$root = 'F:\Dev\SCUMMBUCKET'
$base = Join-Path $root 'TOOLS\ScummVM-P4-CrossRoom-767b677319ce4691953ca06dcf67811c'
$probe = Join-Path $root "TOOLS\ScummVM-MI2-iMUSE-Trace-$([guid]::NewGuid())"
robocopy $base $probe /E /XD .git .github
if ($LASTEXITCODE -ge 8) { throw 'ScummVM copy failed' }
python tools/instrument_mi2_imuse.py $probe
if ($LASTEXITCODE -ne 0) { throw 'Instrumentation failed' }
python tools/build_mi2_imuse.py $probe
if ($LASTEXITCODE -ne 0) { throw 'Probe build failed' }
$save = Join-Path $root 'FIXTURE\CAPTURES\Room7\navigation-01f10e8856574e3a8af15fcf1624e890\saves\monkey2.s01'
$game = Join-Path $root 'FIXTURE\GAMES\MonkeyIsland2_DOS_VGA'
$exe = Join-Path $probe 'imuse-probe\scummvm-imuse.exe'
$adlib = Join-Path $root "FIXTURE\CAPTURES\MI2-iMUSE-AdLib-$([guid]::NewGuid())"
python tools/run_mi2_imuse.py $exe $game $save $adlib --seconds 86
python tools/verify_mi2_imuse.py "$adlib\runtime.log" --tag ADL
$roland = Join-Path $root "FIXTURE\CAPTURES\MI2-iMUSE-Roland-$([guid]::NewGuid())"
python tools/run_mi2_imuse.py $exe $game $save $roland --driver windows --seconds 75
python tools/verify_mi2_imuse.py "$roland\runtime.log" --tag ROL
```

The native build needs the pinned CrossRoom source, its compiled archives and Win32 objects, and MSYS2 UCRT64 GCC, SDL2 and zlib. The MSYS shell failed with Windows access denied for its named-object directory. Compiling the instrumented objects and linking with the native toolchain bypassed that shell. The runtime uses SDL dummy video/audio with explicit normal scaler settings. The Roland run uses the Windows MIDI backend with native MT-32 mode for sequencing. This setup verifies resource selection and sequencer behavior. Authentic MT-32 audio output requires a compatible renderer or device. The null MIDI backend loaded ROL but did not activate the sequencer in this fixture.

## Observed playback

Both completed traces restored sound 101 from the room 7 save without a fixture start. The probe invoked the doorway script and observed its original call to script 96 with (7, 9). ScummVM loaded the expected tag for both sound IDs, queued both triggers and dispatched the original MIDI events in this order.

| Step | AdLib | Roland |
| --- | --- | --- |
| Woodtick sound 101 track 0 marker 0 | Tick 13360 | Tick 13360 |
| Released command 263 (queued jump) | Track 3, beat 4, tick 400 | Track 1, beat 4, tick 400 |
| Confirmed jump position | Track 3, absolute tick 1840 | Track 1, absolute tick 1840 |
| Woodtick marker 1 | Tick 1920 | Tick 1920 |
| Marker 1 release | Stop 103, start 103 | Stop 103, start 103 |
| Bar sound 103 sequence start | Track 0, tick 0 | Track 0, tick 0 |
| Bar unconditional hook 0 | Track 0, 40140 to 1740 | Track 0, 40140 to 1740 |

The static example used an earlier marker 0 at tick 3760 and selected track 1. The live runs demonstrate later phase selection and two valid transition tracks. The ingress uses the marker queue's direct jump command, which has no hook identifier. The observed Bar exit hooks were unarmed. The Bar loop itself used hook 0.

Private run directories are `FIXTURE/CAPTURES/MI2-iMUSE-AdLib-Full-20261128` and `FIXTURE/CAPTURES/MI2-iMUSE-Roland-Windows-20261128`. Each contains the runtime log, run provenance and verification JSON. Instrumented executable SHA-256: ff4a2e8236fdb2b00f9feb452d1b6dc1ce3b7138b4e8aef1362a56a9b3123055. Original save SHA-256: 39035338ed89bdfe754f31e390f247c83095f1938aeae6877c0373ad7f72aa0d.
