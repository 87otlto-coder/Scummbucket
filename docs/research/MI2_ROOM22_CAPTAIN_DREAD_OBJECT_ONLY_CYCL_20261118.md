# MI2 Room22 — Captain Dread object-only palette cycling with eight independent two-color clocks

**Date:** 2026-11-18. **Evidence:** original MI2 DOS VGA `MONKEY2.000` SHA-256 `cde7aa8980317e3a750fbb3b49884cdddaf1ff3d4231a0c840b22cceed9033f1`; `MONKEY2.001` SHA-256 `ad045372e0d49626503bb50fca29a687ec8e01ef75d9b8bca702a366d143819e`, XOR0x69 decoded read-only. Verified LOFF room22 offset **0x1AF6CF**; Room22 CYCL chunk **0x1AF6E5** size82; CLUT chunk **0x1AF88B** size776. ScummVM [v2026.4.0 palette.cpp](https://github.com/scummvm/scummvm/blob/v2026.4.0/engines/scumm/palette.cpp), `initCycl`, `cyclePalette`, `doCyclePalette`; and source pixel-coverage analysis [CYCL object/background inventory](MI2_CYCL_BACKGROUND_OBJECT_COVERAGE_20261116.md). **No original interpreter execution, ScummVM frame trace, official descumm or native indexed screen pixel parity.** Game bytes/images excluded from Git.

## Source identification: the object-only indices belong to named object240 “Captain Dread”

The original Room22 contains exactly 8 v5 color cycle records, followed by a zero record-ID terminator. Source animation metadata and original CLUT are entirely preserved in the read-only original archive. The original OBCD at **0x1C3671** explicitly names object ID **240** **Captain Dread** in its OBNA resource. This resolves an important ambiguity in the earlier source-pixel coverage note: the three *object-only* cycle ranges overlap **Captain Dread's stored OBIM image state IM01**, not an unidentified shipboard environmental object. (This is the game's original *logical object name*; actual costume/actor rendering and overlay visibility still require a runtime trace.)

The previous complete source-strip research found:
- CYCL6 range 186–187: 15 decoded nontransparent pixels in object240/IM01, absent from source background.
- CYCL7 range 188–189: 24 decoded nontransparent pixels in object240/IM01, absent from source background.
- CYCL8 range 190–191: 5 decoded nontransparent pixels in object240/IM01, absent from source background.

**44 stored object-pixel occurrences across the three disjoint ranges**, although runtime compositing, alpha/occlusion, actual selected image state, and image decode parity remain unverified. Do **not** call these 44 observed on-screen pixels.

## Every original cycle is exactly a two-entry color swap

The source CYCL payload consists of eight v5 `id,skip2,rateBE16,flagsBE16,start,end` entries. All original flags are **0x0000**, all intervals have length **2** and none has an invalid start/end. ScummVM's `initCycl` sets delay **floor(16384 / rawRate)** engine timing units. The current engine's `cyclePalette` accumulates `max(VAR_TIMER,VAR_TIMER_NEXT)`, so these delays are **not directly display frames or FPS**. The first five intervals intersect the source background and three do not.

| CYCL ID | Original BE16 rate | Derived initial delay (engine units) | Original index pair | Source BG overlap | Object240/IM01 source overlap |
| ---: | ---: | ---: | --- | --- | --- |
| 1 | 230 | **71** | 176/177 | Yes | unmeasured in this targeted follow-up |
| 2 | 307 | **53** | 178/179 | Yes | unmeasured |
| 3 | 384 | **42** | 180/181 | Yes | unmeasured |
| 4 | 460 | **35** | 182/183 | Yes | unmeasured |
| 5 | 153 | **107** | 184/185 | Yes | unmeasured |
| **6** | **230** | **71** | **186/187** | **No** | **15** |
| **7** | **307** | **53** | **188/189** | **No** | **24** |
| **8** | **384** | **42** | **190/191** | **No** | **5** |

Read-only CLUT inspection also confirms **all eight RGB pairs have distinct colors**. For the three object-only pairs, original color values are:
- 186 RGB(47,99,151) vs 187 RGB(43,87,131).
- 188 RGB(47,91,135) vs 189 RGB(27,71,115).
- 190 RGB(35,75,123) vs 191 RGB(15,55,103).

Since each interval contains exactly two entries, either cycle direction becomes the same visible **swap**. The different delays make the pairs advance independently rather than one uniform eight-color scroll. An exporter should log each original pair's phase/counter separately.

**Important runtime caveat:** the original CYCL data can initialize timers, but script-controlled `stopCycle`, `setCycleSpeed` and room-change behaviour may modify them. Record existence and initialized delays as archive facts, **not proof each timer remains active in ordinary gameplay**. Also verify whether this logical Captain Dread object is actually drawn in the expected state, separately from any actor COST sprites.

## Why this is a P4 architectural test

A validator checking only Room22's 320-pixel-wide source RMIM can correctly see zero direct CYCL6/7/8 pixel coverage, while visible composited room art may still change when an object layer carrying indices 186–191 is present. This is a **named logical-object-only palette-animation** candidate, and also a distinct clock-composition problem: eight pair phases, five BG-affecting and three potentially overlay-only.

Suggested future Windows acceptance:
1. Log native `_colorCycle[0..7]` flags, delays, counters and the actual palette RGB six upper pairs on natural Room22 entry, with game/engine hashes and script slots.
2. Capture object240 state, visibility, draw/undraw operations, associated COST actors, occlusion and native indexed pixels. Check the **15/24/5** original stored counts against the actual composited indexed image.
3. Independently compare exact per-cycle RGB changes on the first five background-related pairs and last three object-related pairs. Only then mark its visible animation as observed and pixel-verified.
4. Do not combine eight clocks into an arbitrary fixed-frame GIF or apply palette cycles to raw images independently of the shared room palette.

**Status:** original archive/source decoder and pinned engine source; no active-runtime or frame-level verification.
