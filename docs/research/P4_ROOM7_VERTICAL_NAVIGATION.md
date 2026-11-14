# Room 7 vertical navigation and foreground occlusion

Original Monkey Island 2 DOS VGA, 14 November 2026. A fresh copy of the pinned Room 7 ScummVM tool loaded a byte-verified copy of monkey2-1.s01. Ordinary mouse clicks took Guybrush from the low bridge onto the right cliff, back across the room, into the left ship, and out via the stairway. The renderer ran normally. The capture contains 1,149 Room 7 engine/presentation pairs. Its two Room 7 segments are separated by 151 unobserved engine ticks. See the [continuous doorway protocol and private rerun](P4_ROOM7_DOORWAY.md).

## Runtime measurements

Y increases downward. Coordinates below are room coordinates. Frame numbers refer only to this replay.

| Section | Frames | World origin | Walkboxes in order | Viewport left | X/Y scale | Indexed errors with / without ZP01 |
|---|---:|---|---|---:|---:|---:|
| Low bridge to cliff stop | 448–470 | (571,70) → (742,47) | 28, 19, 20, 21, 22 | 464 | 255 | 0 / 2,701 |
| Walkway into ship | 927–961 | (141,78) → (54,54) | 1, 23 | 0 | 150 | 0 / 3,531 |
| First exterior frame after return through stop | 962–987 | (55,55) → (105,77) | 23, 1 | 0 | 150 | 0 / 3,248 |

The cliff stop persisted through frame 555. The rendered anchor moves with the world origin after viewport subtraction. Actor elevation was zero throughout. The trip between these sections did involve horizontal camera travel and scale changes, including 201, 155 and 150. At the left entrance a decrease of room Y on the way in reverses on the return. Foreground artwork can hide most of the costume during that change. On return frame 962, removing ZP01 changes 228 indexed pixels. At the stop on frame 987 it changes one.

## What the comparisons establish

The existing Room 7 integration, renderer source map and costume 142 validation describe the archive geometry and compositor. The debugger-equivalent 87-frame sweep was an injected walk/pan (778 unmasked index errors). The accepted 87-frame native-save sequence established restoration from the supplied save. This experiment uses a separate capture.

At the draw call the hook records the selected plane, renderer anchor, costume ID, facing, scales and 16 limb cursors. At frame end it records the actor origin, camera, box, logical frame, movement, clipping state and elevation. There were 694 sampled draws. On the other 455 frames the comparison carries the last drawn pose within the same continuous segment. The pinned DOS renderer checks forceClip, NeverClip and the box mask to select a plane. Its draw Y subtracts actor elevation. COST command 0x79 stops a limb while preserving its cursor. The comparison derives the walking stop bits from the archive's directional animation initialization. It uses the existing costume painter and the previously established static actor 11 pose.

All 52,945,920 Room 7 indexed front pixel observations matched across all 1,149 frames. Archive background and ZP01 crops matched both engine reference planes as applicable, and the indexed backend room crop matched the front throughout. Omitting Guybrush's plane-1 mask caused 81,234 erroneous pixel observations. Repeated frames contribute separately. Every sampled section selected plane 1. Private mask overlays mark pixels whose visible palette index changes in magenta and the projected anchor in green. The world route appears in yellow. Each JSON row identifies the engine and presentation bytes by SHA-256. Presentation IDs and payloads were parsed. The equality result concerns indexed pixels.

## Reference video and limits

The supplied 1.mp4 (SHA-256 2c6a976ce4f5f698413fbeaaa27b3e8b125ff16c1f650c8e017e70b6fb390c61) was inspected around 15.5–18 and 22–23 seconds. The rail and uprights obscure the threshold. Around 33–39 seconds the feet rise relative to the bridge deck and remain higher against the cliff. These are qualitative visual observations. No timestamps or screen pixels were fitted to this replay. Exact inputs, frame correspondence and save provenance for the recording remain unknown. The trace covers the Room 7 side of the ship doorway. Object identities for individual rail pixels and behavior on untested routes remain open.

## Reproduction and private evidence

Private capture under FIXTURE/CAPTURES/Room7 is navigation-b9d905869e894798b5d7744caaf66a5a. The accepted analysis is FIXTURE/REPORTS/Room7/navigation-b9d905869e894798b5d7744caaf66a5a-v2/navigation.json (SHA-256 772fe65fa8edbda456973de6bc31f400a6fda2b3a1843e9f13d2069a55866826). The first comparison, preserved alongside it, produced 5,518 mismatches before stopped-limb handling. The null-audio launch ended before any frames, and the live launch finished before its analysis module had been installed. The saved pairs were subsequently analyzed offline. The private tool build required correcting protected-field access and retained the earlier unsigned xstart compiler warning.

To reproduce the tool, copy TOOLS/ScummVM-P4-Room7-20261110-a into a fresh TOOLS build directory, run tools/instrument_room7_navigation.py with the original and copy as arguments, then build the copy with the existing MSYS2 UCRT64 make procedure. The verified navigation executable SHA-256 is b7700b37ba47eeaeb74c23c6cf04263d6ae1fac912ba94c25ede9d6a21e85df1.

The following PowerShell command uses the installed navigation build. Click through the desired route, then close the game. Each launch reserves a fresh private capture folder and produces its own report. The tool captures up to 2,400 Room 7 frames.

```powershell
& { Set-Location 'F:\Dev\SCUMMBUCKET\SOURCE\ScummBucket'; python -B -m tools.capture_room7_navigation --root 'F:\Dev\SCUMMBUCKET' }
```
