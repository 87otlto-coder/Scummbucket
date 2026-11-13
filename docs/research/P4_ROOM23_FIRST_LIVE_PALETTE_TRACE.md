# P4 — First actual ScummVM Room 23 palette trace: 180 real callbacks

**Research date:** 2026-11-08. **Evidence status:** Captured engine palette samples, independently decoded game CLUT/CYCL, exact replay within two phase-aligned segments. **Trace container incomplete: no END marker.**

## Input provenance

The user uploaded `room23-normal-20261108-215059-863.raw.log` after compiling the corrected ScummVM V2 `Common::DumpFile` hook. The original DOS VGA MI2 archive was independently decoded from the user-provided `mi2.zip` (not committed):

| Input | SHA-256 |
|---|---|
| Raw engine trace | `ac8163b6305a35680764fd157694ea85a10de63949be20349dae7cbc943100ee` |
| `MONKEY2.001` | `ad045372e0d49626503bb50fca29a687ec8e01ef75d9b8bca702a366d143819e` |
| Source Room 23 CLUT, 768 RGB bytes | `44a542ed57e641676623a0d48c5a28a7b8d47e87482acb5af21a4a2eef65d242` |

**Limits:** The raw trace format does not embed a cryptographic attestation of the running executable, compiler, or source commit. The ScummVM V2 build was user-confirmed, not independently inspected. No original game bytes or 768-byte palette payloads are committed to the repository.

## Structural integrity and runtime observations

- Log has **181 records**: one `SBP4|BEGIN` and **180 consecutive** `SBP4|SAMPLE` records, numbered 1–180. Each contains a syntactically valid, exactly 768-byte RGB palette.
- **No `SBP4|END`** is present. The strict importer is correct to reject the file as an *incomplete recording*, not label it a completed trace. Do not append an artificial END marker or weaken the importer.
- All **180** timer pairs are `VAR_TIMER=6`, `VAR_TIMER_NEXT=6`. Their timestamp intervals are normally ~100 ms (median **100 ms**), independently corroborating the 10-Hz nominal Room 23 update regime.
- Engine timestamps span **38036 → 83042 ms** (~45.006 seconds of real clock), but there is a single **27,086-ms gap** between samples 80 and 81. The log does not record why. Apart from that discontinuity, the regular intervals are consistent with ongoing engine updates.
- Across the capture, only **16 palette indices change**: **176–191**; all 240 other palette entries remain unchanged from the BEGIN record. Across 180 samples there are **26 distinct full RGB palettes** and 98 sample-to-previous-palette transitions with no change.

## Direct original-resource validation

From the actual input archive, the encrypted `MONKEY2.001` is decoded with XOR `0x69`. The original Room 23 CLUT was found at archive offset `1894950`; its eight cycle records at offsets `1894080 + 9*i` for cycle IDs 1–8. This independently corroborates all cycle definitions previously exported by ScummBucket:

```text
ID:                  1    2    3    4    5    6    7    8
Palette pair:     176-177 178-179 180-181 182-183 184-185 186-187 188-189 190-191
Raw rate:           230  307  153  384  460  384  230  307
Delay units:         71   53  107   42   35   42   71   53
```

All ranges are two colors, so each source-defined cycle rotation exchanges the two RGB triplets. For a six-counter-unit update, the predicted color state after `n` cumulative updates follows `floor(6*n / delay)` rotations (modulo two), assuming uninterrupted cycles initialized at zero.

The raw source CLUT and the engine BEGIN palette differ at **six** indices: `1,2,3,6,180,181`. Only two are within the animated region; the other four are **stable runtime overrides** and are not explained by the room's CYCL records. The BEGIN record's animated indices match the original CLUT after **59 equivalent six-unit updates**. This equivalence is an *inferred phase*, not a direct measurement of room-entry time.

## Replay and held-out validation

Exactly **two** independent model phases explain all observed changing RGB entries, with no hand-editing of individual expected frames:

| Sample segment | Inferred cycle update positions | Calibration | Held-out frames matching | Total matching |
|---|---|---:|---:|---:|
| 1–80 | 60 through 139 (BEGIN corresponds to 59) | First **3** samples | **77 / 77** | **80 / 80** |
| 81–180 | 1 through 100 | First **5** samples | **95 / 95** | **100 / 100** |
| **Total** | Two separately aligned phases | 8 frames | **172 / 172** | **180 / 180** |

For calibration, a search of candidate starting update indexes `1..500` yields a **unique** first-segment starting index after three samples (`60`) and a **unique** second-segment starting index after five samples (`1`). The remaining 172 samples were held out from selecting their respective phase.

**Strongest result:** The 16 cycling palette indices match the original resource-driven reconstruction in **all 180** actual post-`cyclePalette()` engine samples. The **full 768-byte RGB palette** also matches on all 180 samples *when retaining the four stable engine-observed non-cycle palette overrides (indices 1,2,3,6)*. This validates the recorded Room 23 cycling behavior within the stated state and time constraints, **not** complete room scene animation, graphics composition or render presentation.

### Interruption and likely state reset

The 27.086-second gap between samples 80 and 81 coincides with **all sixteen** animated palette entries changing at once (all eight two-color pairs), and the sample-81 animated entries matching the **original source CLUT exactly**. Afterward the sample sequence behaves as if the room's cycle counters were initialized again to zero. **Likely** mechanisms include re-entering Room 23 via the debugger or another palette/cycle state reset; the trace alone cannot distinguish them.

Do **not** attribute the 27-second period to 270 simulated six-unit updates: no such callbacks were logged. Do **not** describe the apparent reset as ordinary normal cycling behavior.

## Acceptance status and next work

1. **Engine instrumentation and live palette collection:** observed working (V2 compiled, capture supplied).
2. **Source-driven palette cycle mechanism, original VGA Room 23:** exact match for 180/180 observed callbacks, with phase model and stable runtime overrides disclosed.
3. **Strict complete-trace importer acceptance:** **not achieved** because the raw trace lacks `SBP4|END`; preserve the truncated original for forensic study.
4. **Rendering beyond palette cycling:** not covered. Object/actor animation, layer masks, scripts, and presentation timing remain separate research objectives.
5. **Important verifier limitation:** Even if a new capture reaches an `END` record, the current strict `compare_palette_samples()` implementation **assumes the live BEGIN palette exactly equals the static CLUT**. This capture proves that can be false (four stable runtime overrides plus active cycle phase). A nominally complete log may therefore still raise `TRACE_INITIAL_PALETTE_MISMATCH`. Do **not** weaken that strict contract without introducing a separately reported, explicit phase-aware comparison mode with independent stable-palette and reset diagnostics.
6. **Recommended next work:** preserve and use these real samples as a forensic reference, implement the explicit phase-aware research verifier, and separately obtain an uninterrupted normal capture through 256 callbacks (`SBP4|END|256|limit`) for the formal strict-import acceptance check. Then capture the 60-unit stress regime to test modeled loss of per-update rotations. Keep all raw captures outside the public repository.

**Related:** [Windows runbook](P4_WINDOWS_TRACE_RUNBOOK.md), [original scheduler sweep](P4_ROOM23_SCHEDULER_SWEEP.md), [trace protocol](P4_SCUMMVM_ENGINE_TRACE_CAPTURE.md), [model verifier](../../scummbucket/palette_trace.py).
