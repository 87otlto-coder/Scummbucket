# MI2: exact 127-cycle phase-period inventory, repeated RGB entries and Room22 object-only swaps

**Date:** 2026-11-18. **Source evidence:** read-only original DOS VGA game resource members `MONKEY2.000` SHA-256 `cde7aa8980317e3a750fbb3b49884cdddaf1ff3d4231a0c840b22cceed9033f1` and `MONKEY2.001` SHA-256 `ad045372e0d49626503bb50fca29a687ec8e01ef75d9b8bca702a366d143819e`, XOR0x69 in memory. Exactly 110 LOFF physical rooms parsed, 21 with CYCL. Compare original tagged CYCL record IDs/rates/flags/start/end to native original per-room 256×RGB CLUT; interpret rotation with pinned [ScummVM v2026.4.0 palette.cpp](https://github.com/scummvm/scummvm/blob/v2026.4.0/engines/scumm/palette.cpp), `initCycl`, `cyclePalette`, `doCyclePalette`. **No live ScummVM, original DOS execution, native pixel-fidelity tests or original source bytes/art committed.**

## Full raw-record census: 127 cycles, 21 rooms, zero empty RGB cycles

All 127 records parse as valid positive-length palette intervals; none has rate 0, and all have at least two **distinct original CLUT RGB values** in their interval. This says only that a cycle **can** alter the RGB palette if active; it does not establish that its source interval intersects actual visible game pixels or that runtime scripts leave it active.

| Cycle interval length | Original records | Number with distinct RGB count less than interval length | Smallest exact cyclic RGB period |
| ---: | ---: | ---: | ---: |
| **2** | **91** | 0 | 2 |
| **3** | **4** | 0 | 3 |
| **4** | **27** | **27** | 4 |
| **8** | **3** | **3** | 8 |
| **16** | **2** | **2** | 16 |
| **Total** | **127** | **32** | — |

All **27 four-color records** have repeated color values: **24** have three distinct RGB values, and **three** have just two RGB values. However **none of all 127 cycles has a strict shorter rotational period than its interval length** when comparing exact source RGB sequences. Repeated entries are arranged nonperiodically, so full-phase history matters even with only two or three unique colors.

### Particularly revealing Room46 four-color patterns

Three original Room46 cycles have **four palette positions but only two unique RGB entries**:

| CYCL | Native palette indexes | Original RGB equality arrangement | RGB-rotation period |
| ---: | --- | --- | ---: |
| 1 | 178–181 | **AAAB** | 4 |
| 2 | 182–185 | **AABA** | 4 |
| 3 | 186–189 | **ABBB** | 4 |

Here A and B are *relative equality labels* within each record, not exported color values. The four rotations produce distinct palette assignments; halving the period because `uniqueRGB=2` would be an error. This is not a source animation-FPS measurement. It matters when translating source palettes to individually exported GIF frames: each cycle has a **phase clock** and **color-equality pattern**, not simply a count of unique RGBs.

Other notable nonperiodic repeated-color examples:
- Room24 CYCL1–8 all have **four entries / three distinct RGB values**, but an exact four-phase rotation.
- Room35's two 16-position waterfall cycles each have **15 distinct RGB values**, but require **all 16 positions** for a complete rotation.
- The three Room46 records above demonstrate that a two-color palette can be a *four-phase effect*, qualitatively different from two-position swaps.

## Raw flags and source-clock inputs

| Raw `flags` value | Records | Notes |
| --- | ---: | --- |
| `0x0000` | **121** | Normal direction flag |
| `0x0002` | **2** | Reversed v5 rotation direction |
| `0x0004` | **3** | Nonstandard bit2 exists in source; pinned ScummVM v5 `cyclePalette` uses `flags & 2` for direction |
| `0xD906` | **1** | Room64 abnormal record; includes bit2 and a very high original rate |

Source CYCL stores a **rate**, not precomputed frame count. Pinned ScummVM `initCycl` computes `delay = 16384 / rate` (integer), resets counter and `cyclePalette` accumulates a value derived from `VAR_TIMER` and `VAR_TIMER_NEXT`, rotating when the counter reaches delay. **Do not label these delays as 60 Hz frames without measuring scheduler/timer phase.** Room64 source rate65494 yields delay0, potentially disabling that cycle in pinned engine even though two distinct source RGB colors exist. This is a critical distinction between source metadata and active runtime appearance.

## Connection to previously established layer coverage

[The earlier complete 21-room image-index survey](MI2_CYCL_BACKGROUND_OBJECT_COVERAGE_20261116.md) found **88** cycles with RMIM-only coverage, **29** with RMIM+OBIM coverage, **3** with OBIM-only coverage, **7** without source RMIM/OBIM usage. A source RGB interval with a meaningful period can still be *invisible* when its indexed pixels aren't on screen or the relevant palette phase never advances.

[Room22 unnamed object-layer discovery](MI2_ROOM22_CAPTAIN_DREAD_OBJECT_ONLY_CYCL_20261118.md) correctly identifies **Captain Dread** as original **object239** and the palette-overlap graphic component as **unnamed object240** and ties the three OBIM-only cycles6–8 to source image state1 pixels (15/24/5 occurrences). All eight Room22 cycles are two-entry pairs with distinct RGBs and separate initial delays.

## Engineering implications

**Source-neutral CYCL manifest fields:** source physical room ID, original CYCL ID, start/end indices, raw rate and raw flags, original RGB tuple fingerprint, exact cyclic RGB period, static RMIM/OBIM/COST coverage status, initial engine-derived delay, runtime active/phase status (unknown unless traced), and phase-controlled output palette hash.

**Avoid these false shortcuts:**
1. Distinct RGB count equals number of animation phases — **false** in 32/127 records.
2. Number of CYCL records equals number of independent visibly animated areas — not justified by source pixel overlap.
3. Every declared CYCL always runs — room scripts can stop cycles, mode gates can disable, rate can yield zero engine delay.
4. RGB index swaps alter the source indexed-pixel bitmap — palettes mutate the **mapping**, not the stored pixel-index values.
5. Pair-wise cycle direction affects the two-color swap appearance — for length2 it does not, but it can matter for longer intervals.

**Remaining proof:** independent real engine RGB palette/phase captures for representative two-/four-/eight-/sixteen-position cycles, one source no-overlap case, Room64 rate/flag anomaly and mixed Room35 object/RMIM waterfall. Keep full original art/captures outside Git.

**Evidence status:** fully enumerated and fingerprinted original archive cycle metadata, verified simple rotational-period mathematics and source engine semantics; no executed-game or displayed-frame verification.
