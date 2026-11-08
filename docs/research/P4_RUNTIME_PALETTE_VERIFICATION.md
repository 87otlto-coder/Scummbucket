# P4 — Comparing simulated MI2 palette cycles with actual ScummVM execution

**Status:** Comparison pipeline implemented and tested synthetically. **No real ScummVM palette trace has been captured or verified.**

**Target:** Fingerprinted original DOS Monkey Island 2 archive, room 23 first and room 109 second.

## Why another verification step is required

ScummBucket's `palette-probe` decodes the original room's indexed background, reads the original `CLUT` and `CYCL` data, and rotates colors using the documented v5 algorithm. The original probe assumed **one counter unit per synthetic update**. That was never an engine timing measurement.

ScummVM source confirms the timing relationship:

1. In `engines/scumm/scumm.cpp`, the main loop computes an elapsed engine `delta` from `VAR_TIMER_NEXT` (with engine/game-specific handling), then calls `scummLoop(delta)`.
2. `scummLoop(delta)` assigns `VAR_TIMER = delta` before processing scripts.
3. `scummLoop_handleEffects()` calls `cyclePalette()` in SCUMM v4+ through the relevant HE versions, then `palManipulate()`.
4. `engines/scumm/palette.cpp`'s `cyclePalette()` uses `max(VAR_TIMER, VAR_TIMER_NEXT)` as the **counter increment at the point the cycle runs**, compares against the delay derived from raw `CYCL` rate, and rotates each eligible range **at most once per call**. It also checks the flag bit for direction.
5. Game scripts may change cycle delay, stop cycles, modify the active palette or change `VAR_TIMER_NEXT`. Therefore source `CYCL` plus the initial `CLUT` is **not always sufficient** to predict every runtime state.

Source references: [ScummVM scumm.cpp](https://github.com/scummvm/scummvm/blob/master/engines/scumm/scumm.cpp), [ScummVM palette.cpp](https://github.com/scummvm/scummvm/blob/master/engines/scumm/palette.cpp), and [SCUMM debugger.cpp](https://github.com/scummvm/scummvm/blob/master/engines/scumm/debugger.cpp).

### Two distinct workflows

**A. Visual confirmation with the standard ScummVM application (no custom build)**

1. Run your authorized original Monkey Island 2 files in ScummVM, save your progress if needed, then open the debugger using its configured **Open Debugger** shortcut (normally Ctrl+Alt+D on desktop).
2. The SCUMM debugger provides `room <roomnum>`; `room 23` jumps to room 23. Use `continue` to resume the game. Debugger room-jumping may not replicate all normal gameplay state, so do **not** assume the resulting scene is equivalent to naturally entering the room.
3. Capture several screenshots after entering the room, using ScummVM's configured screenshot shortcut (commonly Alt+S). On Windows, its default screenshot directory is `%USERPROFILE%\Pictures\ScummVM Screenshots`.
4. Compare visible changes in static scenery over time, paying special attention to the cycled color regions. Keep actors, object overlays, scrolling, transformations and scaling/aspect correction in mind.
5. This can establish **observed on-screen changes**, but not yet the exact `VAR_TIMER` values, engine palette event log or timing in internal counter units. A screenshot taken on one frame is not an accurate standalone timer measurement.

Official references: [ScummVM keyboard shortcuts](https://docs.scummvm.org/en/latest/use_scummvm/keyboard_shortcuts.html), [ScummVM configuration file / screenshot path](https://docs.scummvm.org/en/latest/advanced_topics/configuration_file.html).

**B. Exact engine palette trace (requires independently instrumented ScummVM build)**

To compare palette values automatically, capture a **private JSON trace** from the SCUMM engine at a precise sampling point:

- At the beginning, before the first logged `cyclePalette()` update for the selected room, capture the 768-byte RGB `_currentPalette` as `initial_palette_rgb_hex`. **If this differs from the archived room `CLUT`, the current verifier refuses the comparison** with `TRACE_INITIAL_PALETTE_MISMATCH`, rather than silently ignoring the effects of room scripts, fades or other palette manipulation.
- For each consecutive `cyclePalette()` invocation while the same room is active, sample the two engine values `VAR(VAR_TIMER)` and `VAR(VAR_TIMER_NEXT)` **at the actual call**, and record `_currentPalette` immediately **after `cyclePalette()` but before `palManipulate()`**. This avoids falsely treating subsequent palette-manipulation effects as a cycle-model discrepancy.
- Include the original `MONKEY2.001` SHA-256, the room ID, a ScummVM version/commit, and the capture method. Use a maximum of 256 updates per trace.
- Avoid recording copyrighted script text, sound, images or proprietary source chunks. The RGB palette trace is for private comparison only; **do not commit traces or game assets to GitHub**.

**Note:** Standard ScummVM does not appear to expose these per-update palette byte arrays in its built-in SCUMM debugger. A developer build or engine instrumentation is required for this precise dataset; we are **not** claiming that the current user has already captured it.

### JSON trace structure

The following is a *shape example*, not a real-game trace. The hex fields must contain exactly 768 bytes (= 1536 hex characters), produced by the capturing engine.

```json
{
  "schema_version": "0.1",
  "room_id": 23,
  "game_resource_sha256": "REPLACE_WITH_ACTUAL_64_CHAR_SHA256",
  "capture_point": "after_cyclePalette_before_palManipulate",
  "engine_commit": "REPLACE_WITH_SCUMMVM_COMMIT",
  "capture_method": "instrumented ScummVM engine",
  "initial_palette_rgb_hex": "REPLACE_WITH_1536_CHAR_INITIAL_HEX",
  "samples": [
    {
      "sequence": 1,
      "var_timer": 4,
      "var_timer_next": 4,
      "palette_rgb_hex": "REPLACE_WITH_1536_CHAR_POST_CYCLE_HEX"
    }
  ]
}
```

Values `4` above are merely illustrative. **Do not enter them as real measurements unless captured in the engine.**

### Run an actual comparison (once a trace exists)

```powershell
cd "C:\Users\87otl\ScummBucket"
git pull --ff-only origin feature/p1-scumm-v5-inventory

python -m scummbucket verify-palette-trace "D:\old" --room 23 --trace "C:\path\to\room23-observed-trace.json" --json
```

Optional `--output "C:\path\to\new-verification.json"` writes a new report and refuses to overwrite an existing one.

The comparison must validate input schema, source hash, room ID, contiguous sequence, exact capture point, valid timer counters and the exact initial static palette. It then replays **one engine-like palette update per supplied sample** using `max(var_timer,var_timer_next)`. Each sample reports predicted and observed palette SHA-256, rotation events, matching state, mismatched entry count and a few mismatched palette indices. The **first mismatch is explicitly identified**.

A `success` result means the model agrees with the **user-provided** palette values at those sampled updates. It does **not** authenticate who captured the trace, prove in-game animation visibility, establish a continuous animation loop, or measure elapsed milliseconds. A mismatch is reported as failure and may indicate unmodeled script state, unsupported palette effects, different initial state, or a decoder/model issue. Never silently skip mismatches.

### Current synthetic-probe extension

Even without external trace input, `palette-probe` now accepts `--counter-increment N`, where N is a **hypothetical fixed counter increase for each simulated update**:

```powershell
$stamp = Get-Date -Format "yyyyMMdd-HHmmss"
$out = "C:\Users\87otl\ScummBucket\exports\room23-delta4-$stamp"
python -m scummbucket palette-probe "D:\old" --room 23 --ticks 0 1 4 9 18 --counter-increment 4 --output-dir "$out"
```

The `--ticks` values here are **synthetic update indices** (not elapsed milliseconds). For a snapshot taken at index 9 with `--counter-increment 4`, the model has received 36 hypothetical total counter units; the actual engine may use different increments and scheduling.

## Acceptance criteria still outstanding

- Confirm ScummBucket's initial indexed room pixels against ScummVM's actual room rendering.
- Capture repeated visual proof of changes in the room's palette-cycled regions.
- Obtain an independently recorded per-update palette trace with exact timer values and palette bytes; compare all captured states.
- Investigate any divergence without muting diagnostics or assuming the source engine is wrong.
- Recover real scheduling/elapsed timing and relevant global script controls.
- Verify a true animated-background reconstruction with repeatable output and provenance.

**No real engine execution trace, sprite compositing or timing-accurate animation export is yet complete.**
