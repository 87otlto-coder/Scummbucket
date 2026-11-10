# Room 23 foreground-post crossing

On 10 November 2026 two headless SDL software runs loaded the same private Room 23 save. After the engine wrote frame 5, the hook called Guybrush's normal `startWalkActor(280, 125, -1)` once. Pathfinding brought him from (85, 118) to (280, 137). He first moved on frame 6 and reached his standing pose on frame 38. Neither a debugger nor timed mouse input was needed.

The control overrides only actor 1's costume renderer depth selection to plane zero after frame 5 in Room 23. Each frame records the last plane selected in costume preparation **before** the override. On held poses that selection can come from an earlier redraw. The frame also records position, visibility, costume ID, logical costume frame, walkbox, forceClip, movement flags, facing, animation counter, and 16 limb sequence positions. The original four palette stages, virtual screen planes, runtime masks, full indexed screen, and SDL presentation retain the frame-reference format and ID. The extra header row is `walk plane control moving facing animCounter curpos[0] ... curpos[15]`.

## Indexed visibility

Each count measures pixels with an index distinguishable from the background. Hidden counts come from the normal/control difference. Pixels painted with the same index as the background cannot be counted this way. Actor 1 stayed logically visible throughout.

| Frame | Foot x, y | Box / selected plane | Visible | Hidden |
|---:|---|---|---:|---:|
| 1–5 | 85, 118 | 2 / 0 | 767 | 0 |
| 25 | 172, 137 | 1 / 0 | 551 | 0 |
| 26 | 187, 137 | 12 / 2 | 635 | 8 |
| 27 | 195, 137 | 12 / 2 | 517 | 0 |
| 28 | 203, 137 | 12 / 2 | 455 | 81 |
| 29 | 211, 137 | 12 / 2 | 354 | 329 |
| 30 | 219, 137 | 12 / 2 | 4 | 546 |
| 31 | 227, 137 | 12 / 2 | 6 | 545 |
| 32 | 235, 137 | 12 / 2 | 196 | 447 |
| 33 | 243, 137 | 12 / 2 | 440 | 77 |
| 34–35 | 251–259, 137 | 12 / 2 | 536, 683 | 0 |
| 36 | 267, 137 | 12 / 2 | 547 | 3 |
| 37 | 275, 137 | 12 / 2 | 551 | 0 |
| 38–87 | 280, 137 | 12 / 2 | 660 | 0 |

The actor traversed boxes 2, 1 and 12, selecting planes 0, 0 and 2 respectively. Entry into box 12 occurred on frame 26. The first eight blocked indices lay at x=200–203, y=135–137. The next gait pose cleared the mask before the main overlap on frames 28–33. Frame 36's three blocked indices lay farther right at x=269–271, y=92.

Both runtime depth planes matched independent RLE decodes of RMIM/IM00/ZP01 and ZP02 on every frame in both runs, with 1,880 and 3,315 set bits respectively. Plane zero was empty. Matching frame IDs also had identical actor/object records, limb state, timer pairs, selected plane and all four palette stages. Each run's post-cycle palette and timer pair matched its own V2 log. The native background matched both engine back buffers, and the backend room crop equalled each front buffer throughout.

For every one of the 4,008,960 paired room pixels, selecting the background index wherever the selected mask bit was set and the control front index elsewhere reproduced the normal front index exactly. There were 2,036 suppressed pixel observations across eight frames. This tests one route, one save, and the indexed composition stage. The route never selected plane 1. SDL RGB readbacks establish presentation pairing, but the counts above use palette indices. The control is a separate engine run and the comparison requires matching poses and palettes.

## Reproduce on the research machine

Run from the updated ScummBucket SOURCE checkout in PowerShell with Python and Pillow. The setup uses the verified frame-v2 tree described in [the frame-reference runbook](P4_ROOM23_FRAME_REFERENCE.md). Each reproduction creates new paths under TOOLS and FIXTURE.

~~~powershell
$root = 'F:/Dev/SCUMMBUCKET'
$f = "$root/FIXTURE"
$stamp = Get-Date -Format yyyyMMdd-HHmmss-fff
$old = "$root/TOOLS/ScummVM-P4-Frame-v2"
$build = "$root/TOOLS/ScummVM-P4-Walk-$stamp"
if (Test-Path $build) { throw 'Choose a new build path' }
robocopy $old $build /E /XJ /R:1 /W:1 /MT:8
if ($LASTEXITCODE -ge 8) { throw 'Copy failed' }
python -B tools/instrument_room23_walk.py $old $build
if ($LASTEXITCODE) { throw 'Source guard failed' }
$env:MSYSTEM = 'UCRT64'
& C:/msys64/usr/bin/bash.exe -lc "cd /f/Dev/SCUMMBUCKET/TOOLS/ScummVM-P4-Walk-$stamp && make -j4"
if ($LASTEXITCODE) { throw 'Build failed' }
$env:SCUMMBUCKET_MI2_GAME = "$f/GAMES/MonkeyIsland2_DOS_VGA"
$env:SCUMMBUCKET_NATIVE_EXPORT = "$f/OUTPUT/Room23/native-mixed-20261110-v1"
$cap = "$f/CAPTURES/Room23/walk-$stamp"
$report = "$f/REPORTS/Room23/walk-$stamp"
foreach ($mode in 'normal','control') {
    python -B tools/run_room23_frames.py --exe "$build/scummvm.exe" --game $env:SCUMMBUCKET_MI2_GAME --save "$f/CAPTURES/Room23/frame-reference-v7/saves/monkey2.s01" --headless --music-driver 'windows_Microsoft GS Wavetable Synth' --walk $mode --output "$cap-$mode"
    if ($LASTEXITCODE) { throw "Capture failed ($mode)" }
    python -B tools/compare_room23_frames.py --capture "$cap-$mode" --export $env:SCUMMBUCKET_NATIVE_EXPORT --output "$report-$mode-frames.json"
    if ($LASTEXITCODE) { throw "Reference verification failed ($mode)" }
}
$env:SCUMMBUCKET_WALK_NORMAL = "$cap-normal"
$env:SCUMMBUCKET_WALK_CONTROL = "$cap-control"
python -B -m tools.compare_room23_walk --normal "$cap-normal" --control "$cap-control" --game $env:SCUMMBUCKET_MI2_GAME --output "$report.json"
if ($LASTEXITCODE) { throw 'Walk comparison failed' }
$env:SCUMMBUCKET_REFERENCE_CAPTURE = "$f/CAPTURES/Room23/frame-reference-v8"
$env:SCUMMBUCKET_MI2_ARCHIVE = "$f/mi2.zip"
$env:SCUMMBUCKET_ROOM23_MIXED_LOG = "$f/CAPTURES/Room23/room23-normal-20261110-081315-043.raw.log"
python -B -m unittest discover -s tests -q
~~~

Verified suite result: 251 tests run, four skipped. The verified private captures use the prefix `CAPTURES/Room23/walk-20261110-a`. The per-frame report is `REPORTS/Room23/walk-20261110-a.json` (SHA-256 `ab34f9c0ccbac98561494e4014addc5fb7a84258eaa5d577556e2bae129f9550`). The instrumented executable SHA-256 was `b9b55ec2fa34805f6e10bc797334f5e0adbb4273e88750400232d590d209851b`. The save SHA-256 was `968bbdfaa855f35e0e89c271172d3d185448f256213f87d527cfa2b18ccea8ad`. The launcher copies that save into each new capture directory. Preparing a replacement save manually yields a different experiment and requires rechecking the route and frame expectations.
