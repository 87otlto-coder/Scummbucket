# P4 — Experimental palette-driven GIF preview

> **Current workspace (2026-11-09):** Execute commands from `F:\Dev\SCUMMBUCKET\SOURCE\ScummBucket`; originals, generated assets and reports belong in `FIXTURE`, and third-party utilities in `TOOLS`. Historical discussion retains its original evidence paths and timestamps. See [workspace migration](../WORKSPACE_MIGRATION.md).


**Status:** Exporter implemented, unit-tested with synthetic assets. An **independent private-file research reconstruction** also produced a real source-backed GIF and verified its pixel/timing readback. The GitHub CLI's own original-game integration test is still **opt-in and pending on the user's Windows checkout**.  
**Scope:** Original DOS VGA Monkey Island 2 room palette cycling; first reference room 23.

## What it exports

The new command builds a **play-once animated GIF** from the same decoded room background and modeled palette state used by the existing indexed PNG-sequence exporter.

The original SCUMM background is a single palette-indexed bitmap. The engine animates selected regions by rotating RGB values in the room palette. ScummBucket therefore continues to treat **the original indexed source, CLUT, CYCL definitions, and time-stamped palette events** as authoritative. The GIF is a **convenient preview only**.

The exporter reuses the established, licence-compatible [Pillow](https://pillow.readthedocs.io/en/stable/handbook/image-file-formats.html#gif) encoder rather than implementing GIF LZW compression. Pillow is an **optional dependency**; non-GIF CLI commands remain standard-library based.

For the first example, a **30 fps, 4-second, 60-units/second** request samples 120 model frames. GIF merges **consecutive frames that render identically**, not all recurrences of the same palette state. For instance, A → B → A must remain three time segments even though there are only two globally unique appearances.

The comparison is based on RGB values at **palette indices actually used by the native background**. A rotation affecting unused palette entries is still recorded in the manifest's event timeline even if it does not create another visual GIF frame.

## Run on Windows

First update the current feature branch and install the optional GIF extra **once**:

```powershell
cd "F:\Dev\SCUMMBUCKET\SOURCE\ScummBucket"
git pull --ff-only origin feature/p1-scumm-v5-inventory
python -m pip install -e ".[gif]"
```

Then export the VGA source room's water shimmer to one GIF:

```powershell
$stamp = Get-Date -Format "yyyyMMdd-HHmmss"
$out = "F:\Dev\SCUMMBUCKET\FIXTURE\OUTPUT\room23-preview-$stamp.gif"
python -m scummbucket palette-gif "D:\old" --room 23 --fps 30 --duration-seconds 4 --counter-rate 60 --output "$out"
Start-Process "$out"
```

The output files are:

- `room23-preview-<timestamp>.gif`: a **nonlooping**, native 320 × 144, full-background animation preview with per-segment GIF delays.
- `room23-preview-<timestamp>.manifest.json`: source hashes, original palette and indexed-pixel fingerprints, original CYCL details, timing assumptions, all rotation events, all visual-state segments, output-file hash and diagnostics.

The exporter **does not** commit game assets, insert a logo, upscale, stretch, apply CRT scanlines, convert to EGA or rasterize actor/object sprites. The source ZIP/folder is read-only.

## Source timing model and GIF duration precision

The exporter delegates palette update calculations to the existing `simulate_frame_palettes()` method rather than independently implementing new SCUMM timing logic.

For a source sample at frame index `i`:

`modeled_counter_total(i) = floor(i * counter_rate / fps)`.

A single SCUMM-like palette-cycle update is performed for each modeled output frame after the initial frame. This is an explicit **sampling assumption** rather than a direct emulation of the engine scheduler.

- At 30 fps and 60 modeled counter units/second, each sampled output frame advances the source-derived counter by two units.
- For fingerprinted room 23 only, **60 counter units/second is a video-calibrated hypothesis** supported by eight observed water color-swap periods. It is not yet verified from `VAR_TIMER`, `VAR_TIMER_NEXT`, or a real engine `cyclePalette()` trace.
- GIF stores delays in hundredths of a second. Segment boundaries are quantized using **absolute time rounding** and their differences, preventing cumulative drift. Durations shorter than 20 ms receive a warning because some players clamp them.
- Each GIF frame is decoded back using Pillow to verify **exact RGB pixel reproduction** and exact stored durations against the modeled original indexed pixels and palette. A mismatch aborts the export with an error.
- There is **no loop extension**. We have not yet confirmed a seamless repeating endpoint, and a GIF viewer may stop on the last frame.

## Event timeline and manifest

The manifest contains:
- `summary.source_frames_sampled` and `summary.gif_frames_written`: different values because unchanged consecutive visual frames are folded into durations.
- `summary.unique_visual_states`: number of globally distinct appearances, which can be lower than the **number of GIF frame segments** if a state recurs later.
- `segments`: ordered GIF frame boundaries, source-frame spans, integer duration in milliseconds, original full-palette SHA-256 and rendered used-color SHA-256. Repeating nonadjacent states remain separate.
- `palette_events`: every modeled CYCL rotation, including those that affect palette indices not referenced by the background. Events carry sample frame/time fraction, counter total and increment, cycle ID/range/direction, affected original-pixel count and resulting palette hash.
- `source` and `cycles`: original resource SHA-256, chunk offsets, native geometry, index buffer SHA-256, initial RGB palette SHA-256, raw cycle data and derived counter thresholds. Runtime counters are not mistaken for immutable source definitions.
- `timing` and `fidelity`: explicit labels for video-calibrated hypothesis, lack of verified live timers, lack of loop validation, absence of mask/sprite compositing and round-trip GIF verification.
- `diagnostics` and `files`: severity/code/message, output digest and byte count. All original archive warnings remain visible.

**Important:** GIF encoders may reorder palette *indices* internally. The exporter validates the **rendered RGB pixels** against the native indexed model, but the **source indices and CLUT remain authoritative outside the GIF** (in the game archive, PNG sequence export and manifest). Do not treat the GIF's internal palette-index numbering as original SCUMM resource data.

## Guardrails and failures

- All output file names are **exclusive-create**, with preflight checks for the GIF and adjacent manifest. An existing file or symlink causes a failure; no overwrite.
- Incorrect game/room data, unsupported strip codecs, malformed RGB palettes, nonexistent Pillow, invalid output suffix, invalid FPS/duration/rate, corrupt source and encoder/readback mismatches are explicitly reported.
- GIF source sampling is limited to **240 frames** per export (e.g. four seconds at 60 fps), and the number of retained pixel samples is bounded to prevent excessive memory usage.
- No visible change produces a valid **single-frame GIF** with a warning, not a false animation claim. No palette events produces another warning.
- A manifest write failure after writing the verified GIF results in **partial** status; the GIF and its successful source hash remain reported. There is no claim of atomic multi-file commit.
- The four `CYCLE_FLAGS_UNVERIFIED` warnings and the distinct room-64 `CYCLE_DELAY_ZERO_IN_ENGINE` warning remain visible as archive-wide findings.
- Original room objects, costumes/actors, depth masks, scrolling, script-controlled lighting and other effects are excluded. This is a palette-only preview, **not** a full-scene renderer.

## Independent private original-game research result (2026-11-08)

A separate read-only research script processed the original user-supplied `MONKEY2.001` data without downloading additional game binaries or executing the new GitHub CLI. It reused the **same source-indexed background, original CLUT and CYCL definition values**, and independently simulated the four-second 30-fps/60-counter-unit sequence.

| Source/model property | Measured result |
| --- | ---: |
| Resource SHA-256 | `ad045372e0d49626503bb50fca29a687ec8e01ef75d9b8bca702a366d143819e` |
| Indexed background SHA-256 | `94b7b2d675778bf73c73a87eca05ab74dca470ad67555faecd03ab112acbcd9f` |
| Original room dimensions | **320 × 144** |
| Sampled playback frames | **120** |
| Time-ordered GIF segments | **18** |
| Globally unique visible palette states | **16** |
| Modeled CYCL rotation events | **32** |
| Preview duration | **4,000 ms** |
| GIF byte count | **261,439** |
| GIF SHA-256 | `9dd0fc97c583a0cba3ae6787427874344203f86921b2654fc06bbdec7e9e216b` |
| Pillow GIF readback | All **18** RGB frames and centisecond durations match the independently generated indexed-source model; no loop extension |

Two of the visual states recur later, explaining why 16 unique states produce **18 necessary playback segments**. No provenance is lost by collapsing only immediately repeated visible states.

**Scope distinction:** This confirms that the original **private game data** can produce a technically consistent 18-segment GIF under the agreed video-calibrated timing hypothesis. It is **not** evidence that the new `python -m scummbucket palette-gif` command itself has completed its opt-in private-archive integration check. The version-controlled private test has been strengthened to assert the exact **18 / 16 / 32** counts when run by the user.

The independently generated preview remains an artifact of this private conversation, **not a file in GitHub**. No game-derived pixels or archive chunks were committed.

## Verification status

| Verification | Result |
| --- | --- |
| Synthetic source and palette cycle coverage | Passed |
| Pure event timeline and consecutive-frame merge logic | Passed |
| GIF RGB roundtrip, ordered frames, durations, nonloop status | Passed via Pillow in CI |
| Missing encoder, unsupported input, overwrite and invalid timing handling | Passed |
| Original MI2 room-23 GIF and metadata regression | Private opt-in test added; not yet run |
| Actual ScummVM timer and palette trace | Outstanding |
| Full-scene, mask, actor and object compositing | Outstanding |
| Seamless looping and animated WebP | Not implemented |

Run the optional original-game regression from the local checkout after installing Pillow:

```powershell
$env:SCUMMBUCKET_MI2_ARCHIVE = "D:\old"
python -m unittest discover -s tests -v
Remove-Item Env:\SCUMMBUCKET_MI2_ARCHIVE
```

The separate optional `descumm` test still needs `SCUMMBUCKET_DESCUMM` if its integration test is to run; it is not required for GIF export.

**P4 remains incomplete.** The GIF demonstrates a reproducible, source-backed, video-calibrated palette reconstruction, not runtime-perfect, comprehensive background animation.

## Sources

- [Room-23 source/video pixel mapping and timing evidence](P4_ROOM23_VGA_SPATIAL_VALIDATION.md)
- [Native PNG sequence exporter and source-sidecar representation](P4_PALETTE_SEQUENCE_EXPORT.md)
- [ScummVM timer/palette trace validation procedure](P4_RUNTIME_PALETTE_VERIFICATION.md)
