# MI2 — global-script control surface beyond LSCR (2026-11-16)

Read-only structural survey of original DOS VGA resource bytes; no original data committed, no descumm boundary validation and **no executed gameplay**. The standalone scanner matched v5 direct-object `drawObject`/`setState` byte patterns in each room's bundled **indexed global `SCRP` resource** against IDs in that room's `OBIM/OBCD` pairs. Source SHA-256 MONKEY2.001: `ad045372e0d49626503bb50fca29a687ec8e01ef75d9b8bca702a366d143819e`.

**Boundary:** The scanner is deliberately unaligned (byte patterns, not decoded opcode starts), checks only global scripts *stored in the same LFLF bundle as the room*, and requires target literal object IDs. It can both report false positives and miss cross-bundle references or indirect-array object IDs. Counts below are therefore **candidate patterns, not confirmed instructions or executed animation events**.

## Newly quantified inventory

**13 room bundles** contain **86** raw direct-object pattern matches in their bundled `SCRP` chunks for locally paired objects. At least **four** (rooms 27, 86, 103, 108) have *zero* corresponding raw direct-object hits in their own ENCD/EXCD/LSCR bodies, while the global scripts stored alongside them have some. In the current `scene_inventory.py`, global scripts are present as storage links but are not searched for direct-object patterns.

| Room | Local direct-object patterns | Same-bundle global direct-object patterns | Linked global DSCR IDs (for relevant bundle) | Primary target IDs |
| ---: | ---: | ---: | --- | --- |
| **103** | **0** | **18** | 52 | 1116–1133 |
| **108** | **0** | **18** | 128,129,130,131,132,133,134,135,136,142 | 1154–1157 |
| **38** | 4 | **15** | 123,159 | 380–384 |
| 9 | 15 | 7 | 70,71,72 | 72,77,84 |
| 4 | 1 | 6 | multiple, see DSCR inventory | 24,26,28 |
| 87 | 1 | 6 | 92 | 809–811 |
| **27** | **0** | 4 | 48,78,137 | 256,257 |
| 93 | 96 | 4 | 143,144,145,146,152,153,154,156,160,161,164,166 | 872,873 |
| 17 | 8 | 2 | 53 | 180,181 |
| 19 | 3 | 2 | 98,99 | 197,199 |
| **86** | **0** | 2 | 83,139 | 806,808 |
| 39 | 19 | 1 | 43,44,68,73,74 | 388 |
| 54 | 2 | 1 | 38,39,40,41,59,119 | 606 |

The “local pattern” count here includes the room's ENCD/EXCD/LSCR, not external callers or object-specific verb handlers. The “global pattern” count includes only `SCRP` stored in that room bundle, not all scripts in the global `DSCR` table.

### Room 108 (new candidate)

- Native room size **320×200**, uniform purple source background in a private native-size decoder preview. **Four paired objects**: 1154 and 1155 each have **15 stored images** (56×48 each), objects 1156/1157 each have **2 stored images** (24×16 each). Total **34 stored image states**, and no CYCL records.
- 18 unaligned direct-object patterns in global scripts, none in ENCD/EXCD/LSCR. Linked `DSCR` indexes 128–136 and 142 are stored in this bundle.
- Example pattern associations from direct source offsets: `SCRP` 8,855,967 (582 bytes) references variable states of 1154/1155; `SCRP` 8,856,566 (877 bytes) includes references to both 15-state objects and the two smaller objects; `SCRP` 8,857,443 (219 bytes) contains state 1/2 references to 1156/1157; `SCRP` 8,858,988 (61 bytes) contains literal state 15 and variable state references to 1154/1155.
- **Potential research value:** global-script-centered, palette-free multi-state image mechanism. A preview shows iconographic elements, but actual purpose (UI, cutscene, puzzle or normal gameplay) and real state order are NOT established. The small, uniformly colored background and unusually high script count are reasons to classify it separately until a genuine entry/caller is found.

### Room 38

- Native 320×144; **6 CYCL records** and 2 multi-image objects (379:3 states, 381:4 states). One of the known raw `CYCL` flag anomalies is here (flags 0x0004 in one record), which remains a separate diagnostic.
- 15 unaligned global direct-object matches, mostly in **DSCR[159]** (SCRP source offset 2,990,871, 729 bytes), targeting object 381 in states 1–4 and changing object states for 380–384.
- Preliminary indexed source preview shows outdoor coastal scenery, and the relevant object images include long narrow elements. This is a potentially rich **palette cycles + script-controlled object** comparison target. Do not infer observed ongoing animation or call it a fishing-line mechanism without script/runtime evidence.

### Room 103

Global DSCR[52] has all 18 raw draw-state-2 matches in six triple-object groups; private source-state decoder found opaque-black mask images. Details preserved in `MI2_ROOM103_GLOBAL_MASK_STATES_20261116.md`.

## Cross-room caution and architecture

ScummVM's resource directory maps a global script ID to a *storage* room bundle, but scripts can run in other rooms or be called from global logic. **Same-bundle matching is only a useful narrow search heuristic, not an execution graph**. A complete future analysis should index all verified opcode-aligned object IDs and dynamic expressions, then separately trace caller/callee/control flow, resource load, room state, and actual runtime execution.

Prioritize **Room 108 global animation** as a distinct prototype after Room 55's source-aligned state loops, Room 44 composite face and Room 72 indirect placement are understood. Room 38 is an excellent mixed palette/script target once baseline source scene decoding is verified.

Engine source:
- https://github.com/scummvm/scummvm/blob/v2026.4.0/engines/scumm/script_v5.cpp
- https://github.com/scummvm/scummvm/blob/v2026.4.0/engines/scumm/script.cpp
- https://github.com/scummvm/scummvm/blob/v2026.4.0/engines/scumm/object.cpp
