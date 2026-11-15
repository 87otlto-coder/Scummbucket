# P4 — Room 12 indexed actor capture audit (15 November 2026)

**Scope:** Original Monkey Island 2 DOS VGA, real Room 7 → 12 → 7 route. This audit uses the user's recovered metadata, not the private raw engine indexed buffers.

Capture ID: cross-room-e4deddf716114bc9907d5d99e1b85232.
Uploaded cross-room-indexed.json SHA-256: 5ab5c5859e1028538ffb780292b555a846e1d937080fcb8354e5278fa16d45d7 (1,877,586 bytes).

Reported acceptance status: indexed_capture_with_actor7_8_observed.
Scene fidelity: **NOT VALIDATED**.

## Verified manifest structure

- 472 unique consecutive indexed engine frame and tick numbers (1–472).
- 1,227 sequential presentation records; a post-final-tick SDL reference to tick 473 is not an extra engine tick.
- Room groups: Room 7 ticks 1–149; Room 12 ticks 150–393 (244 frames); Room 7 ticks 394–472 (228 total Room 7 frames).
- Zero metadata sequence gaps, duplicate ticks, malformed 16-cursor / 32-slot actor rows or invalid digest formats detected.
- The file includes hashes and actor state, **not original source indexed front-buffer bytes**. Hash content cannot be rechecked independently from this JSON alone.

## Room 12 actor state

| Actor | Costume | Draw observations | Planes |
| --- | --- | ---: | --- |
| Guybrush (1) | COST 1 | 232 | 0:128, 1:50, 2:54 |
| Actor 7 | COST 20 | 244 | 2:244 |
| Actor 8 | COST 41 | 244 | 0:244 |

Actor 7 is observed at (119,101), actor 8 at (220,136), both at scale 255. Guybrush's scale varies from 179 to 255. The actors have distinct recorded cursor vectors: Guybrush 21, actor 7 31 and actor 8 four.

**Draw order changes within Room 12:** 7–1–8 in 147 frames; 1–7–8 in 70; 7–8–1 in 15; and 7–8 in 12. A fixed draw-order compositor would be incorrect. Absence of Guybrush from 12 draw records is not evidence the character was deleted.

219 unique indexed front-buffer hashes, one background-buffer hash, and 31 final palette hashes were recorded in Room 12. All four depth buffer hashes are stable across this recording.

## Source fidelity problem discovered and corrected

All 32 entries of every recorded Actor::_palette were **255 across all 472 frames**. ScummVM ClassicCostumeRenderer::setPalette explicitly interprets 255 as a sentinel to use the original loaded COST palette slot. The earlier source-based multi-actor compositor instead drew with palette index 255.

Corrected in scummbucket/scene_source.py, with synthetic tests in tests/test_scene_source.py covering default COST fallback, an explicit palette override and stopped-limb masking. This correction is backed by the ScummVM classic costume renderer source; it is not itself independent full-scene validation.

## Next gate

Run the existing PowerShell stage Compare on the original F: capture after fast-forwarding the P5-named research branch. That stage compares source-composited 320x144 Room 12 indexed frames with the original captured indexed buffers, reporting every unexplained difference and an unmasked negative control in a fresh FIXTURE/REPORTS/P5 directory.

A mismatch is a **partial research result** and must not be disguised as source-faithful framebuffer reconstruction. The previous RGB video audit and this indexed metadata audit answer different questions.

No original copyrighted archive, frame image, binary or raw capture is committed. Draft PR #17 remains unmerged.
