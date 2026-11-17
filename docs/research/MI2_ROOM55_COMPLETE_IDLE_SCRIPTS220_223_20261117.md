# MI2 Room55 — exhaustive idle/fallback scripts220–223 (17 November 2026)

**Evidence:** read-only original DOS VGA `MONKEY2.001`, SHA256 `ad045372e0d49626503bb50fca29a687ec8e01ef75d9b8bca702a366d143819e`; independent narrow SCUMM v5 opcode decoding of *all original bytes* in four Room55 local scripts, checked against pinned [ScummVM v2026.4.0 v5 opcode handlers](https://github.com/scummvm/scummvm/blob/v2026.4.0/engines/scumm/script_v5.cpp), [variable/branch semantics](https://github.com/scummvm/scummvm/blob/v2026.4.0/engines/scumm/script.cpp). **No official descumm comparison or gameplay execution, and no indexed image fidelity testing.** No original game bytes or copyrighted images committed.

## Exhaustive source walks

| Room55 LSCR | Original chunk start | Body bytes consumed | Instructions | Valid branch destinations | Related active animation children |
| ---: | ---: | ---: | ---: | ---: | --- |
| **220** | `0x4998EE` | **339/339** | **54** | **12/12** | 201, object620 and flag163 |
| **221** | `0x499A4A` | **900/900** | **164** | **50/50** | 202/203, objects617/623, flags165/166 |
| **222** | `0x499DD7` | **378/378** | **74** | **7/7** | 204/205, objects627/630, flags167/168 |
| **223** | `0x499F5A` | **509/509** | **103** | **27/27** | 206/207, objects634/636/638, flags169/170 |
| **Total** | | **2,126/2,126** | **395** | **96/96** | Four distinct ambient scene families |

These complete walks include source nested `expression` opcodes, `getRandomNr` calls, `delayVariable`, `isScriptRunning`, `startScript`, `stopScript`, `drawObject`, flag assignments, `breakHere` and branch polarity. The source output remains a structural interpretation, not a measured scene timeline.

## New result: animation children can run *without the corresponding actor speaking*

The [complete Room55 spatial controller LSCR211](MI2_ROOM55_COMPLETE_SPATIAL_SCRIPT211_20261117.md) selects proximity categories0/7/8/9/12 using Ego's distance from eight placed actors and vertical screen position. On category changes, it starts group-dependent scripts214–217 and ensures fallback scripts220–223 are active when their relevant group animation is not.

These **fallback** scripts are **not passive or empty background timers**. Their directly encoded instructions can themselves launch the same animation loops controlled by speaker-specific [LSCR212](MI2_ROOM55_COMPLETE_SPEAKER_CONTROLLER_20261117.md), e.g.:

- **LSCR220** source PC0x02A `startScript(201)`, after a random-selection branch; separately changes Var163, draws object620 in states1/3/4, uses random script-yield counts and `delayVariable`. It tests `isScriptRunning(201)` at its beginning to avoid interfering during an already-active child loop.
- **LSCR221** source PC0x034 `startScript(203)` and PCs **0x198/0x1A8/0x1B8** `startScript(202,[8/4/5])`; it can independently drive object617 states4/6 and object623 states1/3/4, and toggles Vars165/166 as well as introducing random wait/yield phases.
- **LSCR222** source PCs0x034,0x0B7 start **script204**, PCs0x071,0x0F4 start **script205**; it restores and alternates paired object627/630 states, sets Vars167/168 for a bounded group of **15 consecutive `breakHere` opcodes**, then clears them and applies randomized delay.
- **LSCR223** source PC0x034 `startScript(206)`, PC0x07B `startScript(207)`; it drives object634/636 state sequences and guarded redraws of object638 using **Bit210**, toggles Vars169/170, and applies variable delays.

This corrects a potentially misleading earlier interpretation: Room55's local 201/202/203–207 animation loops are **not exclusively invoked by TALK_ACTOR script212**. Source-backed **idle/ambient scripts220–223 can also invoke them**, and the scheduling/stopScript behaviour must be modeled as competing or cooperating parent contexts. The dynamic actor state still needs runtime confirmation.

### Detailed LSCR220 variation example

`LSCR220` repeatedly yields while script201 is already active. Once available, it computes `getRandomNr(3)+1` using a v5 `expression` containing an embedded `getRandomNr` and chooses one of four source-coded outcomes:

1. Start script201, wait a random `delayVariable` interval, clear Var163, reset paired object621/620 state1 and stop script201.
2. Set Var163=1, yield for a sampled interval from `getRandomNr(20)`, clear Var163, then delay a further randomized multiple of 60 script time units.
3. Delay one randomized interval and, depending on machine-speed state, optionally another interval.
4. Explicitly draw object620 state sequence **1→3→1→4→1**, each visible-state choice followed by `breakHere`, then delay a randomized multiple of 60 time units.

Its final branch jumps back to random selection without ending. This makes LSCR220 a **source-encoded randomized idle/gesture scheduler**, even though its actual wall-clock durations and frame visibility are still unknown.

### Important engine semantics

- `getRandomNr(max)` is inclusive of both 0 and max, and its source expression operands are signed/variable depending on opcode mask bits.
- `delayVariable` consumes a script variable and schedules an engine script pause. It does **not** count raw video frames.
- `breakHere` is one yield point; several consecutive yields are not automatically equivalent to the same number of distinct pixels displayed.
- `startScript` nests/evaluates immediately under pinned ScummVM semantics; a subsequent stop or redraw in the same parent path can affect what eventually reaches the renderer.
- The scripts can redraw object states or change flags that LSCR213 continuously synchronizes; do not collapse this to a single flat frame list.

## Cross-reference and classification

Source-complete Room55 controller set now includes:
- [LSCR200 fully aligned room initialization](MI2_ROOM55_COMPLETE_ENTRY_SCRIPT200_20261117.md)
- [LSCR211 spatial/proximity scheduler](MI2_ROOM55_COMPLETE_SPATIAL_SCRIPT211_20261117.md)
- [LSCR212 speaker and distance-specific animation controller](MI2_ROOM55_COMPLETE_SPEAKER_CONTROLLER_20261117.md)
- [LSCR213 continuous seven-pair state synchronizer](MI2_ROOM55_SEVEN_PAIR_SPEECH_SYNC_20261117.md)
- **LSCR220–223 (this report) idle/ambient schedulers**
- [Previously aligned LSCR201/202/203–207/209](MI2_ROOM55_STATIC_EVENT_LOOPS_20261116.md).

The **remaining high-value unwalked local scripts** include 214–219 and 224. These must be evaluated for interaction with ambient loops, actor movement, text and sound before making a complete room simulation claim.

**Verification priority:** staged, mode-documented natural Room55 entry, Ego position in each group, talking actor on/off, which idle scripts are running, 15/20/25/31 proximity thresholds, random choices/delays, object 615/638 when Bit210 changes, native color-index and mask output. Keep separate trace events for source-script facts vs runtime observations.

**Done boundary:** complete static original-bytecode instruction boundaries and source-based control model; **not** pixel-perfect reconstruction or confirmed runtime actor/animation timing.
