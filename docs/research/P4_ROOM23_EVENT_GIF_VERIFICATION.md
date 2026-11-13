# P4 — Room 23 event-driven GIF: private-output verification

**Status (2026-11-08):** The user-provided Room 23 GIF and manifest have been independently inspected. **PASS: artifact integrity, modeled timing, source-pixel spatial constraint, and agreement with two previous PNG checkpoints.** This is a reproducible synthetic-event export reference, **not** verified ScummVM engine timing or a complete reconstructed scene.

## Artifacts inspected (not committed)

- Local input bundle: `room23-events-20261108-143724`.
- Local output: `room23-event-preview-20261108-151952.gif`, 278,734 bytes; SHA-256 `1a654c4ed3575ccca020d00566be0baab1bfade51d0c1439e144d7e91b516f95`.
- Adjacent `.manifest.json` reports status success and records bundle SHA-256 `51407c03772450505d3f3a9cf5af37dd3a2109f69b1290b2c3c511058217028c`.
- Original source resource SHA-256 **declared** in provenance: `ad045372e0d49626503bb50fca29a687ec8e01ef75d9b8bca702a366d143819e`; this verification did not reopen that original archive.
- The preexisting original source-indexed PNG, `room-023_event-frame-0000.png`, and independent output PNG `room-023_event-frame-0080.png` were also available for visual pixel comparisons.
- No proprietary source files, PNGs, GIFs or palette bytes were committed.

## Independent checks

| Check | Observation |
|---|---|
| GIF SHA-256 and byte length | Exact match to the supplied JSON manifest |
| Dimensions | 320 × 144 native pixels |
| GIF frames | 20, matching 19 source-event boundaries plus initial state |
| Distinct decoded RGB frames | 17 |
| Frame delays | All 20 GIF delays equal the manifest; cumulative time exactly **4,000 ms** |
| GIF looping | No Netscape looping extension present (play-once presentation) |
| Saved counter boundaries | 0, 35, 42, 53, 70, 71, 84, 105, 106, 107, 126, 140, 142, 159, 168, 175, 210, 212, 213, 214 |
| Original source PNG frame zero | GIF segment zero is pixel-identical in decoded RGB |
| Prior PNG frame 80 | GIF segment five is pixel-identical in decoded RGB |
| Changed pixels over full GIF vs source frame zero | **480 / 46,080** (1.0417%) |
| Source indexed pixels in eight Room-23 CYCL ranges 176..191 | Exactly **480**, one-to-one with the changed-pixel set |
| Changed outside source CYCL mask | **0** |
| Source CYCL positions never changed | **0** |
| Changed-position bounds | x=0..319, y=52..123 (the earlier water-shimmer region) |

No actor, foreground layer, mask or script-controlled environmental effects are reconstructed. The water-shimmer spatial result is independently consistent with `P4_ROOM23_VGA_SPATIAL_VALIDATION.md`, but this GIF itself is **not an original-game playback trace**.

## Timing and playback limitations

- Assumed palette counter rate: 60 modeled counter units/sec. No actual `VAR_TIMER` or `VAR_TIMER_NEXT` value was recorded.
- Absolute event boundaries were rounded to GIF centiseconds. The aggregate 4 seconds remains correct; individual event intervals can differ by a few milliseconds.
- Two states have **10 ms** GIF duration (at counter ticks 70 and 106). The output manifest correctly emits `GIF_SHORT_FRAME_DELAY`. Some viewers will clamp, drop or lengthen such short states. GIF is not a suitable authoritative container for exact sub-20-ms timing.
- There are 17 unique visual states, but 20 timeline segments: three previously observed visual states recur later. Nonconsecutive repeats must not be collapsed.
- Archive-wide `CYCLE_FLAGS_UNVERIFIED` / `CYCLE_DELAY_ZERO_IN_ENGINE` warnings belong to room resources 35, 38 and 64, not the Room 23 event data; they are nevertheless retained for archive provenance.

## Regression acceptance

This is an appropriate **P4 synthetic-event presentation regression**: a future exporter should reproduce the 20 modeled segments, their 17 unique visible states, 4,000 ms nominal duration, exactly the same rendered RGB pixels in order, and all warnings. GIF binary bytes need not be identical across Pillow/LZW encoder versions; compare decoded RGB and delays, not compression hashes, for cross-version reproducibility.

The optional `tests/test_private_room23_event_gif.py` fixture asserts decoded RGB checksums for all 20 GIF segments when `SCUMMBUCKET_ROOM23_EVENT_BUNDLE` points to the private source bundle; it is skipped in public CI.

This reference **must not** be used to claim actual engine-frame timing, faithful object/sprite compositing, a seamless loop, or P4 completion. Those acceptance criteria still require instrumented ScummVM palette-state measurements and representative mixed-mechanism scene verification.
