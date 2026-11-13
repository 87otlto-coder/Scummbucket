# P4 — Second complete Room 23 trace: 256 normal-speed callbacks mislabeled as stress

**Observation date:** 2026-11-08. **Result:** A **valid, complete 256-sample Room 23 runtime palette capture** and exact phase-aware source CYCL replay, **not a 60-unit stress capture**.

## Files received

The user's Windows helper invocation was labeled `-Mode stress`, and they supplied four evidence files (kept private, not committed): the raw `room23-stress-20261108-223403-619.raw.log`, imported `.trace.json`, phase-aware `.phase-research.json`, and strict `.verify.json`.

- Raw hook log SHA-256: `5d9ee5d9a212a71a7446693a6c8a2cd51693c6343a3f906dd43fb9cc0f1e5f33`
- Original `MONKEY2.001` SHA-256: `ad045372e0d49626503bb50fca29a687ec8e01ef75d9b8bca702a366d143819e`
- Valid BEGIN, consecutive 256 SAMPLE records and **`SBP4|END|256|limit`**. Import succeeded.
- **All 256 timer pairs are `VAR_TIMER=6`, `VAR_TIMER_NEXT=6`.** There are **zero** observations at 60. The 256 samples span **25,498 ms**, with median interval **100 ms** and no clock discontinuities.
- Phase-aware source match: **256/256** cycled palettes and **256/256** complete palettes (with observed non-cycle baseline retained); **253/253** samples held out after 3 early calibration samples. Equivalent source-model phase starts at update **60**.
- Room 23 active cycle entries **176–191** only; stable runtime overrides outside that range: **1,2,3,6**.
- The **first 80 samples match the first 80 samples of the prior 180-sample normal capture byte-for-byte**; the BEGIN palettes match as well. This further corroborates normal-cycle replay, but does not establish any 60-unit effect.

## Why did strict verify-palette-trace return failed?

The existing strict verifier rejected its **source CLUT versus observed BEGIN** precondition with `TRACE_INITIAL_PALETTE_MISMATCH`, listing **1,2,3,6,180,181**. It therefore returned `result: null`; it **did not compute or report any per-sample error**. The four stable runtime overrides and initially cycled colors were already understood in the first live trace.

Do not interpret this as an actual palette-cycle disagreement. The separate phase-aware report recorded `status: success` and `model_comparison_status: matched`, with completion true.

## Why did the requested stress timing not occur?

The current PowerShell `-Mode stress` **does not alter the running ScummVM timer**; its role is instructions and output naming only. The earlier instructions asked the user to set `scumm_vars[19] 60` **before** calling `room 23`. ScummVM debugger `Cmd_Room` calls `startScene()`; `startScene()` invokes room exit/entry scripts and resets the room palette/cycle state. **A room-entry script may alter the timer setting**. This is a plausible cause for the 6/6 trace, but the actual cause is **not logged** and cannot be assigned with certainty; the timer command may alternatively not have been applied. The evidence establishes only that the final **live timer was 6/6 throughout**.

## Corrected next experiment

Use an updated `run_scummvm_palette_capture.ps1` (the existing V2 exe needs **no MSYS2 rebuild**):

1. From another room, enter `room 23`; it automatically leaves the debugger.
2. **Only after Room 23 is visibly active**, reopen the debugger with Ctrl+Alt+D, enter `scumm_vars[19] 60`, then query `scumm_vars[19]` and confirm it prints `60`. Type `continue`.
3. Allow **30–40 observable 60/60 callbacks** (typically 30–40 seconds). Earlier 6/6 samples before the override are acceptable and must be disclosed, not erased.
4. Reopen the debugger, enter `room 22`, let the game resume, and exit. This should emit `SBP4|END|N|room_exit`.
5. Upload the new raw log and `*.phase-research.json` report, including the actual timer-pair histogram.

The forensic analyzer now records **timer-pair distribution**, and the PowerShell runner flags **`CAPTURE_MODE_NOT_OBSERVED`** if `-Mode stress` produces no 60/60 samples. A filename or the desired `-Mode` flag is never considered evidence of scheduler behavior.

## Status

- **Confirmed:** Real full 256-callback normal-cadence capture; source CYCL state matches perfectly after bounded phase alignment.
- **Not confirmed:** Any actual 60-unit palette callback or missed rotation. Do not use the mislabeled trace to validate the 1-Hz model.
- **Still outstanding:** Complete visual room reconstruction including scripts, objects, layer masks, animation effects and rendering.

[First incomplete live trace](P4_ROOM23_FIRST_LIVE_PALETTE_TRACE.md) · [Phase-aware verifier](P4_ROOM23_PHASE_AWARE_VERIFICATION.md) · [Windows runbook](P4_WINDOWS_TRACE_RUNBOOK.md)
