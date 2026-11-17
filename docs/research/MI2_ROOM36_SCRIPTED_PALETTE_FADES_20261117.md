# MI2 Room36 — 40-step VGA palette speed fades, local scripts 201 and 202 (17 November 2026)

**Evidence:** Read-only `MONKEY2.001` original DOS VGA archive, SHA256 `ad045372e0d49626503bb50fca29a687ec8e01ef75d9b8bca702a366d143819e`. Narrow independent opcode-boundary walk checked against ScummVM v2026.4.0 `o5_roomOps`, variable array indirection and reverse-branch semantics. **No actual ScummVM/DOS execution, no independent descumm run, no palette/framebuffer comparison.** Original game resources remain private and unchanged.

## Full aligned script census

| Local script | Decoded file body offset | Body bytes | Narrow walker consumed | Instructions | Jump targets | `breakHere` source sites |
| --- | --- | ---: | ---: | ---: | --- | ---: |
| 201 | `0x2BFC68` | 95 | 95/95 | 18 | 4/4 aligned | 1, executed repeatedly |
| 202 | `0x2BFCD0` | 124 | 124/124 | 23 | 4/4 aligned | 1, executed repeatedly |

**Important:** Both have **one opcode location** for `breakHere`, but the surrounding bounded loop executes that yield **40 times** if `Var[49] == 19` and the script runs uninterrupted. Both issue **40 × 5 = 200** dynamic `SO_CYCLE_SPEED` calls over the 40 passes in that case, not 200 different opcodes.

### Room36 local script 201 — gradual palette-cycle shutdown

- Initial values: `Local[1..5] = [33,32,35,21,20]`.
- Guard: if `Var[49] != 19` (VGA), jump to stop.
- Outer counter `Local[6]` starts at **1**, repeats while ≤ **40**.
- Inner `Local[7]` visits cycles **1 through 5** on each pass.
- For each cycle `i`, call `roomOps.cycleSpeed(i, Local[i])`, then decrement `Local[i]` by one and clamp negatives to zero.
- After all five cycles, `breakHere` **once**, increment outer counter, repeat.
- During the initial passes, the palette cycles gradually slow or stop as their speed parameters decrease. The final script-set delay is **zero** for every cycle.

Representative first, 2nd, and final *speed parameters supplied by this script*, not measured render phases:

| cycle | pass1 input | pass2 input | last pass input | final speed state |
| ---: | ---: | ---: | ---: | ---: |
| 1 | 33 | 32 | 0 | 0 |
| 2 | 32 | 31 | 0 | 0 |
| 3 | 35 | 34 | 0 | 0 |
| 4 | 21 | 20 | 0 | 0 |
| 5 | 20 | 19 | 0 | 0 |

### Room36 local script 202 — gradual palette-cycle ramp-up

- Target values: `Local[7..11] = [33,32,35,21,20]`.
- Initial current values: `Local[1..5] = [0,0,0,0,0]`.
- Guard: `Var[49] == 19`, otherwise terminate.
- Outer counter `Local[12]` starts **1**, repeated through **40**.
- Inner `Local[13]` visits cycles **1–5**.
- For each cycle `i`, call `roomOps.cycleSpeed(i, Local[i])`, increment `Local[i]`, and clamp it to `Local[6+i]` target.
- Yield once after each full five-cycle sweep and repeat. The first emitted speed is **0** and subsequent steps increase toward the target. All five speeds reach target before the last pass; the final live palette-speed values are the five targets.

### Why the indirect syntax matters

Pinned ScummVM [`script.cpp::readVar`](https://github.com/scummvm/scummvm/blob/v2026.4.0/engines/scumm/script.cpp) treats SCUMM v5 variable reference bit `0x2000` as **indirection**, consuming a following word: if the following word also has bit `0x2000`, its stripped variable reference supplies the index to add. E.g. bytecode `00 60 07 60` evaluates `Local[0 + Local[7]]` for the current cycle in script201. In script202, `06 60 0d 60` indexes target array `Local[6 + Local[13]]`.

Pinned [`script_v5.cpp::o5_roomOps`](https://github.com/scummvm/scummvm/blob/v2026.4.0/engines/scumm/script_v5.cpp) interprets `SO_CYCLE_SPEED` speed `b` as `delay = (b != 0) ? floor(16384/(76*b)) : 0`; the opcode's **subop `0xD0`** uses variable references for cycle ID and speed, unlike Room36 ENCD's direct immediate subop `0x10`. Simply scanning for literal `33 10` would **miss** both 40-pass gradual transitions.

Both source scripts use `o5_isLess` / `o5_isGreater` with `jumpRelative` branch-on-false semantics. Every eight-byte indirect reference is fully accounted for; all control destinations align.

## Connected environmental scene mechanism

From [Room36 pump cutscene script200](MI2_ROOM36_PUMP_CUTSCENE_SCRIPT200_20261117.md):

- **Bit92 initially 0** → the action eventually sets Bit92=1, and **starts Room36 script201** (fade speeds down to zero).
- **Bit92 initially 1** → the action eventually sets Bit92=0, and **starts Room36 script202** (ramp speeds up from zero).
- Both directions first run the original actor-costume pump cutscene (158 or 78 `breakHere` yields based on Bit763, subject to cutscene skip), then source-dispatch to the gradual palette-speed transition.
- Room36 ENCD separately uses Bit92 and video mode to choose enabled/disabled initial cycle speeds; Room35 ENCD also gates its object364 eight-image-state loop on Bit92. Room37 ENCD sets Bit92=1.

**Classification:** source-aligned *script-controlled palette fades and cross-room environmental state*, not “CYCL records automatically looping forever.”

### Fidelity and test requirements

For a real P4 renderer, store timer deltas, one per-pass yield and all 200 cycle-speed calls in temporal order. Convert **speed arguments to engine delays using integer division**; the mapping is nonlinear and often yields the same delay for several successive speed values. Preserve `cyclePalette()`'s phase accumulator when `delay` changes; changing speed does not itself prove a palette rotation or a full redraw. Do **not** model “40 opacity frames” or “40 actual palette rotations”: source instructions modify the *speed* of RGB palette cycling, with visible changes dependent on cycle counters, update order, current indexed pixels and run-time delay.

The `startScript(201/202)` is nested/immediate within Room36 script200's final transition. Retain room-qualified script identity, since Room35 has an unrelated **local script202** controlling object364's stored image states.

**Next runtime gate:** separately capture both pump directions under VGA with `(Bit92, Bit763)` initial states documented; measure `room36/script200` finishing, `room36/script201/202` calls, 40 actual yielded iterations, five cycle-speed arguments and resulting `_colorCycle[*]` delays, `_currentPalette` RGB hashes, sound35, and the native indexed composite. Compare a deliberately skipped pump cutscene for correct final state.

No native palette frame sequence or copyrighted artwork has been generated or committed.
