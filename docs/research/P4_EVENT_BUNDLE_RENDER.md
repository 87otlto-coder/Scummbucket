# P4 — Render indexed PNGs from an exported palette-event bundle

**Status:** Feature implemented, synthetic regression tests passing. Private-source bundle supplied by the user was independently checked. The new repository CLI still requires optional integration verification against the user's Windows export.

## Purpose

The new "render-events" command needs only a **previously exported** palette-events bundle:
- room-023_indexed.png
- room-023_initial-clut.rgb
- timeline.json

It does **not** reopen MONKEY2.001, re-extract the original game, reinterpret the CYCL flags, or rerun the palette-cycle simulator. It validates the saved bundle and replays the exported RGB patch history to produce a new frame sequence at the requested output FPS.

This makes source decoding, **hypothetical palette-event reconstruction**, and raster frame-rate selection separate operations. It does **not** prove engine scheduling, timing accuracy, layering, or seamless loops.

## Run on Windows using the existing room-23 bundle

    Push-Location "C:\Users\87otl\ScummBucket"
    git pull --ff-only origin feature/p1-scumm-v5-inventory

    $bundle = "C:\Users\87otl\ScummBucket\exports\room23-events-20261108-143724"
    $stamp = Get-Date -Format "yyyyMMdd-HHmmss"
    $out = "C:\Users\87otl\ScummBucket\exports\room23-replay60-$stamp"

    python -m scummbucket render-events "$bundle" --fps 60 --output-dir "$out"

    Pop-Location
    explorer.exe "$out"

This produces 240 **native 320 x 144 indexed PNG frames** and a render-manifest.json with exact source-bundle fingerprints, sampled counter ticks, per-frame palette hashes, inherited diagnostics and any skipped intermediate states.

The requested FPS may be 1..60, but the export remains bounded to 240 PNG frames per operation. For four-second room 23, 60 fps is the largest available within this bound. The original indexed background remains unchanged in its source bundle. No Pillow installation is needed.

## Independent check of the uploaded original-game bundle (2026-11-08)

The user uploaded room-023_indexed.png, room-023_initial-clut.rgb and timeline.json from the local room23-events-20261108-143724 export.

The uploaded original indexed PNG is 320 x 144 and has SHA-256 9f8807bc71efbb97cd68160c916760183f71e9607a4de19b67b2504e9272adf7. The source indices have SHA-256 94b7b2d675778bf73c73a87eca05ab74dca470ad67555faecd03ab112acbcd9f. The separately uploaded CLUT is 768 bytes and SHA-256 44a542ed57e641676623a0d48c5a28a7b8d47e87482acb5af21a4a2eef65d242, matching the original PNG's PLTE and every SHA-256 in the provided manifest.

The supplied event manifest declares original resource SHA-256 ad045372e0d49626503bb50fca29a687ec8e01ef75d9b8bca702a366d143819e. **This is a manifest declaration, not a rehash of the absent original game file in this comparison.**

An independent in-memory patch replay verified:
- 19 distinct time positions containing cycle changes.
- 32 individual modeled rotations across those positions.
- Exact before/after RGB values for every changed palette entry.
- Exact full-CLUT SHA-256 after every event; final value 1e6a0ce0942efec60e5ceb7daa1f09d1b9f92151c8a89a429ef852b739cd1d97.
- Four archive-wide CYCLE_FLAGS_UNVERIFIED warnings and one separate CYCLE_DELAY_ZERO_IN_ENGINE warning, retained rather than suppressed.

The upload is a **self-consistent modeled event bundle**. It is not a genuine instrumented ScummVM timer trace.

## Why frame rate changes visual state coverage

A renderer samples the latest available state at output frame i using integer modeled counter tick floor(i * source_counter_rate / output_fps). The original event list remains intact regardless of output FPS.

For the fingerprinted uploaded room-23 event bundle:

| Output FPS | Frames in four seconds | Intermediate palette event states not sampled | Counter positions not independently shown |
| ---: | ---: | ---: | --- |
| 15 | 60 | **5** | 70, 105, 106, 210, 213 |
| 30 | 120 | **2** | 105, 213 |
| 60 | 240 | **0** | None |

At 30 fps, this does not mean two events vanished from the JSON. Instead their temporary palette states are overwritten by subsequent modeled events before a video frame is sampled. A 60-fps output captures all 19 modeled event states in this particular four-second example, **not all possible real-game events**.

The new renderer computes the omitted-state count and emits a visible EVENT_RENDER_UNSAMPLED_STATES warning at output FPS that miss intermediate event states. It also preserves the original five archive warnings.

The earlier PNG sequence and GIF use a **different synthetic scheduler** (one palette update per exported frame). Therefore a numerical match in frame count, or an approximately similar visual result, is not a proof of equivalent event timing. Do not silently replace that original model until verified against real engine calls.

## Validation and diagnostics

The new renderer:
- Requires a successful palette_counter_events schema-v0.1 timeline and known counter model, validates timing data and the source room ID.
- Verifies PNG and CLUT file sizes and SHA-256 against the timeline's output-file entries.
- Parses the ScummBucket-authored indexed PNG strictly (indexed 8-bit, no interlace, row filter zero), checking PNG chunk CRCs, bounded decompression, dimensions, exact palette bytes and original indexed-pixel SHA-256. It does not pretend to be a general PNG codec.
- Replays **all** recorded palette events and RGB patches from the saved CLUT, verifying before and after hashes; even events after the last requested sample are validated.
- Generates one standard indexed PNG per requested output sample and records each output hash and source palette state.
- Refuses filename collisions/symlinks, invalid FPS, missing or corrupted source files, invalid events and excessive output.
- Reports failures and partial writes explicitly. It never modifies the original event bundle.
- Marks the source scheduling model and original game-state verification as **unverified** in the render manifest.

The synthetic tests cover FPS invariance at matched timestamps, no archive dependency, source-index preservation, invalid PNG/CLUT hashes, tampered events, manifest corruption, output collisions, warnings for unrendered events and CLI failure codes.

A separate optional private test can reconstruct the user's fingerprinted original DOS VGA room-23 bundle and assert exactly 120 30-fps frames, 240 60-fps frames, two omitted event states at 30 fps and none at 60 fps. This is skipped in public CI.

## Limitations and next direction

The current command renders **PNG frames from a saved event bundle**, not a GIF directly. A later adapter may use the same saved patches for GIF/WebP, with variable segment durations and explicit loop policy.

Actual ScummVM timer/event tracing, object-state changes, depth/foreground masks, actors and other environmental animation mechanisms remain outstanding. Room 23's water shimmer is well supported; comprehensive scene reconstruction is not.

**P4 completion is not claimed.**
