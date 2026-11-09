# Room 23 — standard ScummVM debugger timer observations (2026-11-08)

> **Current workspace (2026-11-09):** Execute commands from `F:\Dev\SCUMMBUCKET\SOURCE\ScummBucket`; originals, generated assets and reports belong in `FIXTURE`, and third-party utilities in `TOOLS`. Historical discussion retains its original evidence paths and timestamps. See [workspace migration](../WORKSPACE_MIGRATION.md).


## Evidence scope

User-provided manual readings from a standard ScummVM debugger while running **Monkey Island 2, original DOS VGA**, room 23. These are **live scalar-variable observations**, not instrumented per-callback palette captures. The source archive edition is independently known to match the Room 23 study; the debugger observations themselves contain no self-authenticating game fingerprint.

The following commands were entered in ScummVM's debugger (not Windows PowerShell):

```text
room
scumm_roomresource
scumm_vars[46]
scumm_vars[19]
scumm_vars[47]
continue
```

ScummVM `v2026.4.0` reference: in `engines/scumm/vars.cpp`, SCUMM v5 initializes `VAR_TIMER=46`, `VAR_TIMER_NEXT=19`, `VAR_TIMER_TOTAL=47`. In `scumm.cpp`, `scummLoop(delta)` sets `VAR_TIMER=delta` and adds `delta` to `VAR_TIMER_TOTAL`; `palette.cpp` `cyclePalette()` uses `max(VAR_TIMER, VAR_TIMER_NEXT)`. The debugger exposes `scumm_vars[N]` through its registered integer variable array. Source revision: `scummvm/scummvm@v2026.4.0`, inspected 2026-11-08.

## Observations

| Sample | Room | Room resource | VAR_TIMER (46) | VAR_TIMER_NEXT (19) | VAR_TIMER_TOTAL (47) |
|---|---:|---:|---:|---:|---:|
| First | 23 | 23 | 6 | 6 | 51,900 |
| Second | 23 | 23 | 6 | 6 | 52,314 |
| Third | 23 | 23 | 6 | 6 | 52,620 |

The total increments are **414** and **306** counter units, exact multiples of 6 (69 and 51). From first to third, the counter increased **720 units**, equivalent to **12 s at a 60-unit/sec timebase**. The observations are consistent with an effective palette counter increment of 6 per call, or about **10 calls/sec** at the nominal 60-unit/sec rate. Individual updates could have varied between the sampled observations: their exact count, monotonicity, jitter and palette values were **not directly logged**.

Do **not** label the observed 6/6 values as proof that the synthetic 1-unit-per-callback event bundle is engine faithful. The earlier 240-frame event-timed GIF may contain brief palettes that are absent at six-unit runtime update cadence because `cyclePalette()` rotates eligible cycles at most once per callback.

## Immediate controlled comparison

The existing `palette-gif` command uses the separate **frame-coupled** synthetic model, with `fps=10` and `counter_rate=60`: for each subsequent image sample, it simulates exactly one `advance_palette(..., delta=6)` call, preserving at-most-one-rotation-per-call semantics. This is **not the same model** as the event-bundle GIF. Output is explicitly hypothetical and does not assert the exact observed starting phase or effects of scripts.

On Windows, with a clean new output:

```powershell
$stamp = Get-Date -Format "yyyyMMdd-HHmmss"
$out = "F:\Dev\SCUMMBUCKET\FIXTURE\OUTPUT\room23-sixunit-preview-$stamp.gif"
python -m scummbucket palette-gif "F:\Dev\SCUMMBUCKET\FIXTURE\GAMES\MonkeyIsland2_DOS_VGA" --room 23 --fps 10 --duration-seconds 4 --counter-rate 60 --output "$out"
Invoke-Item "$out"
```

This yields a play-once 10-fps-source model preview with a provenance manifest. It need not have exactly ten unique visible states or a literal ten frames because consecutive visually identical samples are collapsed. Compare its shimmer cadence visually with the earlier standard ScummVM VGA recording. **A match cannot substitute for a continuous instrumented engine palette trace.**

## Acceptance limits and next evidence needed

1. The standard debugger reveals `VAR_TIMER`, `VAR_TIMER_NEXT` and accumulated `VAR_TIMER_TOTAL`, but not per-callback 768-byte palettes.
2. Repeat observations over other Room 23 game states and normal entry (debugger room-jump can differ from gameplay) to check timer variability.
3. Capture before/after 768-byte palette values **at the same precise point** with the guarded ScummVM instrumentation when feasible; compare observed sequence with the model. Only then distinguish confirmed runtime palette states, actual callback cadence and synthetic interpolation.
4. Preserve the current 20-segment Room 23 event-bundle GIF as the earlier synthetic-spatial regression; do not quietly replace its provenance or reinterpret its 19 event ticks as engine events.
