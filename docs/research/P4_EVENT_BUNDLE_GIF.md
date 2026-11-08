# P4 — Event-bundle GIF preview (event-driven, not FPS-sampled)

**Status:** Implemented on `feature/p4-event-bundle-gif`. Tested with synthetic/controlled palettes; independent replay on the user's Windows Room 23 event bundle remains a local integration check. No real ScummVM engine-state trace has been obtained.

## Why this exporter exists

The earlier `render-events` command writes a 60-fps indexed PNG sequence, sampling a synthetic palette-event bundle at fixed output times. A low-FPS sample can miss brief intermediate states even when the event log preserves them.

`render-event-gif` instead reads the **saved palette event boundaries** directly. It never opens the original game archive, simulates SCUMM cycle updates again, or assumes that 240 PNG frames are independently changing.

The pipeline is:

1. Read `timeline.json`, the original indexed PNG and the original RGB CLUT from an existing bundle.
2. Verify source sidecar checksums and every saved palette before/after hash using the existing event-replay validator.
3. Apply the **already validated saved RGB patches** at their modeled counter ticks. This does not rerun the cycle simulator.
4. Collapse only consecutive events producing the same RGB values at **source-used palette indices**. Preserve non-consecutive repeated states as separate timed GIF frames. Hidden palette-only events remain in the original event bundle.
5. Quantize **absolute** event boundaries to GIF's 10-millisecond units; refuse a visible segment that becomes zero length rather than silently omit it.
6. Use the existing Pillow-backed GIF encoder and read back every GIF frame to verify its RGB pixels and duration.
7. Save a play-once GIF and adjacent JSON manifest with provenance, event/visual segment counts, modeled durations, diagnostics and explicit uncertainty flags.

GIF is a convenience preview. The indexed room image, original CLUT and full event timeline remain authoritative source artifacts.

## Windows command for the existing Room 23 bundle

```powershell
Push-Location "C:\Users\87otl\ScummBucket"
git status --short
git fetch origin
git switch feature/p4-event-bundle-gif
git pull --ff-only origin feature/p4-event-bundle-gif
python -m pip install -e ".[gif]"

$bundle = "C:\Users\87otl\ScummBucket\exports\room23-events-20261108-143724"
$stamp = Get-Date -Format "yyyyMMdd-HHmmss"
$out = "C:\Users\87otl\ScummBucket\exports\room23-event-preview-$stamp.gif"
python -m scummbucket render-event-gif "$bundle" --output "$out"

Pop-Location
Invoke-Item "$out"
```

The command creates `room23-event-preview-<timestamp>.gif` and `room23-event-preview-<timestamp>.manifest.json`; it refuses to overwrite existing outputs. `--json` prints the full result.

Unlike `render-events`, this command **does not accept an FPS**. Its boundaries are already present in the modeled event bundle. It writes one GIF segment per consecutive *visible* state, with each segment's duration taken from the model's source counter units. The assumed 60 counter units per second in this particular bundle was calibrated against video, **not** verified against actual ScummVM timer values.

## Accuracy, caveats and diagnostics

- GIF delays are stored in 10-ms units. Boundary rounding preserves total modeled duration but may adjust individual durations by a few milliseconds.
- States shorter than 20 ms produce a `GIF_SHORT_FRAME_DELAY` warning: viewers may clamp them. Zero-duration states fail with `EVENT_GIF_ZERO_DURATION`; they are never silently discarded.
- A nonvisual palette update does not get an extra GIF frame. The event remains intact in the source JSON.
- The encoder intentionally omits loop extensions. Loop seamlessness has **not** been established.
- Actors, objects, masks, script-controlled effects and foreground composition are not reconstructed by this GIF.
- Any inherited archive warnings (including source-wide unknown `CYCL` flags outside room 23) are retained in the GIF manifest.
- The output and manifest are non-overwriting. If the GIF is written but the manifest write fails, the operation is reported as **partial**.
- The encoder requires optional Pillow support: `python -m pip install -e ".[gif]"`.

## Verification

Synthetic regression tests in `tests/test_palette_event_gif.py` cover event-boundary timing, non-consecutive repeat states, no missed intermediate events compared with 1-fps sampling, no original archive dependency, read-back GIF frame/duration integrity, corrupt source and event detection, output collision, inherited warnings, and CLI exit behavior.

A separate controlled local smoke test used the uploaded Room 23 initial indexed image with two synthetic color-pair swaps and verified a three-segment, play-once 4-second GIF against full RGB readback. **That test is not a replay of the user's 19-event source timeline.**

The next private verification step is to run the Windows command above on the fingerprinted `room23-events-20261108-143724` folder, inspect the GIF and its manifest, and compare visible shimmer cadence with the earlier ScummVM VGA video. Final engine timing still requires a real timer/palette trace as described in `P4_RUNTIME_PALETTE_VERIFICATION.md`.

**P4 is not complete**. This export validates a presentation path for synthetic, source-backed palette changes, not full scene-reconstruction fidelity.
