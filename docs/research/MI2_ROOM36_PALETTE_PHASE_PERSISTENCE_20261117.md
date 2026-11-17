# MI2 Room36 palette fades — phase/counter continuity and discrete delay model (2026-11-17)

**Evidence:** Original DOS VGA archive has Room36 local scripts201/202 (fully bytecode-aligned and documented in [Room36 fades](MI2_ROOM36_SCRIPTED_PALETTE_FADES_20261117.md)); actual counter/phase semantics from authoritative pinned [ScummVM v2026.4.0 palette.cpp](https://github.com/scummvm/scummvm/blob/v2026.4.0/engines/scumm/palette.cpp), [script_v5.cpp](https://github.com/scummvm/scummvm/blob/v2026.4.0/engines/scumm/script_v5.cpp), [room.cpp](https://github.com/scummvm/scummvm/blob/v2026.4.0/engines/scumm/room.cpp), and [saveload.cpp](https://github.com/scummvm/scummvm/blob/v2026.4.0/engines/scumm/saveload.cpp). **Source-derived deterministic mechanics, NOT observed original-DOS or ScummVM runtime phase**, and no indexed framebuffer parity. Original ZIP remains read-only/outside Git.

## Distinct mechanisms that must not be conflated

1. **Initial physical-room loading:** `ScummEngine::initCycl` clears all 16 `ColorCycle` records with `memset`, then loads each room's stored rate, flags and start/end range, sets each counter=0. `room.cpp::setupRoomSubBlocks` calls `initCycl` for a supported CYCL resource. A new room initialization can therefore begin a new colour-cycle phase, subject to source room and script entry order.
2. **In-room speed override:** V5 `o5_roomOps` subopcode `SO_CYCLE_SPEED` writes **`_colorCycle[a-1].delay` only**. The exact update is `delay=(speed != 0) ? 16384/(76*speed) : 0` with integer division. No counter reset; no change of range, stored flags or current RGB palette.
3. **Palette update:** `cyclePalette()` skips a cycle if `delay==0` or `start>end`. A skipped cycle does **not** clear its accumulator and does **not** restore the originally stored palette colours. Active cycles add `max(VAR_TIMER,VAR_TIMER_NEXT)`, and if the accumulator reaches threshold, they apply **exactly one rotation** and then `counter %= delay`. No catch-up loop for multiple rotations during a large timer step.
4. **Persistence in ScummVM saves:** `saveload.cpp` serializes each cycle's `delay`, `counter`, `flags`, `start`, `end` for normal compatible save versions (the code calls `syncArray(_colorCycle,16,syncWithSerializer)`). A save/load in that implementation can preserve cycle phase information; original MI2 DOS save-data equivalence is **not established**.

**Core consequence:** Two apparently identical stationary Room36 scenes at speed0 can have different retained counters and RGB phases. Reactivating the cycles inside that room may not give identical timing unless the full palette and counters are controlled. A static speed-to-GIF lookup loses this history.

## 40-pass fade speed input and integer delay quantization

Target speeds for Room36's five cycles: `[33,32,35,21,20]`. For **script201** (shutdown), pass `n=1..40` uses:
`speed_off(i,n) = max(target_i - (n-1), 0)`.
For **script202** (ramp-up), pass `n=1..40` uses:
`speed_on(i,n) = min(n-1,target_i)`.
Both call `SO_CYCLE_SPEED` once per cycle per pass and `breakHere` once per full five-cycle pass. No assumption of 40 *rendered* frames or 40 palette rotations.

| Speed | Effective delay = floor(16384/(76×speed)) | Why it matters |
| ---: | ---: | --- |
| 0 | **0** | Disabled; RGB and accumulator retained |
| 1 | **215** | Very slow cycle (not immediate rotation) |
| 2 | **107** | Quantized threshold |
| 3 | **71** | Quantized threshold |
| 4 | **53** | Quantized threshold |
| 5 | **43** | Quantized threshold |
| 10 | **21** | Different scripted speeds can eventually share thresholds |
| 20 | **10** | Final delay for cycle5 |
| 21 | **10** | Final delay for cycle4 |
| 32 | **6** | Final delay for cycle2 |
| 33 | **6** | Final delay for cycle1 |
| 35 | **6** | Final delay for cycle3 |

In ramp-up scripts, **pass1 writes speed0**, **pass2 speed1**, and the corresponding target is first issued on **pass target+1**: cycle5 at pass21, cycle4 at pass22, cycle2 at pass33, cycle1 at pass34, cycle3 at pass36. Shutdown reaches speed0 for cycle5 at pass21, cycle4 pass22, cycle2 pass33, cycle1 pass34, cycle3 pass36. All five continue receiving repeated identical speed writes through pass40. These are source-derived speed commands, **not predicted visible changes**.

## The relevant P4 phase-state transition

Define per active CYCL instance:
`{source_room, cycle_id, source_start,end, flags, delay, counter, rgb_phase, shadow_phase, timer_delta, engine_update_phase}`.

- **Room36 entry** initializes cycles from stored CYCL, and room ENCD can immediately override speed based on `Bit92` / `Var49==19`.
- **Pump script200** changes the persistent Bit92 and immediately starts Room36 local201 or202; the child begins on the same outer script update, not by definition a later displayed frame.
- **Ramp/shutdown loop** writes five delay values before each script yield. Palette update may occur before or after a specific scheduler phase, so log both speed-write PCs and palette-update order in real traces.
- **Stopped state** (`delay=0`): freeze RGB phase, keep counter and shadow palette; do **not** reset to room source palette or empty masks.
- **Re-enabled state:** prior `counter` and current RGB phase remain relevant, even if the scripted target speed equals the original entry value.

**Diagnostic suggestion:** `PALETTE_CYCLE_PHASE_UNOBSERVED` when the export lacks starting `counter`/RGB state; `SCRIPT_SPEED_OVERRIDE_APPLIED` as method label; `ROOM_CYCL_REINITIALIZED` with source PC/phase when appropriate. Do not mark animation complete based solely on known speed operands.

## Next verification

A controlled Room36 sequence in the same ScummVM build with Bit92 toggled twice; capture 40 passes per fade, all five `delay` and `counter` arrays before/after every palette tick, RGB[160..191] and shadow mapping hashes, `VAR_TIMER` and `VAR_TIMER_NEXT`, nested start-script phase, and actual native indexed front/back buffers. Compare an immediate room re-entry against in-room restart, then save/load resume. Mark original DOS equivalence independently.

**Status:** verified *pinned ScummVM implementation rules* and original source scripts; **not** observed MI2 gameplay or original interpreter parity.
