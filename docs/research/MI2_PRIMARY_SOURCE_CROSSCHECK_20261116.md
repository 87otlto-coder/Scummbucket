# MI2 spelunking — authoritative source cross-check and engine-timing findings (2026-11-16)

**Scope and evidence class:** desk-based comparison of **authoritative primary implementations and their own documentation**, plus read-only object-header inspection of the already fingerprinted original DOS VGA MI2 archive. No gameplay, debugger, DOS executable execution, descumm-on-MI2 output, rendered-frame comparison, or ScummBucket implementation change occurred. This is **not runtime observation** and does not establish every archive-predicted script path as reachable.

Original MI2 archive member `MONKEY2.001` SHA-256: `ad045372e0d49626503bb50fca29a687ec8e01ef75d9b8bca702a366d143819e`. Original files are unchanged; no original resource bytes or images are committed.

## Primary sources and confidence boundaries

1. **ScummVM source, pinned to tag `v2026.4.0`**: primary *implementation* evidence for the behavior of that exact ScummVM revision. Important files:
   - [`palette.cpp`](https://github.com/scummvm/scummvm/blob/v2026.4.0/engines/scumm/palette.cpp): `initCycl`, `cyclePalette`, indirect palette mapping.
   - [`script_v5.cpp`](https://github.com/scummvm/scummvm/blob/v2026.4.0/engines/scumm/script_v5.cpp): v5 opcode handlers `o5_startScript`, `o5_drawObject`, `o5_wait`, `o5_delay`, `o5_roomOps`, `jumpRelative`, etc.
   - [`script.cpp`](https://github.com/scummvm/scummvm/blob/v2026.4.0/engines/scumm/script.cpp): `runScript`, `runScriptNested`, `runAllScripts`, `decreaseScriptDelay`, `runEntryScript`.
   - [`scumm.cpp`](https://github.com/scummvm/scummvm/blob/v2026.4.0/engines/scumm/scumm.cpp) and [`scumm.h`](https://github.com/scummvm/scummvm/blob/v2026.4.0/engines/scumm/scumm.h): main update cadence, jiffies, PIT-derived timer constants.
   - [`object.cpp`](https://github.com/scummvm/scummvm/blob/v2026.4.0/engines/scumm/object.cpp), [`object.h`](https://github.com/scummvm/scummvm/blob/v2026.4.0/engines/scumm/object.h): v5 source position, state and dirty-object semantics.
   - [`gfx.cpp`](https://github.com/scummvm/scummvm/blob/v2026.4.0/engines/scumm/gfx.cpp), [`costume.cpp`](https://github.com/scummvm/scummvm/blob/v2026.4.0/engines/scumm/costume.cpp): mask/transparent compression and single clip-plane lookup.
2. **ScummVM Tools's actual `descumm` parser**: [`descumm-tool.cpp`](https://github.com/scummvm/scummvm-tools/blob/master/engines/scumm/descumm-tool.cpp). It explicitly handles tagged `LSCR`, `SCRP`, `ENCD`, `EXCD`, and v5 `VERB`. `-5` selects the SCUMM v5 family; `-o` always prints offsets. `-u` is for unblocked/no-header scripts and is NOT appropriate for a normal extracted tagged v5 chunk. Pin the tool commit/build version when executing validation. This confirms a practical independent *decoder implementation path*, not that it has already checked our custom walker.
3. **[ScummVM-hosted historical SCUMM v5 guide](https://www.scummvm.org/old/docs/specs/scrp-v5.php)** and [script model](https://www.scummvm.org/old/docs/specs/scrp.php): published reference for opcode encodings, `breakHere`, `delay`, nested scripts and variable operands. The guide calls itself “inComplete,” dates to 2000–2002, and includes TODOs/ambiguities: contemporary pinned engine source takes precedence on disagreement.
4. **[GrogVM, independent source-available SCUMM v5 implementation](https://github.com/roccozanni/grogvm)**, read at tree commit `275f562e56c5ea9c28e160dd04f0d5065b4895a4`: its [object documentation](https://github.com/roccozanni/grogvm/blob/275f562e56c5ea9c28e160dd04f0d5065b4895a4/pages/docs/scumm/objects.md), [z-plane documentation](https://github.com/roccozanni/grogvm/blob/275f562e56c5ea9c28e160dd04f0d5065b4895a4/pages/docs/scumm/zplane.md), and [costume scaling notes](https://github.com/roccozanni/grogvm/blob/275f562e56c5ea9c28e160dd04f0d5065b4895a4/pages/docs/engine/costumes.md) corroborate distinct mechanism families from independent MI1 work. **Critical scope limit:** GrogVM is currently MI1-focused, explicitly does NOT animate CYCL palettes in its [PROGRESS.md](https://github.com/roccozanni/grogvm/blob/275f562e56c5ea9c28e160dd04f0d5065b4895a4/PROGRESS.md), and states its scaled actor rendering is an approximation. It cannot independently verify MI2 Room 35 cycling, exact scaled-costume pixels, or MI2-specific activity.
5. **[DREAMM 4.0 author's official documentation](https://dreamm.aarongiles.com/docs/v40/)**: Aaron Giles explicitly describes DREAMM as emulating the x86 hardware to run the **original** DOS interpreter, and lists MI2. It can serve as a different eventual observation target from ScummVM, but **DREAMM source is not public**; its documentation does NOT explain Room 35's CYCL flag 0x0004. Do not claim source confirmation from DREAMM where none exists. Runtime capture still needed.

## Findings confirmed or expanded by source

### F1 — SCUMM v5 palette rotation is discrete, timer-driven and phase-sensitive

`initCycl` DOS v5 path reads each nonzero record's `rate_raw`, `flags`, `start` and `end` and sets `delay = 16384 / rate_raw` using integer division. `cyclePalette` uses `valueToAdd = max(VAR_TIMER, VAR_TIMER_NEXT)`, accumulates `counter`, and on `counter >= delay` takes `counter %= delay` **but rotates the range only once per function call**. This is not a pure frame-index-to-phase mapping and does not automatically perform several rotations to catch up after a long timer step.

For original-source **Room 35**:
- CYCL1 raw rate 3072 → **delay 5 timer units**; colors **176–191**.
- CYCL2 raw rate 2688 → **delay 6 timer units**; colors **160–175**.
- Both raw flags **0x0004**. In the inspected ScummVM v5 rotation path the only used flag bit is `flags & 2`; since 0x0004 lacks that bit, both use the default direction in **this ScummVM implementation**. **Meaning of raw bit 0x0004 to the original DOS executable remains unverified.** Do not rewrite source metadata or suppress warnings.

The same path rotates `_currentPalette` **and** adjusts `_shadowPalette` (if allocated) with indirect index mapping; it also rotates palette-manipulation buffers via `moveMemInPalRes`. A simplistic palette RGB shift without shadow/transform phases can yield mismatches even with correct `CYCL` record extraction. Note script `o5_roomOps` can change cycle speed independently of initial CYCL, as documented in the existing event-surface note.

**Test design:** save `rate_raw`, `delay`, `flags`, `counter_before`, `effective_delta`, `counter_after`, `rotation_direction`, `rotation_count`, `palette_rgb_hash`, `shadow_palette_hash`, update phase and any script cycle-speed override. Do not assign a constant wall-clock GIF interval from the integer delay alone.

### F2 — Main-loop script time is tied to VAR_TIMER_NEXT; delay(18) is not 18 rendered frames

`ScummEngine::setTimerAndShakeFrequency()` sets DOS v5 internal `_timerFrequency` to
`(1193182/4096)*(3433/4167)` ≈ **240 quarter-frame ticks/second**. The main loop reads **delta = VAR_TIMER_NEXT** when available (otherwise 4), and calls `waitForTimer(delta * 4)`, then `scummLoop(delta)`. Thus the chosen `delta` is approximately in **1/60 second script units** at normal speed. This reconciles the historical SCUMM guide's 1/60-second `delay` units with ScummVM's 240 Hz internal pacing. Do **not** equate the 240 Hz timer with a 240 FPS rendered scene.

`scummLoop` records `VAR_TIMER = delta`; for script-delay updates it caps `delta` at 15 before calling `decreaseScriptDelay(delta)`. The latter resumes a paused script only when its remaining delay is **strictly < 0**, not when equal to zero. A requested `delay(18)` in Room 81 therefore has nominal **0.3-second** logical value, but the actual transition is **quantized by chosen engine `delta`** and can overshoot by at least an update. Example **conditional on delta=4 every update** (not an observed Room 81 setting): five future decrements of 4 would be needed (20 > 18), yielding a nominal ≈0.333 seconds before the script is eligible to resume. Frame phase and whether the script was invoked before the current update can change the visible interval. Fast mode, overrides, pauses and real elapsed time matter.

**Further subtlety:** the palette routine can read the uncapped `VAR_TIMER`, whereas `decreaseScriptDelay` uses locally capped `delta`. If a timer update is >15 units, they can advance at **different effective rates** in the same update. Do not use one implicit `dt` everywhere without reproducing these semantics.

A `breakHere` yields until a future script slot run, while `o5_delay` pauses for a decrementing amount. They are not interchangeable. The Room 35 waterfall (`breakHere` per state) vs Room 81 object 780 (`delay(18)` per state) is a good paired benchmark for this engine-specific distinction.

### F3 — Starting a child script is nested/immediate, not necessarily deferred to next rendered frame

ScummVM `o5_startScript` calls `runScript(...)`. `runScript` initializes a slot and invokes `runScriptNested`, which sets up the child and **executes it immediately** until it yields, pauses, terminates or otherwise stops. `runAllScripts` is a subsequent scheduler pass. This means entry/caller graphs like **Room 55 ENCD → 200 → 212 → child loop** can produce multiple state changes within one outer update, and a child may begin before the caller continues. That is *engine-source semantics*, not proof the Room 55 large-script call-site candidates are valid/reachable.

Instrumentation must log `nested_depth`, script slot and bytecode PC, script identity/source, begin/end/yield reasons, rather than assuming every `startScript` implies a one-frame delay.

### F4 — V5 same-bounding-rectangle object eviction confirmed; three MI2 examples

Pinned `o5_drawObject` changes an object's position using **8-pixel units** for explicit `draw at`, enqueues it, then sets the states of all objects with the **same X, Y, width and height** to zero, before setting the selected object's desired state. GrogVM's independently implemented MI1 model describes the same class of **same-box replacement** to prevent animation sprites accumulating.

A read-only independent comparison of every paired MI2 `CDHD` rectangle found these examples:

| Room | Identical initial (X,Y,W,H) in native pixels | Object IDs |
| --- | --- | --- |
| 44 | (88,48,112,96) | 451,461 |
| 48 | (240,32,24,32) | 515,517 |
| 72 | (40,32,40,64) | 741–748 |

Note Room 48 also has six zero-sized `CDHD` entries (547–552) sharing (0,0,0,0): do not treat them as visible art. For the same original member, **all 1,145 paired OBIM/OBCD objects had matching initial X/Y between the 8-pixel-grid CDHD and the IMHD's x/y-like 16-bit fields**. This metadata equality makes base-coordinate disputes invisible on these static inputs; during runtime scripted motion ScummVM v5 explicitly mutates the `ObjectData` coordinates derived from `CDHD`. A third-party reference that informally calls `IMHD` the drawing position must not be treated as authority for a moved object's live coordinates.

The event manifest must retain state-0 eviction, original and *current* bounds, dynamic object placement and dirty-strip processing. Room 72's eight initially same-rectangle objects are a particularly valuable interaction between source aliasing and runtime repositioning.

### F5 — Actor Z-planes are selected, not a cumulative alpha-depth stack

Pinned ScummVM `costume.cpp` calls `getMaskBuffer(..., _zbuf)` for the actor's clip plane. GrogVM independently documents that clip level k samples **ZPk**, not the union of ZP01…ZPk; clip 0 bypasses room occlusion masks. ScummVM `gfx.cpp` treats each Z-plane separately and, in mask update paths, may **OR transparent-region masks** instead of replacing them when `dbAllowMaskOr` is active.

For **Rooms 48/79** with three background Z-plane levels: do **not** flatten ZP01/02/03 into a single foreground image, or compare a generic all-layer mask to actor frames. Capture each actor's clip level and query only its corresponding mask; record dynamic mask writes separately. This is strongly supported by two independent implementations of the SCUMM v5 family (GrogVM validated MI1, ScummVM covers MI2), but the actual Room 48 actor 7/8 clip settings are **unobserved**.

### F6 — Transparent background strips demand scene-underlay and Z-mask context

Pinned ScummVM `Gdi::decompressBitmap` maps transparency-aware codecs (v5 source included) to decoders with the transparency flag set. `Gdi::decodeMask` uses the returned `transpStrip` flag and `dbAllowMaskOr` to decide OR-vs-replace for Z masks. This corroborates the 60 transparent-background strips already recorded in `MI2_P2_TRANSPARENT_BACKGROUND_STRIPS_20261116.md`. It does **not** verify all those strips against original engine framebuffer. Retain the current `BACKGROUND_TRANSPARENT_CODEC_UNSUPPORTED` diagnostic unless actual underlay is explicitly supplied and verified.

### F7 — Official descumm validates a proposed *method*, not our executed scripts

Source `descumm-tool.cpp` confirms that normal v5 tagged `LSCR`, `SCRP`, `ENCD`, `EXCD` and `VERB` can be disassembled with appropriate header parsing and that `-5` targets v5. The historical guide supplies a second encoding reference for `getRandomNumber`, `startScript`, `jumpRelative`, `breakHere`, `delay`, indirect variables and nonorthogonal opcode operands. This supports the *framework* behind Room 35/55/72 candidate script walks. It does **not** directly certify that the walker in our previous research consumed every opcode correctly or that unaligned global-script hits are real.

**Future exact verification:** run `descumm -5 -o <tagged-extracted-LSCR-or-SCRP-file>` without `-u` for tagged original chunks; pin the tool version and compare instruction boundary/operand maps to ScummBucket's narrow walker. Preserve call graph target/control-path uncertainty separately.

## Open disagreements / non-confirmations worth preserving

- **Room 35 `CYCL` flag `0x0004`:** confirmed ignored by the specific ScummVM v5 rotation branch except that `flags & 2` determines direction; **NOT confirmed against the original DOS interpreter** or DREAMM execution.
- **Room 64 `flags=0xD906`, rate=65494:** ScummVM `16384 // raw_rate = 0`, so `cyclePalette` skips that record because delay is zero. This source-based rule confirms the *ScummVM behavior*, **not** whether original game treats an anomalous record identically. Must remain a diagnostic.
- **GrogVM palette cycling:** `PROGRESS.md` explicitly says CYCL is catalogued but NOT animated. GrogVM is therefore NOT an independent palette oracle for Rooms 22/24/28/35/81.
- **GrogVM scaled costumes:** its author explicitly identifies an empirically tuned, not-original row/column removal algorithm. This *reinforces* ScummBucket's need to use the pinned ScummVM phase/scale table and original DOS comparisons; do NOT use matching GrogVM scaled visuals as exactness proof.
- **DREAMM:** runs original interpreter, but no published source; useful for independent runtime comparison when available, not for source-derived CYCL bit semantics.
- **Room-specific source counts and states:** external references cannot independently confirm our `MONKEY2.001` fingerprinted object IDs, counts or script execution; these remain archive observations with future integration tests.
- **Version-specific object placement:** the v5 `resetRoomObject` path gets base X/Y/W/H from `CDHD`; newer SCUMM versions read geometry from different fields. Do not transplant a v7/8 or third-party pixel-accurate claim onto MI2 v5.

## High-information next verification tasks

1. **Room 35 waterfall:** prove descumm alignment for LSCR202 and its caller; log `VAR_TIMER_NEXT`, `VAR_TIMER`, 5/6 cycle counters and 8-state object 364; test palette+object composition against ScummVM indexed output; compare a controlled original-DOS/DREAMM capture if unresolved flags persist.
2. **Room 81 vs 24:** log script clock and yield/delay transitions; test nominal 18/60-second delay vs quantized engine updates; avoid fixed FPS inferred solely from operand.
3. **Room 44/48/72:** test state-0 same-box eviction and dynamic repositioning; keep logical zero-image objects distinct from source-drawn pixels.
4. **Room 48/79:** track actor `_zbuf` (clip level) and per-plane mask modifications under transparent-image OR paths; validate pixel-accurate actor occlusion.
5. **Room 55:** independently descumm large scripts 200/212, trace nested execution and stop/branch reachability before composing randomized loops.
6. **Room 49:** verify transparency-aware SMAP strips and pre-existing underlay; do not synthesize missing colors.
7. **Project evidence:** record engine build/tag, enhancements, original member hashes, script PCs/phase, active actor/costume/clip IDs, palette and masks before/after each update. No new P4 acceptance label without observed indexed-pixel comparison.

This report is authoritative **source confirmation of mechanisms**, not a claim of gameplay reproduction. It extends and qualifies, rather than silently upgrading, the earlier research notebooks.
