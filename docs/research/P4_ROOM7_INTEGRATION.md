# Room 7 integration evidence, 10 November 2026

> **Update — 12 November 2026:** This 10 November research log is retained as **historical evidence at the time of the initial Room 7 capture**. Subsequent P3/P4 work on the same debugger-equivalent Room 23→7 sweep added [16/32-color COST decoding](../../scummbucket/classic_costume.py), [scaled costume composition](../../scummbucket/classic_scale.py) and [an independent full-scene verifier](../../tools/verify_room7_scene.py). The follow-up Work session reported **87/87 indexed front-buffer matches (4,008,960 pixels, zero mismatches)** and **778 mismatches with ZP01 disabled**, reduced to zero with clipping restored. Scenery actor 11 was independently matched in frames 36–81, and scaled Guybrush completed the sampled scene. These are **private paired-capture observations**, not newly rerun Windows CI tests. Statements below about 'unsupported' scaled/full-front composition reflect the earlier stage only. **Natural room entry, other routes and editions remain unverified.** See [portable preview status](P4_ROOM7_PORTABLE_PREVIEW.md) and [draft integration review](https://github.com/87otlto-coder/Scummbucket/pull/8).

Remote research branch HEAD was verified as 68994bd1cce91a3bed8adb3dce479fb122a74afa before work. The desktop checkout started there. The separate F-drive checkout was clean at 1b5d291 and was preserved.

## Archive decoded

Room 7 is 784 by 144 pixels, containing 98 eight-pixel SMAP strips. The viewport is 320 by 144, allowing X offsets 0 through 464. ROOM starts at decoded MONKEY2.001 offset 392340 and has length 82695. SMAP starts at 394658 with length 70134. ZP01 starts at 464792 with length 1976 and decodes to 784 by 144 with 18366 set pixels. CLUT starts at 393816. The indexed panorama SHA-256 is 843f5d1d81ed8bb8f7353a0c5b3c52d2229505becbd47a411b3cd4314b5bccfc.

Six CYCL records cover 16–18, 176–177, 178–179, 180–181, 182–183, 184–185. Raw rates are 384, 384, 459, 306, 228, 153. All flags are zero. The manifest retains source records and hashes.

Twenty paired objects are IDs 40–59. Four have one stored image each. Objects 41, 42, 45 and 57 are respectively 24x32, 56x32, 32x16 and 8x16, each with ZP01. Transparent index is 191. No multiple stored image states were found. Costumes 94, 95, 108, 142 and scripts 77, 96, 148 are stored in this bundle. Storage alone establishes no execution relationship.

## Engine observed

The isolated build is TOOLS/ScummVM-P4-Room7-20261110-a. Capture is FIXTURE/CAPTURES/Room7/sweep-20261110-a. All paths below are relative to F:/Dev/SCUMMBUCKET.

The run loads a copy of the Room 23 save and performs the debugger-equivalent jump. Normal Room 7 gameplay entry remains unverified. Three application saves were inspected by their version-124 serialized room field and all contained room 23. Save hashes and executable/archive hashes are in run.json.

Frames 1–5 precede the injected walk and camera pan. Frame 5 requests walking to world width minus 48 at Y=130 and pans toward the far edge. The camera advances eight pixels per update, reaches X=464 on frame 63 and remains there through frame 87. Guybrush is still walking at frame 87. His scale is 150 or 155, selected depth plane 1. Position, costume, logical frame, walkbox, forceClip, movement, facing, animation counter and sixteen limb cursors are recorded. Camera center, viewport origin, room dimensions, all present actors and their scales, live script slots and object states accompany each frame.

Across 4,008,960 pixels per comparison, archive background crops and engine back buffers have zero index mismatches. Archive ZP01 crops and runtime plane 1 have zero mismatches. Plane zero is empty throughout. Indexed front buffers match the final indexed backend room crop throughout. Front versus background differs at 94464 pixel observations, including actors. Independent front reconstruction remains unsupported for this scaled scene.

Four palettes per frame cover pre-cycle, post-cycle, post-manipulation and backend. The existing continuous scheduler, initialized from frame 1 pre-cycle and advanced with the recorded timer pair, matches all 87 post-cycle palettes without phase fitting. There are 35 distinct post-cycle palettes. Post-manipulation and backend palettes match post-cycle throughout. This validates this run only.

## Script evidence and inference

Private disassembly is FIXTURE/REPORTS/Room7/scripts-20261110-a. External descumm returned zero for all ten ENCD/EXCD/LSCR chunks. ENCD installs actor 11 with costume 142, IgnoreBoxes and NeverZClip, assigns it to room 7 and installs scroll script 207. Script 207 computes world X as 590 - ((camera X - 624) / 2), Y=144. Observed actor positions agree after scroll updates, identifying a camera-controlled scenery mechanism. Its 32-color COST format is outside the current 16-color compositor.

ENCD conditionally sets object 57 state 1 when Bit[567] is set. Object states did not change during this capture, and object 57 stayed zero. Disassembly establishes instruction alignment, while conditional gameplay execution remains unverified.

Sound references encountered opportunistically include startSound 48, 101, 151 and soundKludge operations 266, 268, 272, 11 and -1 in local scripts. Runtime music entry behavior and full audio analysis remain deferred.

## Reproduction

Use the SOURCE checkout with Python and Pillow. Choose fresh output names on every run.

~~~powershell
python -B -m scummbucket panorama F:/Dev/SCUMMBUCKET/FIXTURE/GAMES/MonkeyIsland2_DOS_VGA --room 7 --output F:/Dev/SCUMMBUCKET/FIXTURE/OUTPUT/Room7/native-NEW
python -B tools/instrument_room7.py F:/Dev/SCUMMBUCKET/TOOLS/ScummVM-P4-Walk-20261110-a F:/Dev/SCUMMBUCKET/TOOLS/ScummVM-P4-Room7-NEW
~~~

Before instrumentation, copy the pinned walk build to the fresh TOOLS destination using the non-destructive copy procedure in P4_ROOM23_WALK.md. Compile that copy with the existing MSYS2 UCRT64 make procedure.

~~~powershell
python -B tools/run_room23_frames.py --room 7 --game F:/Dev/SCUMMBUCKET/FIXTURE/GAMES/MonkeyIsland2_DOS_VGA --exe F:/Dev/SCUMMBUCKET/TOOLS/ScummVM-P4-Room7-NEW/scummvm.exe --save F:/Dev/SCUMMBUCKET/FIXTURE/CAPTURES/Room23/frame-reference-v7/saves/monkey2.s01 --enter-room --walk normal --headless --music-driver 'windows_Microsoft GS Wavetable Synth' --output F:/Dev/SCUMMBUCKET/FIXTURE/CAPTURES/Room7/sweep-NEW
python -B -m tools.compare_room7 F:/Dev/SCUMMBUCKET/FIXTURE/CAPTURES/Room7/sweep-NEW F:/Dev/SCUMMBUCKET/FIXTURE/OUTPUT/Room7/native-NEW F:/Dev/SCUMMBUCKET/FIXTURE/REPORTS/Room7/sweep-NEW
~~~

The original comparison and archive-background playback are FIXTURE/REPORTS/Room7/sweep-20261110-a/report.json and play.html. Playback uses recorded viewport offsets and palette samples. It omits actor/scenery composition.

For normal-entry evidence, enter the scene through gameplay, save immediately in a new slot, then pass that save to the launcher with --room 7 and omit --enter-room. The optional --walk normal still injects the research walk/pan. A precise gameplay route from the available Room 23 saves has not been verified.

## Validation limits

The first regression attempt failed because temporary-file writes were denied by the execution environment. The retry uses normal temporary-file access and records results at FIXTURE/REPORTS/Room7/tests-20261110-a.txt. The instrumented build succeeded with one compiler warning about an always-false unsigned xstart comparison. The sweep format retains the R23E1 identifier for compatibility, with a required camera row distinguishing geometry. The verifier intentionally supports this pinned 320x144 viewport and validates world width independently.

Scaled Guybrush composition, 32-color scenery composition, real entry, runtime audio identifiers, and changing object-state captures remain pending. Indexed background/mask comparisons provide the independent image evidence. RGB readbacks retain paired presentation provenance.
Regression retry completed successfully with 256 tests, four skipped, including configured private Room 23 frame, walk and costume fixtures.
