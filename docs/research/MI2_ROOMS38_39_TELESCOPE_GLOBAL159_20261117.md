# MI2 Rooms 38/39 — telescope/statue cross-room scripted visual sequence (17 November 2026)

**Evidence class:** read-only original DOS VGA `MONKEY2.001` (SHA-256 `ad045372e0d49626503bb50fca29a687ec8e01ef75d9b8bca702a366d143819e`) + `MONKEY2.000/DSCR` indexed global script identity; independent narrow static v5 opcode walker, checked against pinned [ScummVM v2026.4.0 script_v5.cpp](https://github.com/scummvm/scummvm/blob/v2026.4.0/engines/scumm/script_v5.cpp), [script.cpp](https://github.com/scummvm/scummvm/blob/v2026.4.0/engines/scumm/script.cpp). **No gameplay execution, no standalone descumm cross-comparison, no original-interpreter instrumentation or indexed framebuffer verification.** All original game bytes stay private, unchanged and outside Git.

## New result: global script 159 really coordinates two room resource families

Indexed **DSCR[159]** belongs to room38's LFLF *storage* bundle; tagged `SCRP` chunk starts at XOR-decoded source offset **`0x2DA317`**, script body **`0x2DA31F`**, body length **721 bytes**. Independent narrow instruction walk consumed **721/721 bytes**, **192 instructions**, with **43 relative branch targets all aligned to instruction starts or script end**. This is more robust than the 15 *unaligned* object-pattern matches in the older [global script survey](MI2_GLOBAL_SCRIPT_PATTERN_SURVEY_20261116.md).

**Critically, the global script has source-aligned `loadRoom` opcodes**:

| Script PC | V5 opcode bytes | Source-decoded action | Condition / purpose |
| ---: | --- | --- | --- |
| `0x00A5` | `72 27` | `loadRoom(39)` | branch reached when object386 “shutters” state equals 1 |
| `0x01C6` | `72 26` | `loadRoom(38)` | return path after the Room39 segment, including `delay(90)` |
| `0x0201` | `72 26` | `loadRoom(38)` | cleanup path if `Var[4]` (current room) is not 38 |

Here `0x27` and `0x26` are decimal **39** and **38**. No speculative source/runtime room identifier conversion was used. Object IDs drawn in these two phases belong to the corresponding two rooms' original paired OBCD/OBIM inventory.

### Source-aligned interactive call chain: telescope + statue

Room38 includes **two separate OBCD objects with original name “grotesque statue”**, IDs **372** and **385**, both logical (no stored OBIM images). Each object's VERB entry for verb **7** is an **identical, fully aligned 34-byte handler**, eight instructions with all four branch targets valid:

| Statue object | Verb7 handler offset | Trigger |
| --- | ---: | --- |
| 372 | `0x2D9C22` | if `Local[0] == 696`, start global script159 |
| 385 | `0x2D9CDA` | same logic, same opcode sequence |

**Original object ID696 is named “telescope”** (paired OBCD stored with Room61, not in Room38). Each statue's handler first requires `Local[0] != 0`, then `Local[0] == 696`; for all other values it instead starts global script3 with literal argument `7`. This is a grounded **telescope-on-statue script activation route**, conditional on the original game dispatching the verb handler with the target object ID as local argument. User interaction and natural gameplay execution are **not observed**.

## Event/timing/control-flow outline for global script 159

| PC range | Original source semantics | Animated content |
| --- | --- | --- |
| `0x0000–0x001C` | begin cutscene; if `Var[251]==0`, set it to **`getRandomNr(4)+392`**, inclusive **392..396**; register cutscene override exit at PC `0x01F0` | **Five possible variation IDs**; selected value persists until some other script resets Var251 |
| `0x001C–0x0054` | Ego actor action250, costume139, action6, sound2, action8; object383 state1 and 384 state1, plus explicit `breakHere` yields | Initial Room38 movement and scene setup |
| `0x0054–0x0099` | read object379 state 0..3; draw object381 state **4/1/2/3** respectively; yield and `delay(60)` | Object state-based four-way Room38 visual |
| `0x0099–0x00AA` | check object386 state (named “shutters”); if 1, `loadRoom(39)` and setCameraAt(250) | **Conditional** transition into Room39 |
| `0x00AA–0x00E3` | `delay(60)`; draw object419; object387 “door” state selects object420 state1/2; draw object421; check object389 “mirror frame” state | Room39 scenery and interactive state |
| `0x00E3–0x01BA` | if mirror frame state1, panCameraTo(160), then select one of five branches by **Var251 = 392…396** | Draw 3 corresponding states of **three Room39 objects 416,417,418**, each storing 5 IM states, with one `breakHere` between each object's draw, `wait(camera)`, then set exactly one of objects411–415 to state1; also set Bit755=1 |
| `0x01BE–0x01C8` | alternate mirror branch sets object410; `delay(90)`; `loadRoom(38)` | Return to original room |
| `0x01CB–0x01F0` | set Room38 object382 state1; delay60; hide previous 381/383/384; Ego action7, sound3, object380 state1, delay60 | Room38 post-effect |
| `0x01F0–0x029B` | conditional cleanup and cutscene-skip state reconciliation, possibly re-enter Room38, then use selected Var251 to set puzzle/overlay object state | Essential **skip path** and state preservation; do not terminate early when skipping |
| `0x029B–0x02D1` | end override, hide Room39 helper objects416–421, restore Ego costume1 and actions, delay20, hide object380, end cutscene and stop | Cross-room cleanup |

**Individual original resource examples:**
- Room38: object379 has **3** stored images; object381 **4**; object380/382/383/384 have one each.
- Room39: objects416,417,418 each have **5** stored images; objects411–415 each one; object420 two; 419/421 one. Objects386 (“shutters”), 387 (“door”), 389 (“mirror frame”) are named source objects whose states control branches.
- On the *normal* case where shutters aren't in state1, the script **skips the Room39 transition and its object-image trio**. The five-way visual is therefore additionally conditioned on both the shutters and mirror frame source state. Do not present it as an unconditional 5-frame looping background animation.
- The random result uses ScummVM's inclusive `getRandomNr(4)`; conditional `Var251==0` initialization prevents re-rolling on every invocation, subject to other script writers.

### Very important evidence distinctions

The **script file's storage room is not its sole runtime rendering room**. A P4 inventory that attaches all `SCRP` resource draw calls to the room containing that `SCRP` will be wrong. This example has:
- a *global script resource* loaded from Room38;
- a *logical object interaction* involving a telescope owned/stored with another room;
- live image draws from at least **Room38 and Room39**;
- a conditional game-state branch that decides whether to move to Room39 at all;
- actor costume/animation, sound, camera and timer changes;
- a five-way *cached random* variation and cutscene skip cleanup.

This is a distinct architectural class from Room35/36's in-room gradual palette fades and from Room55's local randomized object loops. P4 must model **global script identity separately from current room and asset ownership**, and retain source PC, scope, active room, draw layer, current palette, actor costume and event phase.

## Follow-up source linkage: five brick IDs and a difficulty-dependent outcome

A further complete source-aligned narrow walk of **Room39 LSCR203** (145/145 bytes, 34 instructions, 17/17 valid branches) demonstrates that **Var251 values 392..396 are logical brick object IDs** (each original `OBNA` = “brick”). Its Easy-mode path copies the chosen brick ID into `Local[0]` and sets Bit755; the Regular-mode path branches on the supplied brick ID, then later requires both an exact match `Local[0] == Var251` and `Bit755` before starting a distinct follow-up global script44 rather than script43.

See [Room39 brick selection and difficulty bypass](MI2_ROOM39_BRICK_DIFFICULTY_REVEAL_20261117.md). This is a genuine puzzle-state dependency: **a different image state can encode the answer to an interaction**, not just visual variety. No claim is made that either outcome has been observed in natural play.

## Suggested next validation

1. Compare independent `descumm -5 -o` on the exact tagged `SCRP[159]` and both 34-byte statue VERB handlers against the source-aligned narrow walk. Branch target map **43/43** is corroboration of alignment but not an independent tool result.
2. Under pinned instrumented ScummVM, stage telescope-on-statue interaction in Room38 with source state Var251 zero and nonzero, object386/389 alternate states, and capture whether/how `loadRoom(39)` executes.
3. Log **Var251, Bit755**, Room IDs, source object state, object image state, camera, sound, actor costume, relative script PC, wait/yield/delay, indexed framebuffer per update and exact edited bit/variable events.
4. Capture cutscene skip separately to verify the cleanup path still marks the intended object and returns to Room38, avoiding a false animation-only export.
5. Retain all raw original resources and any capture files under `FIXTURE` (no repository game content), tool binaries under `TOOLS`, and eventual decoder/test implementation under `SOURCE\ScummBucket`.

**Done threshold unchanged:** full source alignment is **static evidence**, not observed runtime branch reachability, correct rendering, or original-DOS fidelity.
