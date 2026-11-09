# P4 — Room 23: controlled scheduler sweep (1, 6, 12) and diagnostic stress test (60)

**Date:** 2026-11-08. **Status:** User confirmed the standard ScummVM debugger's scheduler override at 1, 6 and 12 units per update; 5/10/60-Hz **synthetic** Room 23 states independently cross-checked using private exported inputs. **An authenticated live palette trace remains outstanding.**

## Observation versus reconstruction

The user previously supplied explicit debugger output where `VAR_TIMER_NEXT` (`scumm_vars[19]`) was changed from 6 to 1. After `continue`, `scumm_vars[19] = 1` and `scumm_vars[46] = 1` (`VAR_TIMER`). Subsequent confirmation that the 12-unit test worked was verbal; no copied 12/12 command transcript or measured wall-clock cadence was supplied. Treat this as **user-reported confirmation**, not independently collected machine output. See [debugger investigation](P4_SCUMMVM_DEBUGGER_COUNTDOWN_INVESTIGATION.md).

For the original DOS v5 engine, `waitForTimer(delta * 4)` with a ~240 quarter-frame-unit/sec timer makes a `VAR_TIMER_NEXT` of 1, 6, 12 correspond to approximately 60, 10, 5 SCUMM update calls/sec respectively, **when fast mode is off and the variable persists**.

Room 23's eight raw CYCL delay thresholds are (by cycle ID):

```text
cycle:     1   2    3   4   5   6   7   8
delay:    71  53  107  42  35  42  71  53  counter units
```

Their smallest delay is 35. Thus increments 1, 6 and 12 cannot cross more than one threshold in a call, regardless of phase or counter remainder, assuming source cycles remain active. As a result, the pure cycle model must agree at common cumulative-counter boundaries. The number of *separate visible states* between those boundaries depends on update cadence.

## Independently checked 4-second preview metrics

Private input: original 320×144 indexed Room 23 PNG, indexed pixels SHA-256 `94b7b2d675778bf73c73a87eca05ab74dca470ad67555faecd03ab112acbcd9f`, original 768-byte CLUT SHA-256 `44a542ed57e641676623a0d48c5a28a7b8d47e87482acb5af21a4a2eef65d242`. Verified source-file SHA-256 on prior original archive study: `ad045372e0d49626503bb50fca29a687ec8e01ef75d9b8bca702a366d143819e`.

| Model update delta | Nominal update rate | Four-second source sample frames | Output GIF segments | Unique decoded RGB images | Modeled cycle rotations |
|---|---:|---:|---:|---:|---:|
| 1 | 60 Hz | 240 (the prior event-driven reference records intermediate event boundaries rather than 240 GIF frames) | 20 | 17 | 32 |
| 6 | 10 Hz | 40 | 14 | 13 | 32 |
| 12 | 5 Hz | 20 | 12 | 12 | 32 |

**Caveat:** The 60-Hz column records the earlier synthetic event-bundle GIF with 20 collapsed palette-event segments. The 10-Hz column records the earlier user-generated `palette-gif` output. The 5-Hz column records an independently built research preview using the same indexed PNG and source CYCL timing rules (not the `scummbucket` CLI), decoding and verifying every GIF frame's RGB and duration after writing.

- 5-Hz synthesized preview SHA-256: `97bd5aacb4f5ecac6a98ba5894837f70596b3fc417799e9e4870af0c1851bd96`, 365,532 bytes, 320×144, 4,000 ms, nonlooping, 12 segments with durations (ms) `[600,200,200,200,200,400,400,200,400,200,600,400]`.
- The 5-Hz preview is **pixel-identical to both previously uploaded GIFs at all 20 common 200-ms time points**: t = 0, 0.2, …, 3.8 sec.
- Exactly 480 spatial pixel positions change relative to the original Room 23 indexed RGB background across the 5-Hz preview, all at source indices 176–191; none outside this source palette-cycle region change.
- Prior source-derived recordings at 60/10 Hz similarly affect exactly those 480 positions. The difference in encoded GIF byte sizes is not a measure of fidelity; the independent 5-Hz GIF used a different Pillow encoding configuration.

**Interpretation:** All three update rates deliver the same source-defined palette-cycle phases at shared counter values **under an unmodified-cycle, zero-initial-counter model**. The 5-Hz display omits states between 200-ms boundaries; 10-Hz omits some states between 100-ms boundaries; the 1-unit event timeline preserves intermediate modeled states. No direct observation of every engine palette callback or initial room-entry phase exists yet.

## Controlled next experiment: cross the per-callback threshold

Source `ScummEngine::cyclePalette()` increments a cycle counter by `max(VAR_TIMER,VAR_TIMER_NEXT)`, takes modulo `delay` on crossing, but executes **at most one** actual palette rotation for each cycle per invocation. This behavior can make scheduler changes alter the **total rotations**, not just visibility.

A deliberate `VAR_TIMER_NEXT = 60` test sets the nominal rate to **one update/sec**. This exceeds delays 35, 42 and 53. The source-defined four-second synthetic replay predicts **28 rotations** after four complete 60-unit callbacks, whereas 1-, 6- or 12-unit update schedules predict **32 rotations** at the same cumulative 240 counter units. Per-cycle modeled counts:

```text
cycle:              1  2  3  4  5  6  7  8   total
1/6/12 units:       3  4  2  5  6  5  3  4     32
60 units:           3  4  2  4  4  4  3  4     28
```

This is a **specific testable prediction**, not a claim that the actual observed engine animation has already dropped four rotations.

An independently encoded, 4-second **one-update/sec** private GIF was also constructed from the original indexed Room 23 PNG and source cycle metadata (Pillow RGB decoded-frame and 1,000-ms-delay round-trip verified). File: `room23-onehz-stress-preview-20261108.gif`, 121,854 bytes, SHA-256 `fa6510463a7bebc4f49d7b3a413f3b324b561c8892b02b6200ee871fa84a0caf`. Its four visible frames represent t=0,1,2,3 seconds; the t=4 check compares palette states after four full callbacks but is not an exported GIF frame.

With **identical zero-offset cycle baselines**, the synthetic 1-Hz palette differs from the 1-counter-unit model by exactly 0, 0, **65**, **124**, **124** native RGB pixel positions at t=0,1,2,3,4 seconds respectively. All those disagreements remain inside the source water-cycle region; they are **model disagreements**, not engine-captured screen differences. They demonstrate that once the update delta exceeds the shortest 35-unit delay, changing callback cadence can alter the accumulated palette rotation sequence, not merely shift the times intermediate states become visible. Normal game state may have nonzero initial cycle counter remainders, changed rates or game scripts.

From Room 23, in the **ScummVM debugger**:

```text
room
scumm_vars[19] 60
scumm_vars[19]
continue
```

Let the game run several seconds (it will appear very slow). Open the debugger manually and read:

```text
room
scumm_vars[19]
scumm_vars[46]
scumm_vars[47]
```

Then restore the normal observed setting:

```text
scumm_vars[19] 6
continue
```

Record whether `VAR_TIMER=60` and `VAR_TIMER_NEXT=60` persisted, and whether palette colors visibly update roughly once a second. More quantitative fidelity still requires the separately instrumented full-palette capture bridge. The test environment is disposable; original game archives remain read-only.

## Real-engine stress-test result (user debugger observations)

**Date:** 2026-11-08. **Status:** **Confirmed scheduler override and user-observed visual effect**, not a full palette trace.

The user ran the stress test in original DOS VGA MI2 Room 23:

```text
room                   => 23
scumm_vars[47]         => 208701
scumm_speed            => 0
scumm_vars[19] 60      => 60
continue
scumm_vars[19]         => 60
scumm_vars[46]         => 60
scumm_vars[47]         => 209067
scumm_speed            => 0
```

The user explicitly reported that **background animations became visibly more abrupt**. This is a first-person visual observation, not an RGB/palette-frame capture, and should not be silently upgraded to proof of the specific 28-versus-32 modeled rotation counts.

**Derived:** `VAR_TIMER_TOTAL` advanced by `209067 - 208701 = 366` units. The decomposition `366 = 6 + 6 × 60` is consistent with one already-selected six-unit loop followed by six 60-unit loops. That is a **source-supported reconstruction**, not a logged sequence of seven individual calls.

**Important mid-wait timer transition:** In [`scumm.cpp`](https://github.com/scummvm/scummvm/blob/v2026.4.0/engines/scumm/scumm.cpp), the loop reads `delta` from `VAR_TIMER_NEXT` **before** `waitForTimer(delta * 4)`. The debugger event is polled inside `waitForTimer()` via `parseEvents()`. Consequently, a debugger edit to `VAR_TIMER_NEXT=60` may happen *after a six-unit delta was latched*; once gameplay resumes, the next `scummLoop(6)` would add **6 units** to `VAR_TIMER_TOTAL` and set `VAR_TIMER=6`.

However, later in that *same* loop [`cyclePalette()`](https://github.com/scummvm/scummvm/blob/v2026.4.0/engines/scumm/palette.cpp) applies `max(VAR_TIMER,VAR_TIMER_NEXT)`: **max(6,60) = 60 palette units**. Thus the palette rotation may jump by 60 units even on a transitional engine update that advances cumulative game time by only 6. That can matter to live RGB palette reconstruction and means one must not infer the palette increment from the change in `VAR_TIMER_TOTAL` alone during a debugger intervention.

This transition is now covered by the **synthetic** `test_mid_wait_scheduler_override_uses_greater_palette_delta` regression in `tests/test_palette_trace.py`. That test checks the existing trace verifier handles timer pairs (6,60) and (60,60) with palette increments (60,60), without claiming the exact pair was instrumentally observed in this game session. The regression was committed; a fresh full test-suite run was not available during the remote edit.

**Conclusions:**
- Live `VAR_TIMER_NEXT=60` override persisted and `VAR_TIMER=60` was subsequently observed, with fast mode off.
- User observed visibly more abrupt background animation in Room 23.
- The source supports a concrete six-unit-to-sixty-unit handoff explanation for the +366 counter change, but callback count and actual palette phases remain inferred.
- Whether exactly four rotations were skipped in this specific run is **unverified**; game-phase, possible scripts and the handoff alter expectations.
- No proprietary game files, screenshots or captured palettes were added to the repository.

**Recommended next:** Run the already prepared pinned ScummVM palette-capture hook to log true ordered timer pairs and post-cycle RGB palettes. The regular debugger has now established scheduler controllability; repeatedly varying timing manually offers diminishing marginal evidence. Restore `scumm_vars[19] 6` to return to the earlier observed runtime configuration, if it has not already been restored.

## Reproduce the ordinary 5-Hz preview with ScummBucket

On Windows PowerShell from the active feature branch:

```powershell
cd "F:\Dev\SCUMMBUCKET\SOURCE\ScummBucket"
$stamp = Get-Date -Format "yyyyMMdd-HHmmss"
$out = "F:\Dev\SCUMMBUCKET\FIXTURE\OUTPUT\room23-fivehz-$stamp.gif"
python -m scummbucket palette-gif "F:\Dev\SCUMMBUCKET\FIXTURE\GAMES\MonkeyIsland2_DOS_VGA" --room 23 --fps 5 --duration-seconds 4 --counter-rate 60 --output "$out"
Invoke-Item "$out"
```

The ScummBucket encoder may produce a different binary SHA-256 than the independent research GIF but should produce the same decoded RGB states and frame durations, if both paths faithfully implement the same source palette rules. Do not overwrite prior artifacts.

## References

- [Six-unit GIF and event-model comparison](P4_ROOM23_SIX_UNIT_COMPARISON.md)
- [Runtime debugger observations and experiment](P4_SCUMMVM_DEBUGGER_COUNTDOWN_INVESTIGATION.md)
- [Optional ScummVM engine palette capture bridge](P4_SCUMMVM_ENGINE_TRACE_CAPTURE.md)
- [ScummVM pinned SCUMM palette cycling](https://github.com/scummvm/scummvm/blob/v2026.4.0/engines/scumm/palette.cpp)
- [ScummVM pinned SCUMM update scheduler](https://github.com/scummvm/scummvm/blob/v2026.4.0/engines/scumm/scumm.cpp)
