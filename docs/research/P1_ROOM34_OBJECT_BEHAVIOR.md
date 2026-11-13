# P1 — Room 34: Script-Controlled Object-State Behavior

**Project:** ScummBucket  
**Status:** Source-supported script-logic analysis; **not observed gameplay or completed animation reconstruction**  
**Date:** 2026-11-08  
**Game scope:** Fingerprinted original DOS Monkey Island 2 sample  
**Classification:** Interactive/script-directed object-state sequence, not demonstrated autonomous background animation

This analysis follows the [object 358 provenance and opcode register](P1_OBJECT_358_SCRIPT_SURVEY.md). It is based on the two `descumm -5 -o -h` reports supplied by the user, independently checked for their contents and origin. The game bytes, raw script chunks, and text disassemblies are **not** included in GitHub.

## 1. Source and evidence provenance

| Artifact | Identity / evidence |
| --- | --- |
| Game resource file | `MONKEY2.001` SHA-256 `ad045372e0d49626503bb50fca29a687ec8e01ef75d9b8bca702a366d143819e` |
| LSCR 201 source chunk | file offset 2,740,982; 5,050 bytes; SHA-256 `3dd3377827386229962e9aae8d681426115ad228efe1ecf36d7469154d1fbc09` |
| LSCR 202 source chunk | file offset 2,746,032; 1,107 bytes; SHA-256 `1bb2578f20c0aad5146995f7d40b5cfdd0fe6b5c25a65faaffeddb5f12c82ee9` |
| User-supplied report 201 | `script-201-20261108-000910.txt`; UTF-16LE; SHA-256 `dcb0a892ee9206418ff35699e9e2a77c6ff4aa7cdeeb59a0b668c077f8dac876` |
| User-supplied report 202 | `script-202-20261108-000910.txt`; UTF-16LE; SHA-256 `addf2480f01240e92ed38937e8ef1eaf177eb18e4f7d7dbc3fe27a3b2ac19aeb` |
| External instruction-boundary verification | 11/11 starts in LSCR 201 and 6/6 starts in LSCR 202 matched `descumm`; user supplied successful Windows command output |
| Object 358 | `OBIM` plus `OBCD` linked by actual ID 358; `IMHD` declares 16 stored image-state chunks |

The reports contain game-derived dialogue and script content; store only this derived analysis, checksums, instruction offsets and structured observations in version control.

**Evidence levels:**
- **Direct archive observation:** room/object identifiers, image-state and chunk counts, source offsets, hashes.
- **Independently disassembled instructions:** control flow and operands emitted by `descumm`; the object 358 opcode starts were cross-checked by the adapter.
- **Engine-semantic cross-check:** `getRandomNr(max)` invokes ScummVM's inclusive `RandomSource::getRandomNumber(max)`. See [`script_v5.cpp`](https://github.com/scummvm/scummvm/blob/master/engines/scumm/script_v5.cpp) (`o5_getRandomNr`) and [`common/random.cpp`](https://github.com/scummvm/scummvm/blob/master/common/random.cpp).
- **Not established:** actual runtime branch execution, appearance of each image, measured frame durations, recorded in-game playback.

## 2. What object 358 represents

The two scripts show a **Gamblers' Club password/number demonstration interaction**, with dialogue asking the player to identify numbers. The scripts select object 358's image state, change it during the demonstration, and reset it in response to dialogue or cutscene outcomes.

**Supported classification:** **interactive script-directed state changes** of room graphics; a valuable P4 scene-reconstruction case, but **not evidence of an automatically looping background animation**.

It would be inaccurate to export object 358's 16 images as a uniformly timed 16-frame looping animation and claim that reproduces the game's behavior.

## 3. Reconstructed selection expression (script-supported)

Both `LSCR 201` and `LSCR 202` implement this sequence before a variable-driven `drawObject(358, Var[100])`:

1. Generate `Var[100] = getRandomNr(2)`. ScummVM confirms this produces **0, 1 or 2**, inclusive.
2. Compute `Var[483] = (Var[number] * 3) - 1`, where `Var[number]` is **`Var[339]`** or **`Var[340]`**, depending on which number is currently being demonstrated.
3. Add the offset: `Var[100] += Var[483]`.
4. If `Var[100] == 16`, replace it with **15**.
5. Call `drawObject(358, state = Var[100])`.

For the script-observed number range `n = 1..5`, the resulting expression can be expressed as:

`state = min(15, (3 * n - 1) + r)`, where `r ∈ {0,1,2}`.

| Selected number `n` | Random branch `r=0` | `r=1` | `r=2` | Notes |
| ---: | ---: | ---: | ---: | --- |
| 1 | 2 | 3 | 4 | First three possible image states |
| 2 | 5 | 6 | 7 | Second group |
| 3 | 8 | 9 | 10 | Third group |
| 4 | 11 | 12 | 13 | Fourth group |
| 5 | 14 | 15 | 15 | `16` is clamped to `15` |

The scripts use **state 1** for certain setup/transition displays and **`setState(358,0)`** after specified transitions. The **visual meanings** of state 0, state 1, and the number groups need P2/P4 image decoding; a state value of 0 must not automatically be labeled "hidden" without rendering validation.

The `IMHD` resource declares **16 stored images**. These two scripts explicitly select states **1–15** as above; this does **not** prove that image 16 is globally unused, since other scripts or object defaults have not all been traced.

**Important variable warning:** `Var[100]` is reused widely in LSCR 201 for unrelated dialogue-menu verb construction and random waits. It is **not** a dedicated, persistent animation variable. Only the instruction sequences immediately feeding `drawObject(358, Var[100])` establish its **temporary** role as an image-state selector.

## 4. LSCR 201 — Player dialogue / password interaction

This script controls a dialogue exchange, tracks several game and interaction variables, and conditionally displays object 358.

| Relative opcode offsets | Structural sequence | What is / isn't established |
| --- | --- | --- |
| `06EE`, `06F4` | Draw state **1**; then `breakHere()` | A script yield follows the first state change |
| `06F5–073D` | Shuffle numeric variables and compute `Var[100]` using `Var[339]`; then draw that state | First random number image selection |
| `07FB–0821` | `WaitForMessage()`; compute state from `Var[340]`; then draw | Second selection gated by message completion |
| `0D59–0D7B` | State **1**, `breakHere()`, then `setState(358,0)` | Branch-dependent transition/reset |
| `0DB5–0DBC` | State **1**, `breakHere()`, then state **0** | Different branch-dependent reset |
| `1046–104D` | State **1**, `breakHere()`, then state **0** | Additional dialogue branch |
| `1271–1278` | State **1**, `breakHere()`, then state **0** | Another dialogue branch |

Conditions include `Var[175]` (selected dialogue response), `Var[339]` / `Var[340]` (demonstrated numbers), `Var[342]` (successful attempts), and flags associated with gameplay progression. The caller that initially triggers this local script is **not yet traced**.

Other `getRandomNr` operations in the script serve dialogue options and numerical choices and must not all be conflated with object-frame selection.

## 5. LSCR 202 — Cutscene demonstration

The second script stages a related demonstration using actors, room placement and a password exchange.

| Relative opcode offsets | Structural sequence | What is / isn't established |
| --- | --- | --- |
| `013A–0173` | Generate distinct numbers in `Var[339]`, `Var[340]`, `Var[341]`; draw state **1** | Setup of a number demonstration, not automatic sprite cycling |
| `0179–019E` | `breakHere()`; compute state from `Var[339]`; draw selected image | A yielded script step precedes first number image |
| `025C–0282` | Wait for a message, then compute state from `Var[340]`; draw next image | Message-gated second number image |
| `02FF–031D` | Wait for a message, `delay(30)`, state **1**, dialogue, yield, then state **0** | Both script delay and dialogue timing matter |
| `0428–042C` | On an override branch, set object **357** to 0 and object **358** to 0 | Explicit paired cleanup on a conditional path |

There are additional actor/costume animation and walking instructions in LSCR 202, including `animateCostume` and `WaitForActor`. These are **separate mechanisms** from object 358's image-state changes. Whether the room's actual visible background is independently animated remains unverified.

## 6. Time, triggers and playback fidelity

**Directly decoded timing/control constructs:**
- `breakHere()`: yields to the SCUMM script scheduler; it is **not enough** to derive a wall-clock frame duration from this report alone.
- `delay(30)`, `delay(120)` and other delays occur on particular paths. Treat the numbers as **engine script timing values** until their unit conversion and game speed are verified.
- `WaitForMessage()`: progression depends on a message finishing, not necessarily on a fixed number of frames.
- Conditionals, jumps, choice responses, and cutscene override logic determine which state transitions occur.
- Random selection introduces variation in image state and numbers, so a single fixed state order would not be faithful.

**Not observed:** actual on-screen image appearance, visual effects or masks, exact elapsed milliseconds between changes, visibility of any state under a room-specific rendering rule, real-game branch reachability, and whether assets elsewhere in the room animate on their own.

**P4 export implication:** A future reconstruction may need a **conditional, parameterized event timeline** (script triggers, image-state decisions, message/actor gates, delays) rather than a fixed FPS animation. Never invent missing timing to produce a superficially plausible GIF.

## 7. Object 357 — adjacent but not yet a shared animation

Object **357** appears as an **actor placement and walking destination** in LSCR 202 (`putActorAtObject`, `walkActorToObject`). Scripts **25** and **26** are also started with **357** as an argument in the local-scene control. The **override branch** in LSCR 202 resets both `setState(357,0)` and `setState(358,0)`.

That is a **confirmed connection through scene script context and cleanup**, not proof that the two objects have synchronized image-state animation, shared graphics, or the same execution schedule. A nearby reference to object 357 is not automatically a second animation.

## 8. Explicit errors and uncertainties

| ID | State | Diagnostic / next verification |
| --- | --- | --- |
| V01 | **Verified** | 17/17 candidate opcode boundaries confirmed by user's real descumm runs |
| V02 | **Verified from disassembly + engine semantics** | Formula and clamp for the four random image selection instructions |
| V03 | **Verified from disassembly** | Dialogue/conditional gates, `breakHere`, `WaitForMessage`, `delay` instructions |
| V04 | **Verified from disassembly** | Object 357 actor-position references and conditional reset alongside 358 |
| U01 | **Open** | Visual identity of each image state and how state 0 behaves in rendering |
| U02 | **Open** | Actual elapsed time, scheduler/frame conversion and game-speed dependencies |
| U03 | **Open** | Real-time trace of executed branches and state changes, including random outcomes |
| U04 | **Open** | All script callers / cross-resource dependencies for scripts 201, 202, 25, 26 |
| U05 | **Open** | Whether other room 34 resources produce autonomous background animation |
| U06 | **Unrelated, still open** | Four archive-wide `CYCLE_FLAGS_UNVERIFIED` warnings; not explained by the successful script analysis |

## 9. Recommended next experiment and acceptance criteria

1. **P1/P4 boundary:** retain these verified object and script references in the inventory and mark them `interaction_driven`, not `autonomous_loop`. This is a **research classification**, not an already implemented engine feature.
2. **P2:** decode object 358's `IM01..IM10` images with correct room palette and masks; establish the actual visual meaning of state values 0, 1, 2–15 and 16.
3. **P4:** trace runtime `drawObject` / `setState` calls for object 358 (object ID, chosen state, script ID, interpreter ticks, branch context). Compare with observed ScummVM playback or captures.
4. Examine script 25/26 and object 357 separately for any relevant costume-driven or environmental animation.
5. Identify a **genuine continuously animated scenery example** from the other P0 candidates; this number puzzle alone does not satisfy P4's background-animation exit criterion.
6. Keep the original `CYCL` flag anomalies visible and unrelated to object 358 until separately understood.

**Boundary of completion:** this document establishes a script-backed **interactive state-selection model** for one object. It does not provide rendered frames, playback, gameplay-verified duration, or comprehensive animated-background coverage.
