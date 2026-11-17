# MI2 Room26 waterfall map — Bit93 navigation-box topology (17 November 2026)

**Evidence:** original DOS VGA `MONKEY2.001` read-only XOR-decoded resource member SHA-256 `ad045372e0d49626503bb50fca29a687ec8e01ef75d9b8bca702a366d143819e`. Relevant short bytecode handlers completely walked by a private narrow v5 decoder; branch destinations validated against instruction starts. Cross-check semantics with pinned [ScummVM v2026.4.0 script_v5.cpp](https://github.com/scummvm/scummvm/blob/v2026.4.0/engines/scumm/script_v5.cpp) (`o5_move`, `o5_isLess`, `o5_notEqualZero`, `o5_equalZero`, `o5_matrixOps`, `o5_startScript`), [boxes.cpp](https://github.com/scummvm/scummvm/blob/v2026.4.0/engines/scumm/boxes.cpp) and [boxes.h](https://github.com/scummvm/scummvm/blob/v2026.4.0/engines/scumm/boxes.h). **Static, not gameplay execution or per-pixel verification.** All game data and research scratch bytes remain private.

## The original map actually stores two alternative walkbox configurations

Room26's original OBCD object-name strings include **Waterfall (ID252)**, **Beach (247)**, **Cottage (248)**, Wharf, Mansion and Dread's ship; the screen is therefore strongly suggested by original names to be a location/navigation map. The room's **BOXD** chunk is at `0x1EC409`, 510 bytes tagged, with initial `u8` number-of-boxes `0x19 = 25`. The room also has a B O X M adjacency matrix. No runtime was used to determine exactly which boxes correspond to which visible location.

Two complete local scripts form a matched pair:

| Script | Body absolute offset | Body length | Complete narrow walk | Meaning |
| --- | ---: | ---: | --- | --- |
| Room26 LSCR201 | `0x1F7655` | 46 bytes | 10 instructions, 2/2 branch destinations aligned | set `Bit93=1`; unhide one group, hide another |
| Room26 LSCR202 | `0x1F768C` | 46 bytes | 10 instructions, 2/2 branches aligned | set `Bit93=0`; reverse groups |
| Room26 LSCR203 | `0x1F76C3` | 10 bytes | 5 instructions | stop scripts204/208/207, chain to global script33 |

**Exact loop ranges, corrected for reversed v5 jump semantics:**

- LSCR201 writes **`Bit93=1`**, sets **walkbox flags 0 on boxes 0–9 (10 boxes)**, then **flags 128 on boxes 10–24 (15 boxes)**.
- LSCR202 writes **`Bit93=0`**, sets **flags 128 on boxes 0–9**, then **flags 0 on boxes 10–24**.
- Source `o5_isLess` passes `jumpRelative(b < a)`, with the jump taken when the condition is false; the loops run while `Local[0] <= 9` and `Local[0] <= 24`, **inclusive**, not exclusive.
- In ScummVM's box flags, `0x80 = kBoxInvisible`; `setBoxFlags` writes that flag for each declared box. Thus the scripts **switch which region of the navigation mesh is hidden**, not just alter drawing opacity. Actual actor routing must still be tested.

## Entry-script caller of the two map configurations

Room26 ENCD (77-byte body at original `0x1F75D6`) contains a bytecode branch `notEqualZero(Bit93)`:
- if **Bit93=1**, source-called `startScript(201)`;
- if **Bit93=0**, source-called `startScript(202)`.

This span is manually operand/branch checked in the entry script but the **ENTIRE 77-byte ENCD has not yet been fully opcode-walked**. The paired scripts themselves are fully aligned as above. Room37 ENCD (independently fully aligned in [crossroom research](MI2_ROOMS35_36_37_CROSSROOM_CYCL_STATE_20261117.md)) unconditionally writes **Bit93=1** on entry. Global script1 startup paths also have raw direct assignment candidates for Bit93=1. These offer plausible state sources for the map entry; only runtime will prove specific natural pathways.

## Interactive object handlers — three fully aligned original verb11 scripts

| Object (OBCD name) | Handler absolute offset | Body length | Full narrow walk | Confirmed source-dependent caller |
| --- | ---: | ---: | ---: | --- |
| 247 “Beach” | `0x1F7439` | 43 | 11 instructions, six valid jumps | depends on Bits93, 525 and 92 |
| 248 “Cottage” | `0x1F73D5` | 43 | 11 instructions, six valid jumps | byte-identical logic to Beach |
| 252 “Waterfall” | `0x1F7535` | 21 | 5 instructions, two valid jumps | depends on Bit93 |

**Beach / Cottage conditional dispatcher:**

- If **Bit93 is set**, `startScript(204, [Var7])`.
- Otherwise, if **Bit525 and Bit92 are both set**, `startScript(207, [Var7])`.
- Otherwise `startScript(205)`.

The `[Var7]` argument is a standard word-vararg entry with the variable-pointer mode bit; document it as the literal global `Var7` until its full game meaning is established. A game-level map click still requires dispatcher/caller evidence.

**Waterfall object dispatcher:**

- If **Bit93 is zero**, `startScript(204, [Var7])`.
- Otherwise, `startScript(208, [Var7])`.

All three handlers use v5 bytecode-encoded conditional jumps and direct local script calls, and their branch targets fall on verified instruction boundaries. The source says nothing here about which object image is on screen in a particular gameplay state.

### Script207/208 link into the map configuration

The short Room26 LSCR207 and 208 each explicitly invoke **LSCR201** or **LSCR202**, respectively, after an actor wait/cutscene prefix. This gives a second source-coded route to changing Bit93 and the walkbox partition from within the same room. The complete 31-byte bodies of LSCR207/208 have **not** yet been independently boundary-verified and their actor movement/room-change side effects are unobserved; do not prematurely claim an exact click-to-room path.

## Architectural impact

This expands the linked cross-room mechanism beyond palette and object states:
- Room36 pump interaction changes Bit92 and drives a 40-pass gradual five-cycle palette speed transition.
- Room35 entry uses Bit92 to select waterfall objects and whether to start an eight-image-state waterfall loop; difficulty Bit567 may force Bit92=1.
- Room37 entry sets Bit92 and Bit93.
- **Room26 location-map scripts use Bit93 to swap two entire walkbox subsets**, and map object interaction dispatch also depends on **Bit92** and **Bit525**.

Therefore a plausible future P4/P6 environment-state model needs not just a local animation timeline but persisted puzzle/mode state, walkbox geometry and visibility, animation speed, cutscene state and transitions. Keep static decoded art, source-code-derived state machine, and observed runtime snapshots as separate evidence categories.

**Validation gate:** Use ScummVM to capture Room26 entry and Waterfall/Beach/Cottage interactions for both Bit93 states, document the resulting box flags for all 25 entries, verify actual script dispatch 204/205/207/208 and actor/room transitions; compare against original DOS when discrepancies arise. No new runtime work was performed here.
