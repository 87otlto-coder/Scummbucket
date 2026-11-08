# P0/P4 — Autonomous background-animation candidates from MI2 CYCL inventory

**Status:** Indexed room background decoded; engine-described palette rotation reproduced as a hypothetical preview. Actual gameplay execution and timing are not verified.  
**Source:** Fingerprinted original DOS Monkey Island 2 `MONKEY2.000/.001` pair (SHA-256 values in [P0/P1 evidence register](P1_OBJECT_358_SCRIPT_SURVEY.md)).  
**Research date:** 2026-11-08.

## Purpose

We must avoid limiting ScummBucket to static room backgrounds or to interactively changing image states. Room 34, object 358, is a **script-controlled puzzle graphic**, not a demonstrated continuously animated room background.

The initial source-data survey identified **127 `CYCL` palette-cycle records in 21 rooms**, and **158** multistate object-image resources across the game. These are *candidate mechanisms*, not evidence of active rendered animation.

The following are **non-exclusive investigation priorities**, not a claim that these room effects run continuously.

| Room | `CYCL` records | Multistate object images | Local `LSCR` chunks | Why investigate |
| ---: | ---: | ---: | ---: | --- |
| **23** | **8** | **0** | **0** | High cycle count without local scripts or multistate objects; possible engine-driven visual effect |
| **109** | **5** | **0** | **0** | Another palette-driven candidate with no local scripts |
| **89** | **1** | **0** | **0** | Small, simple candidate for initial palette-cycle validation |
| **51** | **12** | **1** | **7** | Largest observed cycle count; more mechanisms to disentangle |
| **28** | **9** | **2** | **6** | Multiple cycles and multistate objects |
| **27** | **9** | **1** | **6** | Multiple cycles and one multistate object |
| **47** | **4** | **11** | **22** | Rich scripted/object environment; poor initial *autonomous* control case |
| **35** | **2** | **1** | **3** | Two unresolved `CYCL` flags |
| **38** | **6** | **2** | **1** | One unresolved `CYCL` flag |
| **64** | **2** | **0** | **2** | One unusual raw flag value; requires format investigation |

**Important counterpoint:** A room with zero local `LSCR` chunks can still be controlled by global scripts or engine callbacks. It must not automatically be labeled "autonomous."

## Four unresolved flag warnings

The archive-wide `CYCLE_FLAGS_UNVERIFIED` messages remain exactly these structural uncertainties:

| Room | Number of affected cycle records | Raw flag value |
| ---: | ---: | --- |
| 35 | 2 | `0x0004` |
| 38 | 1 | `0x0004` |
| 64 | 1 | `0xD906` |

These raw values require checking against the actual v5 palette-cycle implementation. No warning has been suppressed as a result of successful object decoding or script disassembly.

## New evidence: original indexed backgrounds and engine palette cycling

Read-only analysis of the supplied original DOS MI2 resource pair, cross-checked with [ScummVM palette.cpp](https://github.com/scummvm/scummvm/blob/master/engines/scumm/palette.cpp), gives us a more concrete P4 starting point.

The engine initializes CYCL entries on room load. In this v5 format it calculates the cycle delay as **integer 16384 / raw cycle rate**. Its cycle updater advances a counter using the larger of two engine timer variables and rotates the palette range when the threshold is reached, **at most once per invocation**. Bit 1 of the raw flags controls reverse direction. The unit is an **engine counter unit, not a millisecond or guaranteed rendered frame**. Global scripts and room code can still alter, stop or restart cycling.

The new palette-probe command decodes the original background to native palette indices (RMIM / IM00 / SMAP) and rotates a copy of the original CLUT using a deliberately synthetic scheduler: **one counter unit per simulated update**. The resulting images are **hypothetical** background-palette snapshots, not recordings of gameplay.

| Observation | Room 23 | Room 109 |
| --- | ---: | ---: |
| Native image dimensions | 320 x 144 | 320 x 200 |
| Background strips | 40 | 40 |
| Source codec for all strips | 68 | 68 |
| CYCL records | 8 | 5 |
| Pixel positions using at least one cycle range | **480** | **65** |
| SHA-256 of decoded index buffer | 94b7b2d675778bf73c73a87eca05ab74dca470ad67555faecd03ab112acbcd9f | 47adf2c2d270f2cabaeca483feadd5b5c1d524b7c64df2d1a14a3356adfcca79 |

Every cycle range in room 23 and room 109 is present in the corresponding source background. The pixel counts use **unique positions**, even if cycles overlap; this is evidence that palette cycling *can affect visible room pixels*, not that it actually runs during gameplay.

### Measured hypothetical image differences

| Simulated counter updates | Room 23 pixels changed vs initial | Room 109 pixels changed vs initial |
| ---: | ---: | ---: |
| 0 | 0 | 0 |
| 35 | 65 | 50 |
| 71 | 373 | 30 |
| 107 | 281 | 56 |

The changed pixel count may decrease as two-color ranges rotate back to their starting colors. This is expected in the synthetic preview and must not be interpreted as runtime evidence of an animation stopping.

Room 23's raw-rate / counter-delay pairs are 230/71, 307/53, 153/107, 384/42, 460/35, 384/42, 230/71 and 307/53. No wall-clock conversion has yet been verified.

### Reproduction

From the standard Windows checkout, with your authorized MI2 archive already at D:\old:

    cd "C:\Users\87otl\ScummBucket"
    git pull --ff-only origin feature/p1-scumm-v5-inventory
    $stamp = Get-Date -Format "yyyyMMdd-HHmmss"
    $out = "C:\Users\87otl\ScummBucket\exports\room23-palette-$stamp"
    python -m scummbucket palette-probe "D:\old" --room 23 --ticks 0 35 71 107 --output-dir "$out"

The new output contains native-size PNG previews and a manifest recording source hashes, bitmap index hashes, palette hashes, simulator counter units, simulated rotation events, and explicit failure/warning diagnostics. Unsupported compression, malformed chunks, missing colors, overlaps, and collisions are not silently concealed. Original game assets and generated frame images remain outside GitHub.

An optional private integration test checks exact room-23 and room-109 fingerprints and changed-pixel counts; it skips in CI unless SCUMMBUCKET_MI2_ARCHIVE is provided privately.

### Cycle flags still unresolved

ScummVM's palette rotation tests flag bit 1 for direction, but this does not establish the meaning or origin of every other raw bit. The four existing CYCLE_FLAGS_UNVERIFIED warnings in rooms 35, 38 and 64 remain visible.

Room 64 includes an anomalous raw cycle rate of 65494, yielding a computed integer delay of zero in the inspected engine logic, and its range 97–98 is absent from the decoded static room background. This raises questions rather than resolving the suspicious 0xD906 raw flags.

**Evidence boundary:** We have now reproduced plausible indexed-background palette changes under explicit simulation assumptions. We have *not* verified executed gameplay cycles, runtime ticks, script interference, compositing of actors/objects/masks, or pixel-perfect ScummVM reference rendering.

## Proposed verification experiment

1. **Completed:** Inspected room-23 CYCL ranges, raw rates and original indexed pixels. All eight ranges are used by the background.
2. **Partially completed:** Decoded native room-23 and room-109 backgrounds into indexed buffers and original CLUT palettes. Independent pixel-for-pixel ScummVM comparison remains pending.
3. **Next:** Instrument or observe a time series of actual palette values in ScummVM to establish real runtime changes, direction, script interference and elapsed timing.
4. Determine whether engine state automatically advances cycles, or whether a global/room script starts, stops, modifies, or overrides them.
5. Reconstruct a **palette-only animation** as separate source bitmap plus palette-event timeline if evidence supports it; do not bake rendered backgrounds into permanent raster frames when the source mechanism can be preserved.
6. Repeat with room 109 and then a more complex mixed-mechanism room (51 or 28).
7. Keep reports for absent colors, ineffective cycles, unsupported flags, invalid offsets, and unverified timing. Report those as explicit uncertainties or failures, not as "no animation."

**P4 exit criterion is not met:** no continuous background animation has yet been observed and reconstructed. The CYCL room shortlist gives us reproducible targets for doing that.
