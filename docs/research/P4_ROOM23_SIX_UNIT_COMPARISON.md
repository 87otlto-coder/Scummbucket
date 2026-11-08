# P4 — Room 23: six-unit callback comparison to event-bundle GIF

**Verification date:** 2026-11-08. **Status:** Independent file-integrity, decoded-RGB and timeline comparison passed. **Classification:** Synthetic model cross-check using runtime-observed scalar timer values, **not** an instrumented ScummVM palette-state verification.

## Evidence and provenance

The user read the following values in the ordinary ScummVM debugger while in room 23: `scumm_vars[46] = 6` (`VAR_TIMER`), `scumm_vars[19] = 6` (`VAR_TIMER_NEXT`), and `VAR_TIMER_TOTAL` observations 51,900, 52,314 and 52,620. The increments of 414 and 306 are multiples of 6. [Original observations](P4_ROOM23_DEBUGGER_TIMING_OBSERVATIONS.md).

The original DOS VGA `MONKEY2.001` source fingerprint declared in the new output is `ad045372e0d49626503bb50fca29a687ec8e01ef75d9b8bca702a366d143819e`; background indexed pixels have SHA-256 `94b7b2d675778bf73c73a87eca05ab74dca470ad67555faecd03ab112acbcd9f` and room CLUT SHA-256 `44a542ed57e641676623a0d48c5a28a7b8d47e87482acb5af21a4a2eef65d242`. Original game archives were not modified by this analysis.

The compared user-provided private files (not committed):

| Artifact | Size | SHA-256 |
|---|---:|---|
| `room23-event-preview-20261108-151952.gif` | 278,734 bytes | `1a654c4ed3575ccca020d00566be0baab1bfade51d0c1439e144d7e91b516f95` |
| `room23-sixunit-preview-20261108-161024.gif` | 219,034 bytes | `c93407c5e95114849daf3faf12077393f5ae6680f3093f9aa5bd0a3c69262d03` |

Both GIF hashes were independently checked against the files, and the six-unit hash matches its manifest. The earlier GIF has a separate [verification report](P4_ROOM23_EVENT_GIF_VERIFICATION.md).

## Model distinction

- **Event-bundle GIF:** `render-event-gif` replays modeled palette patches at 1-counter-unit event boundaries, with a nominal 60-unit/sec timebase. This is an event-resolved synthetic reference; not sampled to an engine-call schedule.
- **Six-unit GIF:** `palette-gif "D:\old\mi2" --room 23 --fps 10 --duration-seconds 4 --counter-rate 60` models exactly one `cyclePalette`-like update of 6 units at each of 10 sampled callbacks/sec, except that the initial sample at time zero is unchanged. This is the independently video-calibrated frame-coupled exporter and **is not a render of the earlier saved event bundle**.

ScummVM source increments palette-cycle counters by `max(VAR_TIMER, VAR_TIMER_NEXT)`, and performs **at most one rotation per cycle per callback** when a delay threshold is reached. The repeated debugger readings make six units a plausible steady-state delta, but the debugger does not record all intermediate calls, initial cycle-counter phase, script modifications or actual RGB palette arrays.

## Independent result

| Metric | Event-bundle GIF | Six-unit GIF |
|---|---:|---:|
| Native dimensions | 320 × 144 | 320 × 144 |
| Nominal duration | 4,000 ms | 4,000 ms |
| GIF segments | 20 | 14 |
| Unique decoded RGB images | 17 | 13 |
| Modeled cycle rotations | 32 | 32 |
| Source-sampled frames | Event-driven | 40 at 10 FPS |
| Short 10-ms segments | 2 | 0 |
| Visually changed source pixels across all segments | 480 | 480 |
| Changed pixels outside Room 23's cycling colors (source palette indices 176–191) | 0 | 0 |
| Seamless loop verified | No | No |
| Exact runtime clock / palette verified | No | No |

- Each of the **14 decoded RGB states** in the six-unit GIF appears in the **20-segment** event-driven GIF, in consistent sequence. Its nearest original-segment matches by zero-based index are `[0,1,2,3,5,6,9,10,12,13,14,15,13,19]`. Nonconsecutive RGB states can repeat.
- Four distinct RGB images in the 17-state event-driven collection do **not** appear in the 13-state six-unit collection. There are **no new** six-unit RGB images absent from the earlier event-driven collection.
- At **all 40 times** `t = n × 100 ms`, `n = 0..39`, the GIFs decode to **pixel-identical RGB frames** (zero differing pixels at every matched timestamp). Their state-transition times *between* those comparison points differ as expected.
- The six-unit GIF has 14 segment durations, in ms: `600, 100, 200, 300, 200, 400, 300, 300, 300, 100, 200, 500, 100, 400`. Sum = `4,000`; all decoded GIF delays match the manifest exactly.
- Six-unit segment start counter units: `0, 36, 42, 54, 72, 84, 108, 126, 144, 162, 168, 180, 210, 216`. They are multiples of 6, as expected under this model.
- The spatial union of changing pixels is exactly 480 positions bounded by x=0..319, y=52..123. All 480 are in the Room 23 CYCL source indexed-color range; none outside are altered.

### Interpretation

The newer GIF is consistent with the prior synthetic reconstruction *on the observed six-unit timing hypothesis*. It removes short-lived intermediate visual combinations without modifying the palette values of retained states. This materially improves the plausibility of the **update-call scheduling hypothesis** but does **not** prove actual 10-Hz callback cadence, engine-derived initial phase or accurate animation against naturally entered gameplay.

The earlier 20-segment version remains the event-resolved regression; the new 14-segment version is a **candidate engine-cadence presentation regression**. Do not rewrite the first artifact's timing metadata or claim that either version is fully runtime-verified.

### Reproducibility test

The optional `tests/test_private_room23_cadence_compare.py` runs entirely against the two existing user-generated GIFs and adjacent manifests. It requires Pillow, compares file hashes and decoded RGB states, verifies 40 matching 100-ms samples, and checks the 480-pixel spatial union. It does **not** require proprietary game archives. Public CI skips when either private path is absent.

On Windows PowerShell, set both variables to the exact existing files, then invoke the test:

```powershell
$env:SCUMMBUCKET_ROOM23_EVENT_GIF = "C:\Users\87otl\ScummBucket\exports\room23-event-preview-20261108-151952.gif"
$env:SCUMMBUCKET_ROOM23_SIXUNIT_GIF = "C:\Users\87otl\ScummBucket\exports\room23-sixunit-preview-20261108-161024.gif"
python -m unittest discover -s tests -p "test_private_room23_cadence_compare.py" -v
Remove-Item Env:SCUMMBUCKET_ROOM23_EVENT_GIF
Remove-Item Env:SCUMMBUCKET_ROOM23_SIXUNIT_GIF
```

Locally, this test passed once with both supplied files and was confirmed skipped when no private-file environment variables were present. It remains a **synthetic animation-model comparison test**, never a substitute for actual ScummVM palette trace evidence.

### Remaining tasks

1. Use a build-instrumented ScummVM `cyclePalette()` capture to record every `VAR_TIMER`, `VAR_TIMER_NEXT` and post-cycle RGB palette for consecutive callbacks; existing [capture bridge](P4_SCUMMVM_ENGINE_TRACE_CAPTURE.md) targets this.
2. Compare actual callbacks and their palettes with `verify-palette-trace`, noting any startup phase differences and script effects. Report failures as failures.
3. Independently compare captured visual cadence with the original VGA gameplay reference while controlling for actors, object layers, camera and aspect correction.

Only the source hash and derived measurements are recorded here. No original game images or commercial archives are in source control.
