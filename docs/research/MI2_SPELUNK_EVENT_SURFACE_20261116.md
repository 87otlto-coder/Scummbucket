# MI2 spelunking — rendering event surface and phase ordering (16 November 2026)

This is a code-reading note based on the pinned ScummVM v2026.4.0 ScummEngine v5 path. It is NOT an observed original DOS runtime trace, not a statement that a specific MI2 room executes every listed operation, and not a new ScummBucket implementation. Source excerpts were inspected on GitHub without running a debugger.

## Why a room inventory cannot establish all animation

The following mechanisms can change the visible result but are not enumerated by a static CYCL + multistate-OBIM inventory:

| Mechanism | Source entry point | Required observable data |
| --- | --- | --- |
| Palette cycles | palette.cpp initCycl / cyclePalette | Initial CYCL, active delays, counter phases, timer pair, direction, post-cycle palette |
| Scripted palette color change | script_v5.cpp o5_roomOps SO_ROOM_PALETTE (v5 branch) | RGB operands, chosen color index, palette before/after |
| Scripted intensity/shadow change | SO_ROOM_INTENSITY, SO_RGB_ROOM_INTENSITY, SO_ROOM_SHADOW | Shadow-palette mappings and affected color range |
| Palette transform / fade | SO_ROOM_TRANSFORM, SO_ROOM_FADE, palette.cpp palManipulateInit | Source string palette resources, manipulation time, step order and resulting RGB |
| Scripted cycle-speed override | SO_CYCLE_SPEED | Active cycle ID and new delay; decoded CYCL raw rate alone is not sufficient |
| Actor/costume state changes | o5_actorOps, o5_animateActor; actor.cpp / costume.cpp | Actor id, COST id, command/chore, limbs/cel cursors, frame phases, clip/scale and loaded palette |
| Room/camera movement | SO_ROOM_SCROLL, o5_panCameraTo, o5_setCameraAt, camera processing | Camera current/last/dest; room width/viewport; actor world-to-screen coordinates |
| Object image/state change | o5_drawObject, o5_setState; object.cpp | Object id, selected state/variables, placement and dirty rectangles, image/mask and alpha mode |
| Scheduler/conditional timing | o5_wait, o5_delay, o5_delayVariable, breaks and callers | Script slot, program counter, pause state, message/actor/camera gates, timer units and branch state |

Important: a room with zero CYCL *records* can still change palette colors through v5 roomOps, and an object with one stored image can still appear/disappear or move under scripts. Such cases must not be labeled static solely from archive counts.

## Render-phase ordering in pinned ScummVM v5

Source: engines/scumm/scumm.cpp ScummEngine::scummLoop (approximately lines 3250–3355 at v2026.4.0). For the ordinary nonempty room path (and omitting other initialization/input cases):

1. Pre-draw script stage: runAllScripts() and checkExecVerbs() for game versions below 7, plus checkAndRunSentenceScript().
2. Advance movement and scene state: walkActors(), moveCamera(), updateObjectStates(), dialogue update.
3. scummLoop_handleDrawing(): redraw background when camera/current dirtiness demands; processDrawQue() to draw room objects.
4. scummLoop_handleActors(): set redraw flags, reset actors' background, optional v5 flashlight effect, processActors().
5. scummLoop_handleEffects(): cyclePalette() (supported v4/v5), palManipulate(), then fade handling.
6. Run VAR_MAIN_SCRIPT if configured; updatePalette(); drawDirtyScreenParts().
7. Sound/frame completion follows, and camera._last is assigned camera._cur.

The exact order matters: an event observed at a script call site is not automatically visible in the preceding screen snapshot; a pixel capture, an object-state trace and a palette snapshot can refer to different points within one engine update. Record the phase, not just frame number or timestamp.

Room 7 palette research already separates pre-cycle/post-cycle/post-manipulation/backend palette. Generalize this explicit phase vocabulary to object and actor changes rather than fitting individual phase offsets.

## Source-specific caveats

- script_v5.cpp o5_roomOps subopcode 16 SO_CYCLE_SPEED rewrites _colorCycle[a-1].delay via (b != 0) ? 0x4000/(b*0x4C) : 0. The initial archive CYCL rate-to-delay conversion may therefore cease to describe an active cycle.
- o5_roomOps subopcode 15 SO_ROOM_TRANSFORM calls palManipulateInit(); the underlying source can be string palette resources, so a room's CLUT and CYCL records alone cannot reconstruct this effect.
- o5_wait suboperations cover waiting for actor motion, message, camera destination and sentence completion; o5_delay and o5_delayVariable mark the executing script paused. A simple frame-per-object-state animation export cannot faithfully represent such asynchronous, condition-gated sequences.
- object.cpp getObjectImage selects IMxx by state; drawObject returns early when that resource is missing. Room 48 contains 34 zero-image objects, making it a useful negative test for fabricated animation frames.
- script_v5.cpp has optional Monkey Island 2 enhancement workarounds in the v5 object-opcode paths: room 13 object 108 correction and room 22 object 237 Captain Dread script handling. Engine build and enhancement options belong in provenance; no comparison should silently equate enhanced ScummVM behavior with original DOS execution.

## Research-only experiment design for next Work/debugger window

### Room 44 — controlled object-state experiment

Disassemble ENCD and LSCR 201, prove alignment at source offsets in MI2_SPELUNK_STRUCTURE_20261116.md, trace variable 161/162/163 and states of 452/453/454/461. Record potential branch conditions and message/wait gates. Only after live runtime capture may we assign event durations.

### Room 48 — zero-image plus depth experiment

Disassemble ENCD and LSCR 202, 206, 207, 209, 211, 212. Reconstruct which script events change visibility of image-bearing objects (512, 514, 515, 517, 519, 540, 546) and separate logical-only object states from rendered images. Capture and independently compare ZP01/ZP02/ZP03 + actor footprints; no assumptions that zero-image objects produce pixels.

### Room 55 — coordinated many-object experiment

Focus on LSCR chunks 201–207 and 212, where multiple drawObject-like raw patterns cluster. First verify actual instruction boundaries with descumm (the current static pattern survey is UNALIGNED). Derive a conditional event DAG with object, state, script, gate and provenance; avoid inventing a cyclic frame schedule.

### Room 72 — simultaneous reset experiment

Investigate the source-predicted LSCR 200 reset of objects 731–748 and draw states of 731–734. Determine whether visible state changes are synchronized within one engine tick or separated by script yields; runtime appearance remains unknown.

## Trace/schema proposal (not implemented)

Proposed row fields: source edition hashes; engine build/flags; room and camera current/last/dest; engine update counter and phase; script slot/bytecode offset; opcode and decoded operands; object id/state before/after; COST id/actor id/chore and scaling; loaded palette hash before/after with timer pair; background/object Z-plane image hashes; native indexed framebuffer hash; event cause classification (archive-decoded/source-observed/runtime-observed/inferred/synthetic); error/unsupported diagnostics.

A useful trace should support reconstructing a frame *from resource data plus observed control state*, then comparing indexed front pixels independently to the captured engine output. Captured final pixels are references, never source sprites.

Pinned sources:
- https://github.com/scummvm/scummvm/blob/v2026.4.0/engines/scumm/scumm.cpp
- https://github.com/scummvm/scummvm/blob/v2026.4.0/engines/scumm/script_v5.cpp
- https://github.com/scummvm/scummvm/blob/v2026.4.0/engines/scumm/palette.cpp
- https://github.com/scummvm/scummvm/blob/v2026.4.0/engines/scumm/object.cpp

No Windows verification, runtime capture, frame comparisons or repository source-code changes were made in this source-reading session.
