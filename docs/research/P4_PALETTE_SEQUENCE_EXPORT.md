# P4 — Experimental native indexed-background animation export

> **Current workspace (2026-11-09):** Execute commands from `F:\Dev\SCUMMBUCKET\SOURCE\ScummBucket`; originals, generated assets and reports belong in `FIXTURE`, and third-party utilities in `TOOLS`. Historical discussion retains its original evidence paths and timestamps. See [workspace migration](../WORKSPACE_MIGRATION.md).


**Status:** PNG frame-sequence exporter implemented; **synthetic tests passed**. Original-game integration test added but not yet run in this environment. This does **not** meet the final P4 timing-fidelity exit criterion.

**Primary test scene:** Original DOS VGA Monkey Island 2, room 23 (Captain Dread's ship / peninsula), where source pixel locations and observed water shimmer have been correlated with eight `CYCL` records.

## Why the output is an indexed PNG sequence

SCUMM palette cycling modifies the *palette*, not the source pixel indices. A faithful export must preserve the native indexed background and rotate its RGB palette entries in each frame.

The new `palette-sequence` command writes PNG **color type 3** (indexed 8-bit) with a standard `PLTE` chunk. Each frame retains the **identical pixel-index buffer**. Only the palette changes according to the modeled cycle events. This avoids burning color changes into a new RGBA background on every frame and preserves the original mechanism at the asset level.

The default sample is **320 × 144 native pixels** for room 23. There are no scanlines, CRT shaders, EGA conversion, stretching or HD scalers in this low-level export.

## Reproduce on Windows

From the existing local checkout and authorized original MI2 archive:

```powershell
cd "F:\Dev\SCUMMBUCKET\SOURCE\ScummBucket"
git pull --ff-only origin feature/p1-scumm-v5-inventory

$stamp = Get-Date -Format "yyyyMMdd-HHmmss"
$out = "F:\Dev\SCUMMBUCKET\FIXTURE\OUTPUT\room23-sequence-$stamp"

python -m scummbucket palette-sequence "D:\old" --room 23 --fps 30 --duration-seconds 4 --counter-rate 60 --output-dir "$out"

explorer.exe "$out"
```

Expected output if the fingerprinted archive passes the optional private integration test:

- **120** `room-023_frame-0000.png` through `room-023_frame-0119.png` (30 fps × 4 seconds).
- **One** `room-023_source-indexed.png`, with the unchanged original index buffer and initial palette.
- **One** `room-023_initial-clut.rgb` containing the source `CLUT` RGB triplets (768 bytes).
- **One** `manifest.json` with original source hash, room chunk offsets, image dimensions, source-index SHA-256, initial palette SHA-256, individual file/frame SHA-256, explicit counter totals and per-frame rotation events.

PNG frames are individual lossless files, **not an animated WebP or APNG file**. For playback, import them as an image sequence into a viewer/editor and set its rate to 30 fps. Do not infer a seamless loop: no exact loop point has been established. **No external image processing tool is required to export the frames.**

## How timing is modeled

The `--counter-rate 60` default is **derived from the user's 2026-11-08 room-23 VGA video**, where eight palette pairs visibly swap at intervals consistent with ScummVM's source-defined cycle delays divided by approximately 60 effective counter units/second.

At a frame index `i` and output rate `fps`, the exporter uses:

`cumulative_counter(i) = floor(i * counter_rate / fps)`.

It advances each palette cycle **once per exported frame after frame zero**, using the difference between successive cumulative counters. The engine-like update uses `max(VAR_TIMER, VAR_TIMER_NEXT)` semantics *only in the sense that its input is an already chosen counter increment*; the exporter has **not observed those two real engine variables**.

For the recommended 30 fps / 60-unit configuration, the synthetic increment is 2 counter units per frame. For room 23's original delays, this first produces a cycle-5 rotation at frame **18** (0.6 seconds) and a cycle-1 rotation at frame **36** (1.2 seconds), consistent with the observed video's approximate medians.

**Important limitation:** The actual engine may call `cyclePalette()` on a different schedule and scripts can alter the palette, cycles or timers. This model uses one update per output frame and cannot guarantee exact sub-frame timing or engine-level event ordering. The output manifest explicitly labels the timing `video_calibrated_60_units_per_second_hypothesis` only for the known fingerprinted room-23 archive and this exact 60-unit setting. Other settings/rooms remain cross-room or user-chosen hypotheses.

## Coverage and error reporting

- Room input must pass source inspection and SHA-256 revalidation.
- The room must have at least one `CYCL` record and a supported native `RMIM > IM00 > SMAP` indexed-background decode.
- Unsupported source formats, zero/invalid rate, malformed offsets, missing room, unsupported codecs, invalid parameter ranges, output collisions or failed writes yield explicit diagnostic codes and nonzero CLI exit status.
- The exporter limits a single operation to **240 frames**, with output FPS 1–60, duration 1–20 whole seconds and counter rate 1–600 units/second. The 240-frame cap applies first.
- Zero palette rotations during the selected interval and a visually unchanged palette series produce **warnings**, not an invented animation claim.
- Outputs are exclusively created and SHA-256-verified. Existing output files are not overwritten. A partially successful operation is reported `partial`, including the names/hashes of files actually written; original source files are never modified.
- The original inspector's four `CYCLE_FLAGS_UNVERIFIED` warnings and room-64 `CYCLE_DELAY_ZERO_IN_ENGINE` warning remain visible; they are **archive-wide**, not room-23 export failures.
- **PNG is palette-only:** no Guybrush, object layers, foreground masks, scripted lighting, water object alternatives, sound or full scene composite is included.
- EGA and shader conversion are intentionally deferred. The initial VGA source is the authoritative pixel reference.

## Verification status and tests

| Evidence level | Current status |
| --- | --- |
| Original room 23 has eight source `CYCL` pairs and 480 cycle-affected background pixels | **Directly verified from original game** |
| Video shows palette alternation spatially aligned with source CYCL pixels | **Observed and correlated** |
| Video-derived ~60 counter units/sec agrees with source cycle delays | **Strong provisional cadence evidence** |
| Indexed PNG frame encoding preserves the exact pixel indices | **Synthetic automated tests passed** |
| Modeled timeline and palette rotation event counts | **Synthetic automated tests passed** |
| Actual 120-frame export against user's fingerprinted original game via this new CLI | **Private integration test pending on user's machine** |
| Independent ScummVM engine timer/CLUT trace and exact playback timing | **Not yet verified** |
| Pixel-perfect reference rendering of complete room including objects and masks | **Not yet verified** |

The opt-in private regression in `tests/test_private_palette_probe.py` now checks that the original archive produces 120 frames, eight cycles, 480 covered pixels, valid native dimensions and the expected first model rotation at frames 18 and 36. It skips in public CI unless the `SCUMMBUCKET_MI2_ARCHIVE` environment variable is set to the authorized game archive or directory.

To run the complete original-archive tests locally:

```powershell
$env:SCUMMBUCKET_MI2_ARCHIVE = "D:\old"
python -m unittest discover -s tests -v
Remove-Item Env:\SCUMMBUCKET_MI2_ARCHIVE
```

The separate external `descumm` test additionally requires `SCUMMBUCKET_DESCUMM`, but **is not needed for this palette-sequence export**.

Public GitHub Actions: **153 tests discovered, 149 passed, 4 optional private-input tests skipped, 0 failed**. All tests are synthetic, metadata checks or mocked external calls in public CI; they contain no commercial artwork. The local environment in this review could not clone the GitHub checkout to run the new private regression, so no real-archive test is claimed for this new command yet.

## Next acceptance step

Run the 120-frame export on Windows; verify status, pixel/state metadata, and frame visibility. Compare its frame-to-frame pixel/palette changes to the room-23 VGA recording and determine where the provisional one-update-per-output-frame model diverges. A real ScummVM palette/timer trace remains the decisive independent timing cross-check.

This is a first **reconstructed palette-driven background sequence** with provenance and explicit timing limitations. **P4 remains incomplete.**

References:
- [Room 23 original-source/video spatial and cadence evidence](P4_ROOM23_VGA_SPATIAL_VALIDATION.md)
- [Original palette cycle candidate and anomalies](P4_PALETTE_CYCLE_CANDIDATES.md)
- [Exact runtime timer/palette trace contract](P4_RUNTIME_PALETTE_VERIFICATION.md)
