# P4 — Room 23 VGA recording: spatial correspondence with CYCL source pixels

**Status:** Observed video changes strongly coincide with source-backed palette-cycle pixel positions. **Exact engine palette updates, timing, and other possible scene effects are still unverified.**

**Date:** 2026-11-08  
**Game:** Original DOS Monkey Island 2 VGA resource file (fingerprinted)  
**Location:** Scabb Island peninsula / Captain Dread's ship exterior, room 23

## What was compared

The user supplied original-game video recordings and screenshots from ScummVM. No recording, screenshot, decoded background, or source-game bytes are committed to GitHub.

| Evidence | Value |
| --- | --- |
| Original game file | `MONKEY2.001`, SHA-256 `ad045372e0d49626503bb50fca29a687ec8e01ef75d9b8bca702a366d143819e` |
| Native room-23 indexed background | 320 × 144, SHA-256 `94b7b2d675778bf73c73a87eca05ab74dca470ad67555faecd03ab112acbcd9f` |
| Room-23 CYCL definitions | 8, color pairs 176–177 through 190–191 |
| Source-background pixel positions using those ranges | **480 / 46,080 = 1.0417%** |
| User-supplied recording compared | `Recording 2026-11-08 114050(1).mp4` |
| Video SHA-256 | `ffd79ef3d141c8256b47271b497596a66d2f859f39d77093def0666c0283edfd` |
| Video geometry and duration | 324 × 208, 30 fps, approximately 20.77 seconds |
| Aligned native-room origin in video | x=3, y=4; estimated by minimizing median pixel difference in the relatively static upper 48 native scanlines |
| Video sampling | One decoded frame at each whole second t = 1..19, compared against t=1 |
| Change criterion | Maximum absolute RGB channel difference across sampled times **at least 20 / 255** from the first sampled frame |

The source-indexed background was decoded separately from the video. The mask identifies exactly those source pixel positions whose **original palette indices** lie in the eight room-23 cycle ranges. The recording was then aligned to the source room coordinates; a fixed, single-pixel grid translation was adequate for this 1× capture.

## Direct source geometry

The eight palette ranges account for these unique pixel positions:

| Cycle ID | Source color indices | Pixel positions |
| ---: | --- | ---: |
| 1 | 176–177 | 90 |
| 2 | 178–179 | 55 |
| 3 | 180–181 | 42 |
| 4 | 182–183 | 75 |
| 5 | 184–185 | 65 |
| 6 | 186–187 | 49 |
| 7 | 188–189 | 84 |
| 8 | 190–191 | 20 |
| **Union** | **176–191** | **480** |

Every mapped pixel is in source rows **52–123** (0-indexed). In the original background they appear as short horizontal strokes concentrated across water regions. The original sky above row 52 has **zero** cycle-covered pixels. No cycle-covered pixel appeared inside an **approximate**, manually selected cabin/window study rectangle **x=126..176, y=43..82**. That rectangle is not an automatic semantic segmentation of the ship.

This rules out *these eight source CYCL ranges* acting directly on the examined cabin-window pixels. It does **not** rule out ship-light effects caused by object states, other palette operations, sprites/costumes, or different scene setup.

## Temporal video comparison

After aligning the source and video, the peak color difference across the 19 sampled frames was evaluated separately for the 480 source-cycle pixels and other room pixels.

| Pixel population | Pixels exceeding 20/255 channel-difference threshold | Fraction |
| --- | ---: | ---: |
| **Source CYCL positions** | **457 / 480** | **95.2%** |
| Other room-background positions in the comparison region | 378 / 26,469 | 1.43% |

The comparison region for the second row includes y≥52 and excludes the approximate Guybrush idle-animation rectangle x=30..74, y=88..143. The denominator is the remaining non-cycle pixels within that region.

Other thresholds provide useful robustness checks:

| Threshold | CYCL positions changing | Other comparison-region positions changing |
| ---: | ---: | ---: |
| 15 | 475 / 480 (99.0%) | 2,435 / 26,469 (9.20%) |
| **20** | **457 / 480 (95.2%)** | **378 / 26,469 (1.43%)** |
| 25 | 432 / 480 (90.0%) | 48 / 26,469 (0.18%) |
| 30 | 355 / 480 (74.0%) | 8 / 26,469 (0.03%) |

All **eight cycle groups** contain video pixels above the 20/255 threshold, supporting a real, spatially localized effect rather than a global render-mode color change.

**Interpretation:** The strong overlap between a map generated **only from original resources** and the changes visible in a private ScummVM video is **strong spatial corroboration of palette-driven water shimmer**. However, video capture/compression, secondary animations, decoder error, and runtime palette manipulation remain possible confounders. The video alone does **not** establish the exact engine invocation cadence, original RNG/script inputs, or which of the eight cycles was independently active at a given instant.

This is **stronger evidence than the previous hypothetical snapshot preview**, but is not a byte-for-byte palette trace or a frame-perfect timing verification.

## Measured video cadence versus CYCL rates (additional temporal analysis)

The same 324 × 208 recording was also decoded at its full **30 fps** (623 frames). For each pair of source palette indices, the pixels originally using the lower or upper entry were grouped by source location. The **median RGB** of each group was compared to the original `CLUT` pair in its normal order versus its swapped order. A three-frame majority filter suppressed isolated video-compression classification errors. Every switch between the two resulting color orders was recorded as a **video-observed transition**, without trying to infer individual engine instructions.

| Source CYCL ID | Raw rate | Engine delay `16384 // rate` | Observed swap intervals | Median observed seconds | Predicted seconds at *hypothetical* 60 counter units/sec |
| ---: | ---: | ---: | ---: | ---: | ---: |
| 1 | 230 | 71 | 17 | **1.200** | 1.183 |
| 2 | 307 | 53 | 23 | **0.867** | 0.883 |
| 3 | 153 | 107 | 11 | **1.800** | 1.783 |
| 4 | 384 | 42 | 29 | **0.700** | 0.700 |
| 5 | 460 | 35 | 35 | **0.600** | 0.583 |
| 6 | 384 | 42 | 29 | **0.700** | 0.700 |
| 7 | 230 | 71 | 17 | **1.200** | 1.183 |
| 8 | 307 | 53 | 23 | **0.867** | 0.883 |

The observed median intervals are within **one 30-fps frame (33.3 ms)** of the 60-counter-unit/sec predictions for every range; the greatest absolute median discrepancy is approximately **16.7 ms**. Notably, pairs **1 and 7** share near-identical transition times, as do **4 and 6**, matching their shared source rates. Individual intervals are less stable because recording frame rate, engine scheduling, captured frame duplication, phase and potential drop/repeat behavior introduce jitter; we do not assume one video frame equals one SCUMM timer unit.

**Conclusion from the video:** A 60-counter-unit/sec model fits the observed water shimmer extraordinarily well, and all eight palette pairs visibly alternate. This upgrades the evidence for real water animation and supports plausible real-time cadence. It does **not** independently establish the actual values of `VAR_TIMER` or `VAR_TIMER_NEXT`, whether scripts intervene, exact sub-frame transition instants, or millisecond-perfect export timing. A real engine-state trace remains the necessary final cross-check.

The video source's classification and alignment were made from the **VGA-appearing** 1× recording and original indexed artwork. The captured renderer configuration is supported by a user-supplied settings screenshot but not cryptographically authenticated by the video itself. The EGA-like capture is intentionally excluded from this timing estimate.

## Reproduce the source-coordinate map locally

Run from the Windows checkout, using the already tested authorized game archive:

```powershell
cd "C:\Users\87otl\ScummBucket"
git pull --ff-only origin feature/p1-scumm-v5-inventory

$stamp = Get-Date -Format "yyyyMMdd-HHmmss"
$out = "C:\Users\87otl\ScummBucket\exports\room23-palette-map-$stamp"
python -m scummbucket palette-map "D:\old" --room 23 --output-dir "$out"
```

The new `palette-map` command produces:
- An alpha-transparent overlay highlighting the union of all source cycled-index positions.
- Eight separate grayscale masks, one per CYCL definition.
- A JSON manifest with per-cycle bounds/counts, source hashes, original indexed-pixel hash, file hashes, and explicit diagnostics.

The output is **native 320 × 144** so it can be overlaid on a VGA capture after separately establishing source-to-screen geometry. It contains no assumptions about water, light fixtures, animation timing or render mode.

Synthetic tests check mask uniqueness, overlapping color ranges, valid bounds, no-overwrite behavior and failures. The optional private MI2 integration test asserts the eight observed room-23 counts and source fingerprint. Public CI skips proprietary-resource checks.

## Rendering-mode control and remaining verification

The user's ScummVM settings screenshot showed **Render mode VGA**, **Graphics mode OpenGL**, **Scaler Normal 1×**, **Shader None**, **filtering off**, and **aspect correction off**. Future screenshot and video comparisons should record these along with exact ScummVM build, game-resource fingerprint, crop origin and capture size. An EGA-style rendering recording was also supplied; it is intentionally **not used** to establish the VGA source-coordinate count or engine timing.

Recommended follow-ups:

1. Record a natural game-entry capture under the same VGA settings, ideally minimizing camera/window movement and character idle motion.
2. Trace the actual `_currentPalette` changes and `VAR_TIMER`/`VAR_TIMER_NEXT` values at `cyclePalette()`, using the separately specified exact trace contract in [P4 runtime palette verification](P4_RUNTIME_PALETTE_VERIFICATION.md).
3. Compare each real palette update against the model. Report every mismatch; only then derive faithful frame/event timing.
4. Investigate ship-light or cabin-window changes **separately**: the current eight CYCL ranges are not present in the examined light-pixel region, but other visual mechanisms have not been ruled out.
5. Expand to room 109, and subsequently test a mixed object/script/palette background.

**Conclusion:** Room 23 is now **strongly corroborated as a palette-animated water scene**, supported by original indexed-source locations, close video pixel correspondence and an observed swap cadence consistent with an effective ~60 counter-unit/second model. **Exact engine timer values, script interference and pixel-perfect rendering remain to be verified**; P4's timing-accurate export exit criterion is not yet met.
