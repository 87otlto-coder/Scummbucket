# MI2 mixed palette/object animation: Rooms 24, 35, 81 and 51 (2026-11-16)

**Evidence level:** directly parsed original DOS VGA archive resource bytes + a narrowly scoped instruction-boundary static walker cross-checked against pinned ScummVM v2026.4.0 engine semantics. **NO gameplay/runtime execution, NO independent descumm disassembly, NO rendered frame verification, NO source modifications.** Source-derived scheduling is not automatically measured on-screen animation.

Original fingerprinted pair:
- `MONKEY2.000`: SHA-256 `cde7aa8980317e3a750fbb3b49884cdddaf1ff3d4231a0c840b22cceed9033f1`
- `MONKEY2.001`: SHA-256 `ad045372e0d49626503bb50fca29a687ec8e01ef75d9b8bca702a366d143819e`
All offsets below refer to in-memory decoded MONKEY2.001 (XOR 0x69 removed, length and positions unchanged). No game bytes or artwork were added to Git.

## Room 24: source-derived randomly alternating three-state water/foam component

- Native room 320×144. **Eight CYCL** records, both background and overlaid object-image palette index coverage in the source-image census. Object **246** stores **three** `IMxx` image states. Source imagery privately previewed as shoreline / water / ship-foam-like artwork; visual labels unconfirmed by engine rendering.
- `LSCR[200]` chunk starts at decoded offset **1,972,742**, with **36-byte script body** and **7 aligned instructions**. The narrow walker consumes **36/36** and its relative jumps land on decoded boundaries.
- At body `0x0000`: expression selects `getRandomNr(2) + 1` into `localVar[1]`; inclusive random range **1–3**.
- `0x000D`: compares against previously selected localVar[0] and re-rolls on equality (a branch that jumps when equality holds, per ScummVM's reverse-polarity `jumpRelative(cond)`).
- `0x0014`: saves accepted selection to localVar[0].
- `0x0019`: `drawObject(246, selected_state)`.
- `0x001F`: `breakHere()`; `0x0020` branches back to 0x0000.
- Critically, **room ENCD is only four bytecode bytes:** `0A C8 FF 00` at decoded ENCD chunk **1,972,720** (body begins at 1,972,728); instruction semantics `startScript(200, no arguments)`, then terminal `stopObjectCode()`. This is strong **source-coded entry-script caller evidence**, though normal-entry gameplay and continuous execution remain unobserved.

**Classification:** *source-decoded non-repeating random three-state object display + palette-cycle candidates*; script yields once after an accepted state, not known wall-clock frame duration. Exact palette/output not captured.

## Room 35: eight-state sequential waterfall object with two abnormal-flag palette cycles

- Native 320×144. Two CYCL records: color ranges **176–191** (raw rate **3072**, flags `0x0004`) and **160–175** (raw rate **2688**, flags `0x0004`). Both CYCL ranges have source-index overlap in background and object **364**; this object stores **eight** native image states. Preliminary private source preview resembles a waterfall.
- `LSCR[202]` chunk offset **2,827,781**, body **26 bytes**, **7 instructions fully consumed** and all relative jumps target boundaries.
- `0x0000`: `move localVar[0] = 1`.
- `0x0005`: `drawObject(364, localVar[0])`.
- `0x000B`: `breakHere()` (one yield after each selected image).
- `0x000C`: `increment localVar[0]`.
- `0x000F`: compare `localVar[0]` to **8** with signed less-than/reverse jump semantics. If state is <= 8, jump backward to the draw; once greater, advance to next branch.
- `0x0016`: jump backward to reset localVar[0]=1.
- Thus the script has a source-defined periodic image-state order **1→2→3→4→5→6→7→8→1**, assuming it runs uninterrupted. No frame duration or active runtime palette phases observed.
- Room ENCD (chunk offset **2,827,542**) contains byte sequence `0A CA FF` at **body offset 127** (decoded file **2,827,677**) corresponding syntactically to `startScript(202, no args)`. This *candidate caller* has **not** independently been instruction-boundary verified in the longer 152-byte ENCD body; do not promote it to an executed caller before descumm.
- The unusual raw flags `0x0004` remain an **unresolved source-format warning** even though ScummVM v5's inspected palette rotation path only checks `flags & 2` for direction. Do not infer original DOS bit semantics or suppress these warnings.

**Classification:** *source-defined deterministic sequential object-state loop + two palette cycles with anomalous flags*. Excellent follow-up for independently pairing visible waterfall movement and palette shimmering.

## Room 81: three-state random selection with explicit script delay

- Native 320×144. **Seven** CYCL records have source-index overlap in background and object **780**. Object 780 stores **three** image states.
- `LSCR[206]` chunk offset **6,709,270**, **39-byte script body**, **7 aligned instructions** fully consumed and validated relative branch destinations.
- At `0x0000`: `getRandomNr(2) + 1` selects 1–3 inclusive into localVar[1].
- At `0x000D`: re-roll if equal to last selected state; at `0x0014`: remember selection.
- At `0x0019`: `drawObject(780, selected_state)`.
- At `0x001F`: **`o5_delay` with three-byte little-endian argument 18**. This pauses the script and invokes break/yield internally; **18 is an engine script-delay value, NOT established 18 milliseconds or 18 display frames**.
- At `0x0023`: jump to select another state.
- Room ENCD starts with bytes `2A CE FF` (chunk offset **6,707,081**, body start 6,707,089): v5 `o5_startScript(206, no arguments)` (0x2A opcode variant). This is **first-instruction source-coded ENCD caller evidence** subject to the conditions of actual room entry.

**Classification:** *non-repeating random three-state object loop + explicit script pause + seven palette cycles*. Compare its actual delay semantics against Room 24/35 yielding loops, not against a guessed FPS.

## Room 51: one-yield object transitions, not perpetual loops

- **12 CYCL** records, the highest room cycle-record count found in original MI2. Object **589** has **three** stored image states with palette-range source pixels.
- `LSCR[202]` body is **10 bytes**, selecting **object 589 state 2**, yielding once, selecting **state 1**, then terminating.
- `LSCR[203]` body also **10 bytes**, selecting **state 2**, yielding once, selecting **state 3**, then terminating.
- These are **finite conditional transition scripts**, not continuous playback loops; caller identity/conditions and actual display state remain unverified. Treat script control distinctly from palette cycling.

## Deep implication: four independent timeline/control contracts

1. **Room 24:** non-repeating randomized state choice, one `breakHere` per accepted state, source entry script calls local script.
2. **Room 35:** deterministic repeating state **1..8**, one yield per state; palette flags need separate research.
3. **Room 81:** non-repeating randomized state 1..3 with explicit **delay(18)** per accepted state, source entry script calls local script.
4. **Room 51:** one-shot two-state transition per called script, one yield, then script exits.

A tool that merely concatenates `IM01…IMnn` into an evenly timed GIF will misrepresent at least three of these four. A source-backed P4 representation should describe state transitions, random/max boundaries, rejection of repeats, caller linkage, script yields/delays, cycles, unknown global/bit variables, and evidence level. Store active timer/scheduler sampling and observed palette/framebuffer hashes only when actual runtime captures are available.

## Specific future gates (none performed in this research session)

- Rerun with full `descumm`, including ENCD Room 35 to verify caller and opcode alignment. Confirm scripts' subsequent callers and stop conditions.
- In a source-compatible ScummVM run with settings/version documented, enter each room naturally and log script slots, opcode PCs, chosen state, random decisions, timer units and complete post-cycle/backend palette.
- Decode source object and background index pixels with maintained ScummBucket engine; verify transparency and Z-mask behaviour, and compare independently rendered front pixels against engine indexed captures.
- Never use final captured screenshots as object source images. Do not claim original runtime parity or natural entry without a matching capture.

Pinned ScummVM references:
- https://github.com/scummvm/scummvm/blob/v2026.4.0/engines/scumm/script_v5.cpp (`o5_expression`, `o5_drawObject`, `o5_getRandomNr`, `o5_delay`, `o5_breakHere`, `o5_isLess`, `jumpRelative`, `o5_startScript`)
- https://github.com/scummvm/scummvm/blob/v2026.4.0/engines/scumm/palette.cpp (`initCycl`, `cyclePalette`)
- https://github.com/scummvm/scummvm/blob/v2026.4.0/engines/scumm/vars.cpp (v5 global-var identifiers)
