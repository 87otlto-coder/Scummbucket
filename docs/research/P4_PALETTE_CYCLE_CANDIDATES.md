# P0/P4 — Autonomous background-animation candidates from MI2 CYCL inventory

**Status:** Structural triage only; observed palette-cycle configuration is not yet proof that the visual effect executes or appears at runtime.  
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

## Proposed verification experiment

1. **Start with room 23.** Inspect `CYCL` record rates and color ranges; identify which palette indices occur in the decoded room's pixel buffer. This must be done without assuming the raw `rate` field is milliseconds, frames or ticks.
2. Decode one static room background in native palette indices. Capture the corresponding initial `CLUT` palette and compare with ScummVM room rendering.
3. Instrument or observe a **time series of runtime palette values**, preferably with an original-engine/ScummVM trace. Identify the number of changed entries, direction of cycling, and measured timing.
4. Determine whether engine state automatically advances cycles, or whether a global/room script starts, stops, modifies, or overrides them.
5. Reconstruct a **palette-only animation** as separate source bitmap plus palette-event timeline if evidence supports it; do not bake rendered backgrounds into permanent raster frames when the source mechanism can be preserved.
6. Repeat with room 109 and then a more complex mixed-mechanism room (51 or 28).
7. Keep reports for absent colors, ineffective cycles, unsupported flags, invalid offsets, and unverified timing. Report those as explicit uncertainties or failures, not as "no animation."

**P4 exit criterion is not met:** no continuous background animation has yet been observed and reconstructed. The CYCL room shortlist gives us reproducible targets for doing that.
