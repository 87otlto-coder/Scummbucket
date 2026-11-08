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

Direct source-byte verification of the user-supplied `MONKEY2.001` confirms the three anomaly locations:

- **Room 35:** cycle 1 at decoded resource offset **2,781,146** has rate **3,072**, flags `0x0004`, colors **176–191**; cycle 2 at **2,781,155** has rate **2,688**, flags `0x0004`, colors **160–175**.
- **Room 38:** cycle 1 at offset **2,939,224** has rate **459**, flags `0x0004`, colors **179–180**.
- **Room 64:** cycle 2 at offset **5,426,226** has raw rate **65,494**, flags `0xD906`, colors **97–98**. For this value, integer `16384 // 65494 = 0`; ScummVM's cycle updater skips entries with delay zero.

ScummBucket now issues a **separate** `CYCLE_DELAY_ZERO_IN_ENGINE` warning for such rate values, in addition to preserving all four `CYCLE_FLAGS_UNVERIFIED` warnings. **That makes five distinct warning occurrences in the analyzed original archive**, rather than reducing or muting the original four. The cause of the high raw flag bits remains **unresolved**; the parser does not assume they are meaningless or corrupted.



## New evidence: original indexed backgrounds and engine palette cycling

Read-only analysis of the supplied original DOS MI2 resource pair, cross-checked with [ScummVM palette.cpp](https://github.com/scummvm/scummvm/blob/master/engines/scumm/palette.cpp), gives us a more concrete P4 starting point.

The engine initializes CYCL entries on room load. In this v5 format it calculates the cycle delay as **integer 16384 / raw cycle rate**. Its cycle updater advances a counter using the larger of two engine timer variables and rotates the palette range when the threshold is reached, **at most once per invocation**. Bit 1 of the raw flags controls reverse direction. The unit is an **engine counter unit, not a millisecond or guaranteed rendered frame**. Global scripts and room code can still alter, stop or restart cycling.

The `palette-probe` command decodes the original background to native palette indices (RMIM / IM00 / SMAP) and rotates a copy of the original CLUT using a deliberately synthetic scheduler. Its default is **one counter unit per simulated update**, and the new `--counter-increment` option supports other explicit counter-unit assumptions. These images remain **hypothetical** background-palette snapshots, not recordings of gameplay.

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

### Next verification step: exact engine timer and palette snapshots

The prototype now has a strict comparison command, `verify-palette-trace`, for **externally captured** ScummVM palette data at the point immediately after `cyclePalette()` and before `palManipulate()`. ScummVM's main SCUMM loop writes `VAR_TIMER` from its current delta, and `cyclePalette()` advances each counter using `max(VAR_TIMER, VAR_TIMER_NEXT)`. Input capture must contain both values and all 256 RGB colors for each update, along with a reproducible source archive hash, engine revision, baseline palette and sequential update ID.

The comparator reports per-update palette SHA-256, number of differing palette entries, and the first sample at which the model diverges. It does **not** authenticate supplied traces or equate palette agreement with verified on-screen animation. Its synthetic regression tests pass, but **no real ScummVM trace has been supplied**.

For the executable contract, Windows commands and non-compiling screenshot observation alternative, consult [P4 Runtime Palette Verification](P4_RUNTIME_PALETTE_VERIFICATION.md).

## Real VGA video spatial and timing correspondence (2026-11-08)

The user supplied an approximately 20.8-second ScummVM recording with VGA-looking artwork. **Independent source-coordinate mapping** placed the eight CYCL color pairs (indices 176–191) onto all **480** native room-23 background pixels using those indices. They form sparse horizontal water highlights. No covered source pixel was found in an **approximate** cabin-window study rectangle; this does not rule out other ship-light mechanisms.

After fixed-grid alignment, 19 sampled VGA video frames showed color changes at **457/480 (95.2%)** cycle positions, versus **378/26,469 (1.43%)** of the non-cycle comparison pixels, using the same 20/255 RGB-channel threshold. This strongly corroborates the palette-driven water shimmer.

Full-frame 30-fps analysis also identified alternating source palette pairs. Their median observed swap intervals were **1.20, 0.867, 1.80, 0.70, 0.60, 0.70, 1.20, and 0.867 seconds** for cycles 1–8. They agree within one capture frame with the source-derived delay thresholds `71, 53, 107, 42, 35, 42, 71, 53` divided by **a hypothesized effective 60 counter units per second**. This is a video-derived cadence estimate, **not directly captured internal SCUMM timer values**.

The new `palette-map` command exports a **source-native transparent overlay, one grayscale pixel mask per CYCL range, and source-hashed manifest**. Synthetic tests verify exact mask union behavior and reject invalid sources; optional original MI2 integration checks remain skipped in public CI.

See [room-23 spatial/video validation and method](P4_ROOM23_VGA_SPATIAL_VALIDATION.md) for the video SHA-256, alignment, exact pixel counts, capture settings, individual cycle results, uncertainty and reproducibility command. No original game art, screenshot or video was committed to GitHub.

**Evidence level:** Source palette-cycle indices and scene pixel positions are directly decoded; time-varying water pixels are visually observed and strongly spatially correlated; effective cadence is estimated from the recording. Exact runtime palette values, script overrides and animation-export timing remain unverified.

## Proposed verification experiment

1. **Completed:** Inspected room-23 CYCL ranges, raw rates and original indexed pixels. All eight ranges are used by the background.
2. **Partially completed:** Decoded native room-23 and room-109 backgrounds into indexed buffers and original CLUT palettes. Independent pixel-for-pixel ScummVM comparison remains pending.
3. **Next:** Instrument or observe a time series of actual palette values in ScummVM to establish real runtime changes, direction, script interference and elapsed timing.
4. Determine whether engine state automatically advances cycles, or whether a global/room script starts, stops, modifies, or overrides them.
5. **Experimental export implemented:** The new [native indexed PNG palette-sequence exporter](P4_PALETTE_SEQUENCE_EXPORT.md) preserves the source pixel indices and records per-frame palette updates using a **video-calibrated, unverified engine-timing hypothesis**. **Next:** execute its private original-archive regression and compare the exported frames with live ScummVM rendering and an actual engine-state palette/timer trace.
6. Repeat with room 109 and then a more complex mixed-mechanism room (51 or 28).
7. Keep reports for absent colors, ineffective cycles, unsupported flags, invalid offsets, and unverified timing. Report those as explicit uncertainties or failures, not as "no animation."

**P4 exit criterion is not met:** room-23 water shimmer is visibly observed and strongly correlated with original CYCL pixel positions and estimated cadence. Palette-only **PNG sequences, nonlooping GIF previews and FPS-independent hypothetical counter-event bundles** are implemented. The new [event timeline](P4_PALETTE_EVENT_TIMELINE.md) preserves original indexed pixels and exact model patches; it is a distinct timing hypothesis, not a silent replacement for the earlier frame-driven GIF/PNG schedule. Private original-game event integration and real ScummVM engine-clock validation remain pending. Layered/scripted background-animation coverage and independent room-109 validation are outstanding.
