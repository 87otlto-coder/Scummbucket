# P0 — Initial SCUMM v5 Research Findings

**Project:** ScummBucket  
**Status:** Preliminary research pass; P0 not yet fully closed  
**Date:** 2026-11-07  
**Scope:** User-supplied archives, SCUMM v5 structural validation, initial background-animation mechanism survey  
**Reference implementation:** [ScummVM](https://github.com/scummvm/scummvm)

> This document is an evidence register, not a claim of a functioning game-asset decoder. No original-game data or extracted graphics are included in this repository.

## 1. Inputs and disposition

| Supplied archive | Bytes | SHA-256 | Assessment |
| --- | ---: | --- | --- |
| `mi2.zip` | 6,951,115 | `fa23ba097c30a66df9fbaf436d0381cd4747220ce7a2b315290dea167535d0cf` | Contains plausible Monkey Island 2 DOS SCUMM v5 resources |
| `mi1.zip` | 11,398,849 | `eb935813942de099cb946cd893d7597c9e3488fa81690e94dcd9050a40d3976e` | **Not Monkey Island 1**; contains `MK1.EXE`, `SAMPLES.DAT`, `.GRA` files, consistent with Mortal Kombat 1 DOS |

Both ZIP archives passed Python `zipfile.testzip()` CRC checks.

**Scope decision:** Only `mi2/MONKEY2.000` and `mi2/MONKEY2.001` were inspected as SCUMM input for this pass. The MI2 ZIP also contains executable, music-driver, ROM, save and MIDI-related files. These are not all SCUMM archive containers and should not be indiscriminately sent through a SCUMM decoder.

**Identification warning:** The ZIP name `mi1.zip` was misleading. The future program must classify inputs using content and supported signatures, not filenames alone. Its rejection must be visible as a diagnostic, not hidden or treated as a corrupted Monkey Island 1 archive.

## 2. Verified Monkey Island 2 source fingerprints

| File in archive | Uncompressed bytes | SHA-256 |
| --- | ---: | --- |
| `mi2/MONKEY2.000` | 11,135 | `cde7aa8980317e3a750fbb3b49884cdddaf1ff3d4231a0c840b22cceed9033f1` |
| `mi2/MONKEY2.001` | 9,080,329 | `ad045372e0d49626503bb50fca29a687ec8e01ef75d9b8bca702a366d143819e` |

Both files yielded valid SCUMM tags after XOR-decoding each byte with `0x69`. The decoded `.000` begins `RNAM`; the decoded `.001` begins `LECF`. This was directly observed on the supplied bytes and is consistent with ScummVM's version-dependent `getEncByte()` logic in [`resource.cpp`](https://github.com/scummvm/scummvm/blob/master/engines/scumm/resource.cpp).

**Important distinction:** This identifies a structurally compatible SCUMM v5-style pair; it does **not yet establish a precise retail edition** through an independently verified detection fingerprint.

## 3. Structural observations — directly tested

### Index file: `MONKEY2.000`

Parsed the entire XOR-decoded file as 4-character ASCII chunk tags followed by a big-endian 32-bit **total chunk size**, including the eight-byte header. All chunk boundaries are within the file and end at byte 11,135, with zero unaccounted trailing bytes.

| Tag | Total chunk bytes | Count read from chunk payload |
| --- | ---: | ---: |
| `RNAM` | 1,109 | Room name mapping; count not yet independently classified |
| `MAXS` | 26 | Maximum-resource metadata; not yet decoded |
| `DROO` | 645 | 127 room directory slots |
| `DSCR` | 1,005 | 199 script slots |
| `DSOU` | 1,280 | 254 sound slots |
| `DCOS` | 1,005 | 199 costume slots |
| `DCHR` | 55 | 9 charset slots |
| `DOBJ` | 6,010 | 1,200 global object entries |

The five-byte-per-entry directory record lengths match `2 + 5 × count` for `DROO`, `DSCR`, `DSOU`, `DCOS` and `DCHR`. These are **table capacities/slots, not confirmed decoded asset counts**. `DOBJ` is a separate object table and should not be assumed to use the same record interpretation.

ScummVM reference: [`ScummEngine::readIndexFile`, `readIndexBlock`, `readResTypeList`](https://github.com/scummvm/scummvm/blob/master/engines/scumm/resource.cpp).

### Resource file: `MONKEY2.001`

- One top-level `LECF` block of **9,080,329 bytes**, exactly filling the file.
- Its children: one `LOFF` block and **110 `LFLF`** room-bundle blocks.
- `LOFF` has **110 distinct room IDs** and **110 distinct byte offsets**.
- All 110 offsets point to `ROOM` tags at **LFLF start + 8**; they do not point to the `LFLF` header.
- All 110 `LFLF` children have valid boundaries; together they cover the file without trailing bytes.
- All 110 nested `ROOM` chunks were recursively walked at one child level without structural boundary failures.

Observed counts within `ROOM` chunks:

| Resource / chunk | Observed total | Qualification |
| --- | ---: | --- |
| `RMHD` | 110 | One per inspected room |
| `RMIM` | 110 | Room image containers; image pixels **not** decoded |
| `CLUT` | 110 | Room palette blocks; RGB colors not yet checked |
| `CYCL` | 110 | Cycle *blocks*, including those with no cycle records |
| `OBIM` | 1,145 | Object-image chunks, not necessarily 1,145 visible objects |
| `OBCD` | 1,145 | Object-code chunks; count matches `OBIM`, object IDs not yet paired |
| `LSCR` | 612 | Room-local script chunks; scripts not decompiled |
| `ENCD`, `EXCD` | 110 each | Room entry/exit script chunks; not executed |

Reference layout: ScummVM's [room code](https://github.com/scummvm/scummvm/blob/master/engines/scumm/room.cpp), [object code](https://github.com/scummvm/scummvm/blob/master/engines/scumm/object.cpp) and secondary [SCUMM v5 resource map](https://grogvm.dev/docs/scumm/resource-file/).

## 4. Animation mechanism survey — evidence and implications

### A. Palette cycling — confirmed **data presence**, behavior not yet verified

- `CYCL` records are present in **21 of 110 rooms**.
- **127 cycle records** were parsed across those rooms; the other 89 `CYCL` blocks terminate with no active records.
- Example rooms with records: **4, 7, 16, 22, 23, 24, 27, 28, 35, 36, 38, 46, 47, 51, 52, 53, 64, 81, 85, 89**, and one further room (inspect programmatically when generating the definitive register).
- Room 24 includes a record with direction-related flag `2`; room 35 includes flag `4`. Their observed effect requires gameplay verification.
- **Room 64 has an unusual second cycle record** (rate field 65,494; flags 55,558). The parser found a structurally bounded record, but it requires a targeted interpretation check; do not silently normalize, discard or call it corrupt.

ScummVM's [`palette.cpp`](https://github.com/scummvm/scummvm/blob/master/engines/scumm/palette.cpp) contains `initCycl()`, `cyclePalette()` and `stopCycle()`, demonstrating runtime palette-state changes and timing logic. This directly supports treating palette effects as animation mechanisms.

**Not established:** A cycle record does not prove a visible, continuously active gameplay animation. State transitions and scripts can affect it.

### B. Object image states — confirmed **data presence**, animation status unverified

- All 1,145 `OBIM` chunks have parseable direct-child boundaries and an `IMHD` header.
- **158 `OBIM` resources contain two or more `IMxx` image-state chunks.**
- Example candidate rooms: 6, 9, 13, 17, 24, 28, 34, 35, 44, 55, 72, 103.
- ScummVM's [`object.cpp`](https://github.com/scummvm/scummvm/blob/master/engines/scumm/object.cpp) has `getObjectImage()` and `getObjectImageCount()`, which look up image states.

**Not established:** Multiple visual states may represent player interaction, scripted animation, or unused alternatives. Do not label these as running animations without script or gameplay evidence.

### C. Costume-driven environmental animation — implementation mechanism supported, usage unverified

ScummVM's [`costume.cpp`](https://github.com/scummvm/scummvm/blob/master/engines/scumm/costume.cpp), [`actor.cpp`](https://github.com/scummvm/scummvm/blob/master/engines/scumm/actor.cpp) and [SCUMM v5 script operations](https://github.com/scummvm/scummvm/blob/master/engines/scumm/script_v5.cpp) provide costume rendering, animation advancement and script-directed animation.

Potential environmental usage must be identified from the actual game scripts and verified against playback. This is **not** yet evidence that a particular room uses animated costume scenery.

### D. Layers, masks and scrolling — implementation mechanisms supported

ScummVM's [`gfx.cpp`](https://github.com/scummvm/scummvm/blob/master/engines/scumm/gfx.cpp) uses room image drawing, graphics-strip operations, masking and a virtual screen. Scene reconstruction must preserve layering and mask relationships, not only individual images.

### E. Script-controlled scene behavior — likely essential

Room-level `ENCD`, `EXCD` and `LSCR` resources are present, and global `SCRP` resources are stored in room bundles. These make script-to-resource relationships a high-priority P1/P4 investigative target. Full interpreter emulation is not an initial requirement.

## 5. Evidence and uncertainty register

| ID | Claim or question | State | Needed next |
| --- | --- | --- | --- |
| E01 | Supplied `MONKEY2.000/.001` decode with XOR `0x69` and valid outer structures | **Observed** | Reproduce using versioned CLI parser |
| E02 | Complete `LECF` room layout has 110 `LFLF` blocks and valid LOFF targets | **Observed** | Cross-check index-directory resource lookups |
| E03 | `mi1.zip` is not Monkey Island 1 | **Observed** | Add unsupported/mislabeled archive test case |
| E04 | 21 rooms contain palette-cycle records | **Observed** | Confirm per-room cycle interpretation and visible results |
| E05 | 158 object images have multiple `IMxx` state chunks | **Observed** | Pair image states with object IDs and scripts |
| U01 | Exact release identity of this MI2 edition | **Unverified** | Cross-reference known game fingerprints and detection logic |
| U02 | Actual timing and onscreen appearance of each cycle | **Unverified** | Compare against ScummVM gameplay/capture |
| U03 | Which multistate objects form automatic scenery animations | **Unverified** | Script investigation and observed gameplay |
| U04 | Room 64 cycle record semantics | **Anomaly / unresolved** | Inspect raw fields against ScummVM parser and original behavior |
| U05 | Character costume decode and asset-level export | **Not started** | P3 |
| U06 | Static background pixel correctness | **Not started** | P2 |

## 6. Initial reference scene candidates

| Room | Why it is useful | Acceptance still required |
| --- | --- | --- |
| 1 | Baseline room with no recorded palette-cycle entries | Decode base image/palette |
| 4 | Six palette-cycle records | Verify palette cycling against playback |
| 24 | Eight cycle records, including flag 2 | Test cycle direction |
| 35 | Two cycle records with flag 4 | Research flag semantics |
| 51 | Twelve cycle records | Stress timing and simultaneous cycles |
| 64 | Unusual cycle field data | Diagnose without silent normalization |
| 34 | Multistate `OBIM` example with 16 image-state tags | Determine whether states are animated, scripted or static alternatives |

Room numbers refer to the supplied sample's `LOFF` order and must not be assumed universal across editions.

## 7. Proposed first development boundary

**Next: P1 archive reader and inventory**, following the acceptance plan in [`P0_ACCEPTANCE_AND_TEST_PLAN.md`](P0_ACCEPTANCE_AND_TEST_PLAN.md).

The first implementation should:

1. Detect and verify a supported `.000/.001` pair, with structured diagnostics.
2. Decode the relevant byte layer safely and validate nested chunk lengths.
3. Inventory rooms, resource slots, source offsets, tags, and candidate animation links without decoding pixels.
4. Preserve provenance and report counts of successes, failures, skips and unsupported items.
5. Be testable on synthetic fixtures and the private MI2 sample.
6. Never package, redistribute or commit copyrighted game bytes.

## 8. Research references

Primary source files from [ScummVM](https://github.com/scummvm/scummvm):

- [`engines/scumm/detection_tables.h`](https://github.com/scummvm/scummvm/blob/master/engines/scumm/detection_tables.h) — game / SCUMM version mapping.
- [`engines/scumm/resource.cpp`](https://github.com/scummvm/scummvm/blob/master/engines/scumm/resource.cpp) — index and directory interpretation, decoding byte selection.
- [`engines/scumm/resource_v4.cpp`](https://github.com/scummvm/scummvm/blob/master/engines/scumm/resource_v4.cpp) — earlier directory layout (relevant to Monkey Island 1 VGA).
- [`engines/scumm/room.cpp`](https://github.com/scummvm/scummvm/blob/master/engines/scumm/room.cpp) — room initialization and scripts.
- [`engines/scumm/object.cpp`](https://github.com/scummvm/scummvm/blob/master/engines/scumm/object.cpp) — image states.
- [`engines/scumm/palette.cpp`](https://github.com/scummvm/scummvm/blob/master/engines/scumm/palette.cpp) — color cycling.
- [`engines/scumm/gfx.cpp`](https://github.com/scummvm/scummvm/blob/master/engines/scumm/gfx.cpp) — room rendering and mask handling.
- [`engines/scumm/costume.cpp`](https://github.com/scummvm/scummvm/blob/master/engines/scumm/costume.cpp) — costumes and animation.
- [`engines/scumm/script_v5.cpp`](https://github.com/scummvm/scummvm/blob/master/engines/scumm/script_v5.cpp) — script opcodes relevant to state control.

Secondary cross-check: [GrogVM's SCUMM v5 resource documentation](https://grogvm.dev/docs/scumm/resource-file/) (not a substitute for local verification).

## 9. Pass conclusion

The available original MI2 archive and ScummVM references provide sufficient **initial format evidence** to begin a bounded P1 parser, but P0 remains provisional until exact edition classification, reproducible checks and acceptance decisions are recorded.

**Tests performed:** ZIP CRC; source SHA-256; XOR header inspection; full index chunk walk; full resource `LECF/LFLF` walk; `LOFF` target checks; first-level `ROOM` chunk walk; `CYCL` record walk; first-level `OBIM` subchunk walk.

**Not performed:** Implemented extraction CLI, ScummVM runtime comparison, static image decode, animation playback, audio decode, cross-edition compatibility, or regression automation.
