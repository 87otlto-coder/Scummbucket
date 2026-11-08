# P4 — Frame-rate-independent palette-event bundle

**Status:** Implemented, synthetic tests passed. Original DOS MI2 integration check is opt-in and pending. This is a HYPOTHETICAL palette update schedule, not a real engine-state trace.

## Why this is different

The existing PNG sequence and GIF preview call the modeled palette updater once per output frame. Their animation result can therefore change when output FPS changes.

The new palette-events command is a separate experiment: it calls the palette model once **per hypothetical counter unit**, records exact model-event positions, and can subsequently sample those saved events at 15, 30, 60 or other output FPS values. The stored sequence of events is now independent of the playback FPS.

**Do not conflate these schedules.** Real ScummVM can advance palette counters by variable timer increments and scripts can change rates or colors. The per-unit callback model is an explicit research assumption. The existing PNG/GIF commands were not silently migrated; they preserve their previous timing behavior.

## Windows command

From any PowerShell location:

    Push-Location "C:\Users\87otl\ScummBucket"
    git pull --ff-only origin feature/p1-scumm-v5-inventory

    $stamp = Get-Date -Format "yyyyMMdd-HHmmss"
    $out = "C:\Users\87otl\ScummBucket\exports\room23-events-$stamp"
    python -m scummbucket palette-events "D:\old" --room 23 --counter-rate 60 --duration-seconds 4 --output-dir "$out"

    Pop-Location
    explorer.exe "$out"

No Pillow install is needed for this command.

## Output bundle

- room-023_indexed.png: source-native indexed room bitmap and original palette, unchanged, saved once.
- room-023_initial-clut.rgb: 768-byte original source CLUT, saved separately.
- timeline.json: source SHA-256, exact room offsets and indexed-pixel fingerprints, original cycle definitions and derived delays, ordered counter-unit events, all modeled cycle rotations, RGB before/after color patches, per-event palette hashes, source-pixel coverage, uncertainties and diagnostic records.

The first two files preserve the original visual information. The event log contains the palette changes needed for replay without running SCUMM cycling again. GIF or PNG rendering becomes a separate, downstream concern.

### Event model and duration

For room 23 with 60 assumed counter units/second and a four-second window, the model performs updates at counter ticks **1 through 239** (239 modeled calls). The time interval is half-open: 0 seconds is included, but 4 seconds is excluded.

Each tick with any palette rotation records:
- Exact rational model time: counter_tick / assumed_counter_rate.
- All cycle IDs, source palette ranges and directions rotating at that tick.
- RGB entries that changed, their previous RGB values and their new values, plus full-palette SHA-256 before and after the tick.
- Number of native background pixels referencing changed palette entries.
- Whether the update was actually observed in the engine (currently false).

Simultaneous cycle rotations are grouped under the same counter tick. A rotation is not discarded just because all its resulting RGB values are unchanged or the affected palette indices are unused by the background.

## Replaying and verifying

The separate replay_event_palettes function consumes the saved initial CLUT and RGB event patches, rather than rerunning the palette-cycle simulation. It validates ordered event timestamps, patch indices, previous RGB values and before/after SHA-256 at each event. It checks all recorded events, including those after the last output frame at low output FPS, so corruption cannot be hidden by undersampling.

For an output sample at frame i and FPS f, the replay uses the latest model event at or before integer counter position floor(i * counter_rate / f). At matching wall-clock sample points, 15-fps, 30-fps and 60-fps renderers therefore recover the same modeled palette.

These checks establish **model consistency**, not real ScummVM execution timing.

Synthetic regressions validate recurrent palette states, hidden palette events, exact native pixels, source read-only behavior, collision refusals, invalid inputs, and corrupted events. The optional private MI2 regression expects the fingerprinted room-23 background to have eight cycle definitions, 480 covered source pixels and **32 modeled rotations** in this four-second window; it is skipped in public CI.

## Important limitations

1. One palette update per counter unit is hypothetical, not a demonstrated ScummVM scheduler.
2. The approximately 60 counter units/sec estimate comes from the supplied VGA video, not instrumented timer variables.
3. The event model and existing frame-sampled PNG/GIF exports may differ by a sample interval. This difference is deliberate and recorded, not silently reconciled.
4. Actors, room objects, foreground masks, script-controlled lights, fades, scrolling and music are not reconstructed by this palette-only event exporter.
5. No seamless loop or full-scene reference-pixel fidelity has been verified.
6. Malformed, absent and anomalous resources remain visible as diagnostic errors or warnings. Partial writes remain labeled partial and existing outputs are never overwritten.

**Next milestone:** Capture real palette/VAR_TIMER updates in ScummVM and compare them against the source-derived event schedules. Only then can we promote a verified timing model to the shared renderer.

Further evidence: [room 23 VGA study](P4_ROOM23_VGA_SPATIAL_VALIDATION.md), [native PNG sequence](P4_PALETTE_SEQUENCE_EXPORT.md), [nonlooping GIF preview](P4_PALETTE_GIF_PREVIEW.md), and [runtime trace contract](P4_RUNTIME_PALETTE_VERIFICATION.md).

**P4 remains incomplete.**
