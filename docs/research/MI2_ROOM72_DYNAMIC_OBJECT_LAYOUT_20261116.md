# MI2 Room 72 — source-backed dynamic object placement and class controls (2026-11-16)

**Status:** independent, narrow static instruction decode of one original DOS VGA local script. Not gameplay-observed, not complete descumm validation, no engine execution, and no copyright game bytes/artwork in Git.

Source: fingerprinted original MONKEY2.001 `ad045372e0d49626503bb50fca29a687ec8e01ef75d9b8bca702a366d143819e`. Room 72 is **320×144**, has 18 paired objects with 36 image states, and LSCR 200 at decoded file offset **6,208,325**.

## The important finding

A narrow opcode walker using ScummVM v5 `script_v5.cpp`, `script.cpp`, and v5 `CodeHeader` semantics consumed the **entire 487-byte body** of **LSCR 200 (487/487)**: **74 aligned instructions, zero invalid jump targets**. This goes substantially beyond the previous unaligned 22 direct-object byte-pattern candidates.

The script first resets all 18 object states to 0, then changes object class flags, selects four image states from variables, and dynamically positions variable-selected objects using **indirect array variables**. This is **script-controlled object placement/layout**, not merely state switching or the presence of static images.

In SCUMM v5, a variable operand with the `0x2000` flag consumes an **additional two-byte array-index operand**. ScummVM `readVar` resolves that index; in this original script, `0x2169` corresponds to base Var[361] with an extra index word. A naïve `object ID immediately after opcode` scanner entirely misses these dynamic object draw calls, and a parser that assumes fixed-length operands loses synchronization.

## Instruction-aligned event graph

### Stage A: reset/classification

- Body offsets `0x0000..0x0048`: eighteen consecutive `setState(obj,0)` instructions for IDs 731–748 (observed order 731–734,741–748,735–740).
- `0x0048..0x0080`: eight `setClass(741..748,160)` opcodes. In v5 `setClass` uses bit 7 to choose setting/clearing a class: encoded 160 = set class 32, **not** a distinct class ID 160.
- `0x0080..0x0098`: `drawObject` state selection for objects 731–734 using source variables **356,357,358,359**.

### Stage B: layout group controlled by Var[360]

All coordinates below are raw script `draw at` arguments measured in **8-pixel units** in ScummVM v5 `o5_drawObject`. Script body positions are canonical 0-based, not absolute file offsets.

| Var[360] | Number of dynamic draws | Object expression | Raw positions (x,y) | Native pixel positions |
| ---: | ---: | --- | --- | --- |
| 1 | 1 | Var[361+0] | (19,1) | (152,8) |
| 2 | 2 | Var[361+0..1] | (14,1),(26,1) | (112,8),(208,8) |
| 3 | 3 | Var[361+0..2] | (14,1),(19,1),(26,1) | (112,8),(152,8),(208,8) |
| 4 | 4 | Var[361+0..3] | (10,1),(17,1),(23,1),(29,1) | (80,8),(136,8),(184,8),(232,8) |

Conditional tests at `0x0098`, `0x00AC`, `0x00CA`, `0x00F2`. All paths continue to `0x0124` before the next group (branch fallthrough semantics confirmed from ScummVM `jumpRelative`).

### Stage C: layout group controlled by Var[366]

| Var[366] | Dynamic draws | Object expression | Raw positions | Native pixels |
| ---: | ---: | --- | --- | --- |
| 1 | 1 | Var[367+0] | (18,5) | (144,40) |
| 2 | 2 | Var[367+0..1] | (15,5),(22,5) | (120,40),(176,40) |

### Stage D: layout and class group controlled by Var[370]

| Var[370] | Dynamic draws | Object expression | Raw positions | Native pixels |
| ---: | ---: | --- | --- | --- |
| 1 | 1 | Var[371+1] | (17,4) | (136,32) |
| 2 | 2 | Var[371+1..2] | (11,4),(23,4) | (88,32),(184,32) |
| 3 | 3 | Var[371+1..3] | (10,4),(17,4),(24,4) | (80,32),(136,32),(192,32) |

For each dynamically placed object in this last group, script also invokes `setClass(obj,32)`, which **clears** class 32 according to ScummVM source semantics (argument lacks bit 7). This may affect scene interaction availability, but runtime consequences are not yet observed.

The script terminates at body `0x01E6`; there are **no `breakHere` script yields in the entire 487-byte decoded body**. Thus these instructions are structurally eligible to run within one interpreter script slice, conditional on caller/engine scheduling. Whether the actual displayed screen changes in one update or several is still unverified.

## Source-image context (private, not published)

A private source-native decode shows Room 72's empty background as a warm orange stage-like recess; its 18 objects resemble carved decorative segments, columns and pictorial panels, including two-state vertical ornaments. Visual identity is **preliminary decoded imagery**, not an independently confirmed gameplay scene. Avoid claiming a puzzle identity or animation duration without corroboration.

## Why this matters

- A future ScummBucket P4 runtime-neutral scene description must support **parameterized object placement from variable-indexed arrays**, not only fixed object IDs/state numbers.
- Native layout is affected by script control state **and** object class changes.
- A fixed-room `OBIM` position inventory is an initialization baseline, not a guarantee objects stay there.
- Raw `script_candidates.py` scanning for literal object IDs will **systematically miss** these `0x85` drawObject instructions with indirect variable addressing.
- Rendering can require the compositor to honor `drawObject`'s same-coordinate replacement logic and altered interactive object state; do not simply pile new sprites onto an otherwise static panorama.
- This room is an excellent complementary future test: Room 55 randomized state changes with yields; Room 72 conditional layout without yields.

## Remaining missing evidence

1. Independently run descumm and validate this exact 74-instruction interpretation.
2. Trace writes/initialization and caller values of arrays Var[361], Var[367], Var[371] and count variables Var[360], Var[366], Var[370]; the script references them but does **not** establish which concrete object IDs are stored.
3. Verify object state, placement, class and native rendering with original SCUMM/ScummVM captures. No tests were run.
4. Preserve original CDHD object origins and separate scripted object X/Y, classes and selected state in the event manifest, with provenance and unknown runtime branch values.

Pinned source references:
- https://github.com/scummvm/scummvm/blob/v2026.4.0/engines/scumm/script.cpp (`ScummEngine::readVar`, indirect `0x2000` array addressing)
- https://github.com/scummvm/scummvm/blob/v2026.4.0/engines/scumm/script_v5.cpp (`o5_drawObject`, `o5_setClass`, `o5_setState`, `jumpRelative`)
- https://github.com/scummvm/scummvm/blob/v2026.4.0/engines/scumm/object.h (v5 `CodeHeader`)
