# MI2 Room55 — COMPLETE local script200 entry initialization and call graph (17 November 2026)

**Evidence class:** exhaustive read-only original DOS VGA MI2 bytecode source walk, not runtime animation. `MONKEY2.001` original stored SHA256 `ad045372e0d49626503bb50fca29a687ec8e01ef75d9b8bca702a366d143819e`. Room55 `LSCR[200]` tagged chunk starts `0x4978F4`; 9-byte tag + LSCR ID header, script body **302 bytes**. Narrow independent v5 decoder consumed **302/302, 62 instructions, four valid relative branch targets, zero unrecognized opcodes**. Covers source-encountered `drawObject`, `setState`, `setClass`, `notEqualZero`, `jumpRelative`, `startScript`, `move`, `matrixOps`, `increment`, `isLess`, `actorOps`, `putActorInRoom`, `putActor`, `isNotEqual`, `stopObjectCode`; encodings checked against [pinned ScummVM v2026.4.0 script_v5.cpp](https://github.com/scummvm/scummvm/blob/v2026.4.0/engines/scumm/script_v5.cpp), [boxes.h](https://github.com/scummvm/scummvm/blob/v2026.4.0/engines/scumm/boxes.h), [vars.cpp](https://github.com/scummvm/scummvm/blob/v2026.4.0/engines/scumm/vars.cpp).

**NOT:** independent official descumm, executed natural entry, frame observation, exact actor costume pixel validation or original-DOS interpreter equivalence. Never commit copyrighted game bytes/captures.

## Fully decoded source sequence

### Phase 1 — 23 object draws

Body PCs **0x000–0x05B** contain **23 consecutive four-byte** bare `drawObject` operations, with IDs **647** then **616–637 inclusive** (22 IDs). Each uses the v5 one-subopcode `0xFF` bare/default draw form, not an `0xFF`-terminated opcode list. These are initialized scene source objects but still require native-layer/occlusion verification.

### Phase 2 — source conditional for animated object615

At PC **0x05C**, `notEqualZero(Bit[210])` (raw variable word `0x80D2`) selects:

| Bit210 value | Exact source behaviour |
| --- | --- |
| **nonzero** | PC0x061 `setState(615,0)`; PC0x065 `setClass(615,160)` (set class32); PC0x06C jumps to 0x08D, bypassing 209 |
| **zero** | PC0x06F `startScript(209)` (two-state, random-dwell loop previously independently decoded); PC0x072 `setClass(615,32)` (clear class32) |

This **settles the previous raw caller candidate at PC0x06F**: it is a correctly aligned source instruction with an exact Bit210 condition. It does **not** prove object615 animates on every real room entry.

### Phase 3 — navigation-box configuration

At PC0x079, initialize `Local0=8`; PC0x07E executes `matrixOps(subop1,setBoxFlags(Local0,128))`, PC0x083 increments Local0 and PC0x086 uses `isLess(Local0,11)` with v5 reversed jump convention. As a result, boxes **8,9,10,11 inclusive** are flagged `0x80 = kBoxInvisible`. No additional boxes are changed by this bounded loop. This scene has source-coded navigation/collision changes in addition to graphics.

### Phase 4 — eight actor initializations, costume/text-color/position

PCs **0x08D–0x0D4** issue eight complete `actorOps` instructions. Each executes subop8 `SO_DEFAULT`, subop1 `SO_COSTUME(0)`, subop20 `SO_IGNORE_BOXES`, and subop12 `SO_TALK_COLOR` using a different source palette index. Then PCs **0x0D5–0x11C** place each actor in Room55 and at specific native coordinate positions through `putActorInRoom` and `putActor`.

| Actor ID | Talk color index | Put actor room | Native X,Y source values |
| ---: | ---: | ---: | --- |
| 7 | 241 | 55 | (98,107) |
| 5 | 237 | 55 | (135,107) |
| 11 | 247 | 55 | (20,135) |
| 8 | 227 | 55 | (51,136) |
| 9 | 235 | 55 | (118,133) |
| 10 | 249 | 55 | (156,132) |
| 12 | 214 | 55 | (228,123) |
| 6 | 227 | 55 | (267,122) |

These are **script-source actor coordinates**, not reconstructed image anchor positions from observed screens. Costume0 here should be interpreted with ScummVM's actor initialization behaviour (some sources may use actor costume0 as a special absence/reset), not assumed to be a rendered costume0 frame.

### Phase 5 — script starts and machine-speed gate

At **PC0x11D** `isNotEqual(Var6,0)` branches to **0x127** if `Var6==0`, skipping the first start:
- **PC0x124:** `startScript(212)` **only when `VAR_MACHINE_SPEED != 0`**
- **PC0x127:** `startScript(213)` unconditionally on this source path
- **PC0x12A:** `startScript(211)` unconditionally
- **PC0x12D:** `stopObjectCode()`.

The room entry `ENCD` previously fully aligned as `startScript(224)`, `startScript(200)`, stop. This now establishes an unbroken, **fully source-aligned** call route `Room55 ENCD → 200 → {212 conditional, 213, 211}`. Each `startScript` may execute nested immediately per pinned ScummVM implementation, so scripts need not wait for separate video frames to begin.

## Source-backed animation architecture

These independently aligned reports can now be linked without speculative instruction boundaries:
- [Room55 LSCR212 complete speaker controller](MI2_ROOM55_COMPLETE_SPEAKER_CONTROLLER_20261117.md): 590/590 bytes, 116 instructions, 56 aligned branch targets; dispatches subanimations based on `Var25=VAR_TALK_ACTOR`, including spatially conditioned actor8 modes; stops/cleans them when speaker changes.
- [Room55 LSCR213 seven-pair synchronizer](MI2_ROOM55_SEVEN_PAIR_SPEECH_SYNC_20261117.md): 415/415 bytes, 77 instructions, 31 aligned branches; polls flags Var163,165–170, sets paired object states 1/2 and sometimes draws obj638 depending on Bit210.
- [Room55 selected local loops](MI2_ROOM55_STATIC_EVENT_LOOPS_20261116.md): 201/202/203–207/209 have earlier complete narrow source walks and distinct randomized state scheduling.

**Remaining unknown:** local script211 still needs full independent decoding. Local224 was found as an entry child but also needs a thorough action/lifecycle interpretation. Other global/nested script activity and actual image pixel fidelity remain unobserved.

### Reproducibility and acceptance

- For actor 8, observe both proximity regimes `getDist(Ego,8)<20` and `>=20`, the selected `startScript(202,[4/5/8])`, its object617 frames, and cleanup.
- For Bit210, observe object615/638 with flag0 and nonzero under actual rendering and object class semantics.
- Capture actor source X/Y, ignoring boxes, talk colors, script entry phase and live costume state. Compare against original indexed front buffer before claiming accurate actor rendering.
- Capture all eight actor IDs with explicit source/edition and room origin. Record scripts224/200/211/212/213 start/end/stop.
- Run pinned official `descumm` over tagged LSCR200/211/212/213 before integrating deterministic source-event parser.

**Status:** comprehensive original archive source-bytecode alignment only, **not** verified gameplay, original interpreter parity or native image reconstruction.
