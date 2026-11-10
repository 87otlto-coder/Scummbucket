# Room 23 lossless frame reference

Two real runs on 2026-11-10 loaded the same private save of the fingerprinted Monkey Island 2 DOS VGA game. Windows SDL2 Surface with Direct3D (frame-reference-v8) and dummy video with the SDL software renderer (v7) each produced 87 paired 320 × 200 frames. All 87 RGB payloads matched across runs. The save already placed the player in Room 23. The optional debugger-equivalent jump was armed but no jump was logged. Neither reference used the interactive debugger.

## Where each measurement occurs

The engine stages three 768-byte RGB palettes on the same SCUMM game-loop iteration, immediately before cyclePalette, immediately after it (the existing V2 trace point), and immediately after palManipulate. A room effect, game script or later palette upload can intervene before the final measurement. Immediately after updatePalette and drawDirtyScreenParts, the engine reads the backend palette, room background, composited room front buffer, depth buffers and complete indexed backend game screen. It records the actor/object state at this boundary. The active capture supports the observed 320 × 144 room, zero horizontal camera offset and 320 × 200 CLUT8 screen. Locking/unlocking the SDL surface forces a redraw and readback has a timing cost.

The engine hands one pending ID to SDL Surface. Immediately before the first subsequent SDL_RenderPresent, SDL_RenderReadPixels captures packed RGB24 from the renderer output with the same ID. Another eligible loop reaching the capture point with its predecessor still pending raises an error. Repeated presentations between game updates are outside the sample set. This is a renderer readback before the OS compositor and physical display. RGB has no final indexed palette. The captured backend palette is the final indexed-stage palette.

The two clocks are monotonic engine wall milliseconds. Their within-pair separation was 0–2 ms. Each loop recorded a 6/6 timer pair. The engine clocks spanned 8.600 s on Windows and 8.598 s headless. Frame IDs establish within-run correspondence. For gameplay timing use the game's timer units. The old mixed log's 12.828 s interval is a wall-clock gap. No extra cycles or gameplay frames are inferred from that gap.

## Results against the 87-PNG native export

| Measurement | Each run |
| --- | --- |
| Archive-decoded background versus engine back buffer | All 46,080 indices identical on 87/87 frames |
| Front buffer versus back buffer | 767 changed indices on each frame |
| Room crop of backend screen versus front buffer | Zero changed indices on 87/87 |
| V2 same-run timer pair and post-cycle palette | Exact on 87/87 |
| Pre-cycle versus post-cycle | Changed on 41/87 |
| Post-cycle versus post-manipulation versus backend palette | All three equal on 87/87 |
| Cross-run match to historical export | 58/87 new frames share a complete post-cycle palette with one or more historical PNGs, covering 80 distinct historical sample IDs |
| Backend RGB reconstructed from indices versus renderer | 59,225 of 64,000 pixels differ on each frame |
| Historical PNG versus renderer room crop at exact palette matches | 46,080 of 46,080 differ, including small channel changes |
| Integer RGB565 truncation and floor expansion model versus renderer | 4,686 or 4,693 pixels still differ on each frame |

The SDL2 Surface implementation creates an RGB565 streaming texture. The simple conversion model accounts for much of the observed difference. For example, an indexed RGB value of (23, 0, 23) was read back as (16, 0, 16). Remaining differences include green-channel rounding and the visible cursor. The report counts exact mismatches including one-unit changes. No historical sample is assigned by nearest timestamp or best visual fit. An exact palette match can have multiple historical sample IDs.

Actor 1 was visible at (85, 118) with costume 1, frame 3, walkbox 2 and forceClip 0. Object IDs 241–243 had state zero. These records and the hashes of all three mask buffers stayed constant across the 87 frames. The comparison image shows the actor missing from the native background. This stationary pose does not validate walking, a depth transition, occlusion correctness, other renderer modes or an entire interactive scene.

The tested executable was ScummVM 2026.4.0dirty with SDL 2.32.10, SHA-256 **1a43ca2593fd0a7312468c15397c373e080c655b08196b24fbbbe04b01b6fc6b**. The launcher records binary/version, arguments, save hash and both archive hashes in run.json. The private JSON reports record engine version, active render/gfx/scaler IDs, renderer name, plane comparisons, palette and file hashes, actor/object rows, depth hashes and both clocks per ID. Windows V2 continued to END at 256. The earlier headless launcher stopped after the frame set, leaving the V2 flushed temporary log without END. Its 87 paired records passed the same checks. Trials v1–v6 produced no usable frame set. Startup trials included an SDL blit failure when switching graphics mode on the command line and timeouts. The final launcher selects SDL Surface in the private configuration before backend setup and permits the save's original MIDI device.

## Reproduce

From PowerShell, use a new build directory. The following copies the configured V2 checkout, including its compiled objects. The installer checks the V2 C++ source against the fingerprinted original and checks the SDL backend source before editing the copy. The incremental build uses MSYS2 UCRT64 and the existing static SCUMM-only configuration.

~~~powershell
$root = 'F:\Dev\SCUMMBUCKET'
cd "$root\SOURCE\ScummBucket"
$original = "$root\TOOLS\ScummVM-P4-Trace"
$build = "$root\TOOLS\ScummVM-P4-Frame-repro"
if (Test-Path $build) { throw 'Choose a new build directory' }
robocopy $original $build /E /XJ /R:1 /W:1 /MT:8
if ($LASTEXITCODE -ge 8) { throw 'Copy failed' }
python -B tools/instrument_room23_frames.py $original $build
if ($LASTEXITCODE) { throw 'Source guard failed' }
$env:MSYSTEM='UCRT64'
& C:\msys64\usr\bin\bash.exe -lc 'cd /f/Dev/SCUMMBUCKET/TOOLS/ScummVM-P4-Frame-repro && make -j4'
if ($LASTEXITCODE) { throw 'Build failed' }
~~~

Choose a new capture and report path per run. Use Pillow for diagnostics. The original save is only copied. The verified save snapshot is under FIXTURE. Add --headless to repeat with dummy video and the software renderer.

~~~powershell
$fixture = "$root\FIXTURE"
$stamp = Get-Date -Format yyyyMMdd-HHmmss-fff
$cap = "$fixture\CAPTURES\Room23\frames-$stamp"
$export = "$fixture\OUTPUT\Room23\native-mixed-20261110-v1"
$report = "$fixture\REPORTS\Room23\frames-$stamp"
python -B tools/run_room23_frames.py --exe "$build\scummvm.exe" --game "$fixture\GAMES\MonkeyIsland2_DOS_VGA" --output $cap --save "$fixture\CAPTURES\Room23\frame-reference-v7\saves\monkey2.s01" --music-driver "windows_Microsoft GS Wavetable Synth" --enter-room
python -B tools/compare_room23_frames.py --capture $cap --export $export --output "$report.json" --preview "$report.png"
$env:SCUMMBUCKET_REFERENCE_CAPTURE = $cap
$env:SCUMMBUCKET_NATIVE_EXPORT = $export
$env:SCUMMBUCKET_MI2_ARCHIVE = "$fixture\mi2.zip"
$env:SCUMMBUCKET_MI2_GAME = "$fixture\GAMES\MonkeyIsland2_DOS_VGA"
$env:SCUMMBUCKET_ROOM23_MIXED_LOG = "$fixture\CAPTURES\Room23\room23-normal-20261110-081315-043.raw.log"
python -B -m unittest discover -s tests -q
~~~

The benchmark regression uses this specific save and historical export. The full configured run executed 249 tests with four skipped. For manual entry use a visible window, omit --enter-room and allow a longer --timeout. On a fresh start, the user's procedure is to press 0 repeatedly at the copy-protection prompt. Enter Room 23 via gameplay or the debugger as described in the Windows trace runbook. To study depth masking, repeat with a moving actor crossing the foreground post and inspect the mask bits at the actor's changing position.

## Private record layout

engine-NNN.bin begins with a text header (R23E1, ID, wall ms, timer, timer-next, room screen Y, mask count, render mode, graphics mode, scaler), version, actor rows (ID, x, y, visible, costume, frame, walkbox, forceClip), object rows (ID, state), then DATA and a newline. Packed bytes follow in order: four RGB888 palettes of 768 bytes, 320 × 144 background indices, 320 × 144 front indices, mask-count planes of 40 × 144 packed bytes, and 320 × 200 backend indices. Rows exclude pitch padding. present-NNN.bin carries R23D1, ID, wall ms, width, height and SDL renderer name on one line followed by width × height × 3 RGB bytes.

Under FIXTURE, CAPTURES/Room23/frame-reference-v8 contains the Windows run. REPORTS/Room23/frame-reference-v8-final.json and frame-reference-v8-preview.png contain its diagnostics. The corresponding headless report is frame-reference-v7-final.json. The launcher terminates its isolated process after both the frame set and V2 log have closed or after timeout. The comparator requires all 87 complete engine/present pairs and matching V2 records, even for a partially closed legacy log. No game, save, capture, comparison image or binary belongs in Git.
