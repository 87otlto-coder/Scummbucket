# Room 7 renderer source map — implementation shortcuts and traps

**Research note only.** These are source findings and test design constraints, **not** evidence that ScummBucket already renders the 32-color scenery or scaled actors. Source examined against ScummVM `v2026.4.0`, original DOS VGA Monkey Island 2.

## Pinned upstream files and useful entrypoints

- [`engines/scumm/costume.cpp`](https://github.com/scummvm/scummvm/blob/v2026.4.0/engines/scumm/costume.cpp) — `ClassicCostumeLoader::loadCostume`, `ClassicCostumeLoader::increaseAnim`, `ClassicCostumeRenderer::drawLimb`, and palette handling.
- [`engines/scumm/base-costume.cpp`](https://github.com/scummvm/scummvm/blob/v2026.4.0/engines/scumm/base-costume.cpp) — `BaseCostumeRenderer::paintCelByleRLECommon`, `byleRLEDecode`, `skipCelLines`; canonical scale and packed RLE logic.
- [`engines/scumm/actor.cpp`](https://github.com/scummvm/scummvm/blob/v2026.4.0/engines/scumm/actor.cpp) — actor screen placement relative to virtual screen `xstart`, scale fields, costume and walk animation advancement.
- [ScummBucket `classic_costume.py`](../../scummbucket/classic_costume.py) — current 16-color archive decoder, native-scale `compose` and packed `apply_depth`. Room 23 87-frame regression is the non-negotiable baseline.

### 16-color versus 32-color COST layout

| Field | `0x58` 16 colors | `0x59` 32 colors | Notes |
| --- | ---: | ---: | --- |
| Format at byte 9 (low 7 bits) | `0x58` | `0x59` | High bit is a mirror/force-right flag |
| Palette bytes | 10–25 | 10–41 | Palette entries refer to *room palette indices*, not RGB triples |
| Local palette count | 16 | 32 | Slot 0 is transparent in classic renderer |
| Pointer to animation-command data | position 26 | position 42 | 16-bit little-endian relative source pointer as in existing v5 decoder |
| Limb table pointers | position 28 + 2×limb | position 44 + 2×limb | Source table offsets shift with palette count |
| Directional animation offsets | position 60 + 2×animation | position 76 + 2×animation | `frame * 4 + direction` where supported |
| Packed RLE color shift | 4 | 3 | `byte >> shift` |
| Packed RLE count mask | 15 | 7 | Zero means next byte stores run length |

The entry locations above are from the pinned v5-source interpretation already used by the native 16-color implementation; **check the precise COST pointer base and bounds on the actual 0x59 chunk before accepting the table**. Do not generalize this table to 0x60/0x61 or older SCUMM versions.

In `BaseCostumeRenderer::paintCelByleRLECommon`, `numColors == 32` explicitly sets `compData.mask = 7`, `compData.shr = 3`. `byleRLEDecode` applies `color = encoded >> shr`, `len = encoded & mask`, and reads another byte if `len == 0`. Source cels are traversed in **columns**, resetting Y after `height` pixels and then advancing X. The costume local zero slot is transparent, not the room's object `TRNS` index.

### Scaling is not ordinary nearest-neighbor resize

The source uses `smallCostumeScaleTable`, a threshold comparison, and **8-bit wrapping scale-phase indices**. In the v5 code:

- `scale == 255` bypasses skipping; lower values compare the table at the current phase to `_scaleX`/`_scaleY`.
- `scaleXIndex` and `scaleYIndex` are seeded from cel relative offsets and `scaletableSize`; this affects output positioning as well as which columns/rows survive.
- X scale phase follows costume draw direction, including mirrored cels; it increments on each **source** column, not just retained output columns.
- Y scale phase resets to the cel's starting phase at each source column; each **source** row advances the phase even if the row is skipped.
- X/Y and visibility are clipped against the viewport; the mask is sampled in **screen** coordinates only after camera subtraction.
- `Actor::prepareDrawActorCostume` sets actor screen X using world `_pos.x - _virtscr[kMainVirtScreen].xstart`. The current Room 7 record includes camera X and actor world positions, so both should be explicit renderer inputs.

If exact scaling cannot be implemented within the usage budget, **export decoded transparent source cels** and record which scale factors and phases remain unsupported. That is durable progress. Do not claim matching indexed foreground from a resized preview.

### Actor 11, Room 7

Room 7 script research in [integration runbook](P4_ROOM7_INTEGRATION.md) identified scenery actor 11 with costume 142. Script 207 computes world X as `590 - ((camera X - 624) / 2)`, with Y 144. In the debugger-equivalent captured run actor 11 moved across the right portion of the room as camera X increased 0→464; `y=144` is actor's foot origin and a costume cel may extend above it.

Observation isolation must use the *actual cel extent*: the previously identified frames 47–74 are candidates because Guybrush is well to the left, but some Guybrush pixels could remain in view when the foot coordinate does not. Always establish exact actor footprint before treating a frame as exclusive evidence.

**Open questions:** actor 11's animation draw-phase versus reported limb cursors; runtime local-to-global palette overrides; cel horizontal mirroring; scaling/mask state; object-state interactions; natural room-entry scripts. Each requires explicit evidence.

## Fast validation ladder

1. **Unmodified baseline:** run `python -B -m unittest tests.test_classic_costume -v` where import layout permits; otherwise `python -B -m unittest discover -s tests -p test_classic_costume.py -v`. Verify existing 16-color Room 23 fixture.
2. **Format smoke:** `DCOS[142]` is linked and `ClassicCostume` accepts the full, edition-pinned `0x59` chunk; enumerate its palette slots, limb tables, cel offsets, bounds, and RLE. Test 32-color synthetic patterns including zero-length extension, slot 0, maximal slot 31, truncated run, and run overflowing a cel.
3. **Single-frame scenery:** choose one captured frame with scene actor 11 demonstrably on screen and Guybrush demonstrably absent from rendered pixels. Render actor 11 using archive cels and captured state. Compare `320 × 144` *indices*, not resized RGB, and log first mismatch with X/Y, predicted/observed indices, masks and actor state. Do not use front pixels as costume inputs.
4. **Sequence:** perform the same independent render on several different camera positions and scenery animation poses; validation must not fit a unique phase/offset per frame.
5. **Guybrush scale:** use actual `smallCostumeScaleTable` and phase logic; compare scaled 150/155 candidates to observed front, then apply ZP01. Preserve native-scale Room 23 result.
6. **Final composition:** only if previous ladders pass, render complete scene, export with per-layer provenance, record both indexed and display limitations.

**A failed test with a clear first-difference diagnostic is preferable to silently filling missing pixels with ScummVM's final front buffer.** Keep any synthetic stress cases explicitly classified as synthetic.

## Local commands for the Work session

```powershell
$repo = 'F:/Dev/SCUMMBUCKET/SOURCE/ScummBucket'
$fix = 'F:/Dev/SCUMMBUCKET/FIXTURE'
git -C $repo status --short --branch
git -C $repo fetch origin
git -C $repo merge --ff-only origin/research/p4-engine-palette-trace
python -B "$repo/tools/room7_work_preflight.py" --root 'F:/Dev/SCUMMBUCKET' --hash-frames
python -B -m unittest discover -s "$repo/tests" -p 'test_room7_work_preflight.py' -v
```

Do not run the merge automatically if the working tree is dirty, diverged, or the repository identity is wrong. The command sequence is an operator procedure, not proof a machine is currently in that state.
