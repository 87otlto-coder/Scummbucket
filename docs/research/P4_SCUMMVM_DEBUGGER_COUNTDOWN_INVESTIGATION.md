# P4 — Why ScummVM debugger `debug_countdown` does not step SCUMM frames

**Reviewed:** 2026-11-08 against ScummVM `v2026.4.0` (source inspection). **Scope:** Original DOS VGA Monkey Island 2, Room 23.

## Reported user behavior

- `debug_countdown 1` was accepted in the ScummVM console, but did not automatically reopen after `continue`.
- Repeated reads of `scumm_vars[47]` while remaining in the debugger were unchanged.
- Pushing the debugger experiment resulted in a crash. No stack trace or precise reproducer exists, so the **crash mechanism is unknown**; do not claim it is a known bug or assert an exact cause.

## Source-backed root explanation for failure to auto-reopen

- `gui/debugger.cpp`: constructor initializes `_frameCountdown=0` and registers `debug_countdown` as an editable integer variable. `Debugger::onFrame()` decrements a positive countdown and enters the console only when it reaches zero. `Debugger::attach()` **resets the countdown to 1**.
- `backends/events/default/default-events.cpp`: the `EVENT_DEBUGGER` event explicitly invokes `debugger->attach(); debugger->onFrame();` once. The keyboard shortcut is `Ctrl+Alt+D`. This immediate invocation is sufficient to reopen the console on user request but does not schedule a future debugger callback.
- `engines/scumm/scumm.cpp`: the running SCUMM game loop calls `waitForTimer(delta * 4)` then `scummLoop(delta)`, without calling debugger `onFrame()`. `engines/scumm/input.cpp`: input polling is delegated to the event manager; no periodic debugger `onFrame()` call exists on the inspected SCUMM path. `engines/scumm/debugger.cpp`: `ScummDebugger::onFrame()` forwards to base class, but is **not used as a step callback by the SCUMM main loop**.

**Finding:** The generic debugger supports a countdown *when its engine periodically calls `onFrame()`*. The reviewed SCUMM path does not appear to do this. As a result, `debug_countdown 1` is **not a functional single-frame stepping procedure for this ScummVM build**. Pressing the Open Debugger shortcut again itself resets the countdown to 1, masking any prior value.

The stalled `VAR_TIMER_TOTAL` while the console is open is expected: this is a modal debugger and SCUMM `scummLoop(delta)` is not running in parallel.

## Engine scheduling revealed by source

For DOS SCUMM v5 `setTimerAndShakeFrequency()` defines:

```text
PIT_BASE_FREQUENCY = 1193182.0
PIT_V5_6_ORCHESTRATOR_DIVISOR = 4096.0
PIT_V5_6_SUBTIMER_INC = 3433.0
PIT_V5_SUBTIMER_THRESH = 4167.0
timer_frequency = (1193182 / 4096) * (3433 / 4167)
                ≈ 239.992156 quarter-frame units/second
```

The normal (unaccelerated) main-loop delay uses `waitForTimer(delta * 4)` and calculates milliseconds using that frequency. Therefore a stable `delta = VAR_TIMER_NEXT = 6` implies **nominal ~100.003 ms per SCUMM update** (about 10 Hz); `delta=1` implies **~16.667 ms** (about 60 Hz), assuming non-fast mode, no substantial host scheduling lag and no script overriding the timer variable. The game's cumulative `VAR_TIMER_TOTAL` records units of the engine's **delta**, not how long the debugger window stays open.

The user's Room 23 observations of `VAR_TIMER=6`, `VAR_TIMER_NEXT=6`, and totals `51900→52314→52620` are consistent with this source-derived cadence, although they do **not** log each individual callback or its palette.

## Controlled alternative without rebuilding

The standard SCUMM debugger allows **writing** indexed `scumm_vars` entries. Because the normal game loop fetches its delta from `VAR_TIMER_NEXT` at the beginning of each iteration, temporarily setting `scumm_vars[19] 1` should request a ~60-Hz callback schedule instead of the observed ~10-Hz schedule, **if room scripts do not immediately overwrite the variable**.

Use debugger commands (NOT PowerShell), starting in room 23:

```text
room
scumm_vars[19]
scumm_vars[46]
scumm_vars[47]
scumm_vars[19] 1
scumm_vars[19]
continue
```

After visually observing several seconds of animation, manually reopen the debugger and read (and restore):

```text
room
scumm_vars[19]
scumm_vars[46]
scumm_vars[47]
scumm_vars[19] 6
continue
```

Expected if override holds: `VAR_TIMER_NEXT=1` and `VAR_TIMER=1` at next sample; palette cycling still uses roughly 60 counter units per wall second but has six times as many opportunities to update individual cycles. If `VAR_TIMER_NEXT` has reverted to 6, record a script/game reset rather than claiming the intervention worked. This is a **deliberate alteration of live game variables** and may change gameplay or crash. Keep archives unmodified. `debug_countdown` does not participate in this test.

This tests the *causal relation of the scheduling variable and callback cadence*, not automatically the exact observed 768-byte palettes or captured frame timing. Even a clear 10-Hz / 60-Hz screen difference remains distinct from an authenticated engine palette trace.

## Links (pinned source)

- https://github.com/scummvm/scummvm/blob/v2026.4.0/gui/debugger.cpp
- https://github.com/scummvm/scummvm/blob/v2026.4.0/gui/debugger.h
- https://github.com/scummvm/scummvm/blob/v2026.4.0/backends/events/default/default-events.cpp
- https://github.com/scummvm/scummvm/blob/v2026.4.0/engines/scumm/debugger.cpp
- https://github.com/scummvm/scummvm/blob/v2026.4.0/engines/scumm/scumm.cpp
- https://github.com/scummvm/scummvm/blob/v2026.4.0/engines/scumm/scumm.h
- https://github.com/scummvm/scummvm/blob/v2026.4.0/engines/scumm/vars.cpp

**Limit:** Source inspection does not independently prove that the user's running ScummVM binary corresponds exactly to this tagged release; confirm build version separately if discrepancies appear.
