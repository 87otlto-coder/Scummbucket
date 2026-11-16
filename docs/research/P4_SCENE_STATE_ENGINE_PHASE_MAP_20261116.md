# P4 — MI2 v5 object/actor/palette execution-phase source map

16 November 2026. **Source-backed research only.** No new ScummVM executable,
native capture, CI validation of a new implementation, script replay, or scene
fidelity claim in this session.

## Inputs and evidence

- Pinned reference: [ScummVM v2026.4.0](https://github.com/scummvm/scummvm/tree/v2026.4.0/engines/scumm)
  (original ScummVM code is referenced, never copied or embedded).
- Game edition: original DOS VGA Monkey Island 2; MONKEY2.000
  SHA-256 `cde7aa8980317e3a750fbb3b49884cdddaf1ff3d4231a0c840b22cceed9033f1`,
  MONKEY2.001 SHA-256 `ad045372e0d49626503bb50fca29a687ec8e01ef75d9b8bca702a366d143819e`.
- Existing validated runtime baselines are described in
  [P4 complete actor-state](P4_COMPLETE_ACTOR_STATE_20261116.md) and
  [native animation-step differential](P4_NATIVE_ANIMATION_STEPS_20261116.md).
  No earlier evidence was changed by this analysis.

## 1. Two distinct v5 object-state commands

**`o5_drawObject`**:
[script_v5.cpp L1031–1129](https://github.com/scummvm/scummvm/blob/v2026.4.0/engines/scumm/script_v5.cpp#L1031-L1129).
For the non-small-header v5 code path, the requested state defaults to 1,
and the subopcode optionally supplies a new state or a new location.
The function resolves an existing local object, optionally changes its
room coordinates in units of 8 pixels, adds that local object to the
draw queue, and **sets the state of every other local object with exactly
the same X/Y/width/height to zero**, before assigning the selected state.
The same object can temporarily be reset in that loop and then assigned
its requested state. The draw call occurs later, not at the mutation point.
This is a source-backed peer-state effect, not evidence of an autonomous loop.

**`o5_setState`**:
[script_v5.cpp L2731–2752](https://github.com/scummvm/scummvm/blob/v2026.4.0/engines/scumm/script_v5.cpp#L2731-L2752).
This writes the selected global object state, marks that object's strips
dirty via `markObjectRectAsDirty`, and clears the queued object draws
if `_bgNeedsRedraw` is set. This is *not* identical to the peer-reset
and drawing-queue semantics of `o5_drawObject`. Distinguish the opcode
and actual affected object IDs in all future event metadata.

**Important:** [object.cpp L1679–1710](https://github.com/scummvm/scummvm/blob/v2026.4.0/engines/scumm/object.cpp#L1679-L1710)
contains a separate `setObjectState` helper whose automatic next/random
state substitutions are guarded by `_game.version >= 7`. Do not project
those v7 substitutions onto MI2 v5.

## 2. State is not equivalent to a drawn image

- [object.cpp L1165–1185](https://github.com/scummvm/scummvm/blob/v2026.4.0/engines/scumm/object.cpp#L1165-L1185):
  the engine synchronizes local objects from global state in
  `updateObjectStates`, and queued objects render through
  `processDrawQue` in the queue's stored order.
- [object.cpp L600–645](https://github.com/scummvm/scummvm/blob/v2026.4.0/engines/scumm/object.cpp#L600-L645):
  normal MI2 room-object redraw traverses **descending local-object slots**,
  tests state `& 0x0F`, and follows an optional parent-state chain before
  actually invoking the drawer. The parent is a *local object slot*;
  decoding a CDHD parent byte does not automatically identify a global object.
- [object.cpp L1233–1255](https://github.com/scummvm/scummvm/blob/v2026.4.0/engines/scumm/object.cpp#L1233-L1255):
  dirty marking identifies strips to restore and requests a background
  redraw. A state-change opcode does not imply an immediately presented
  image or the existence of a specific new drawn `IMxx` state.
- [object.cpp L1384–1433](https://github.com/scummvm/scummvm/blob/v2026.4.0/engines/scumm/object.cpp#L1384-L1433):
  the source image lookup recognizes tags `IM00` through `IM10`,
  but *normal* v5 full-room drawing filters states whose low four
  bits are zero. Hence `state=16` is filtered from the regular room-object
  pass, even though `IM10` can exist as a stored image. An explicit
  queued-object draw calls `drawObject` without that same outer filter.
  The resulting on-screen behavior depends on the exact path and must be
  tested, not inferred as automatic hide or automatic display.
- Previously verified [Room 34 object 358 scripts](P1_ROOM34_OBJECT_BEHAVIOR.md)
  clamp a computed value of 16 down to 15. **This is compatible with** the
  state-16 visibility boundary but does **not prove why** the script
  authors chose the clamp or whether that state ever renders elsewhere.

## 3. Source ordering in a v5 frame

Follow [scumm.cpp L3269–3350](https://github.com/scummvm/scummvm/blob/v2026.4.0/engines/scumm/scumm.cpp#L3269-L3350):
1. Resume scheduled scripts, then process sentence scripts.
2. In a nonzero room, walk actors, move the camera, and sync local
   object states.
3. `scummLoop_handleDrawing` runs `redrawBGAreas` as needed and
   then `processDrawQue`:
   [scumm.cpp L4102–4110](https://github.com/scummvm/scummvm/blob/v2026.4.0/engines/scumm/scumm.cpp#L4102-L4110).
   Background restoration also invokes `drawRoomObjects`:
   [gfx.cpp L1100–1155](https://github.com/scummvm/scummvm/blob/v2026.4.0/engines/scumm/gfx.cpp#L1100-L1155).
4. `scummLoop_handleActors` resets actor backgrounds and processes actors:
   [scumm.cpp L4142–4153](https://github.com/scummvm/scummvm/blob/v2026.4.0/engines/scumm/scumm.cpp#L4142-L4153).
   In v5 the actor is **drawn before advancing its costume**:
   [actor.cpp L2392–2448](https://github.com/scummvm/scummvm/blob/v2026.4.0/engines/scumm/actor.cpp#L2392-L2448).
   Sorting uses `Y - layer*2000` and the engine's historical comparison
   algorithm, not a generic stable Y sort.
5. Effects call `cyclePalette` then `palManipulate`:
   [scumm.cpp L4155–4164](https://github.com/scummvm/scummvm/blob/v2026.4.0/engines/scumm/scumm.cpp#L4155-L4164).
   The current palette may therefore change without changing frontbuffer
   *indices*. Palette-cycling counter and display palette are separate inputs.
6. The configured `VAR_MAIN_SCRIPT` runs **after the above draw/effects**
   but before `updatePalette` and `drawDirtyScreenParts`.
   A state change requested in that script may not have gone through
   `processDrawQue` by that presentation. Record exact phase, not
   an inferred universal one-tick delay; other side effects may exist.

Thus an engine-frame identity alone does not determine whether an
object event belongs to the already painted frame, the next frame,
or merely an unapplied state mutation. The existing indexed event
compositor must continue to require explicit observed draw order rather
than inventing a per-tick order.

## 4. Capture fields to prepare for later Windows verification

**Source-only proposed evidence contract** (not an implemented recorder):

| Event phase | Required observed data | What it resolves |
|---|---|---|
| `script_object_mutation` | engine tick, script slot/number, opcode start, command family, original object ID, requested state/placement, old/new global state for target and same-rectangle peers | Distinguishes `drawObject` peer resets from `setState` |
| `room_object_snapshot` | every local slot with object ID, state, current x/y/w/h, parent slot, parentstate, original source metadata ID | Visibility, actual room-local slot order, runtime relocation |
| `object_draw_attempt` | execution phase, queue vs background-pass origin, local slot, state, image lookup success, clip, dirty-strip range, actual draw call order | Separates state, eligibility and painting |
| `actor_draw_and_advance` | pre-draw actor state, actual draw rows, after-animation cursors, speed/progress, costume, clipping plane and palette overrides | Avoids using a post-animation cel as the same tick's displayed pose |
| `palette_effect` | cycle counters/delay/flags, room/current CLUT before/after, manipulator state, timer values and phase | Distinguishes CLUT cycling/fades from indexed pixel changes |
| `presented_indexed_front` | camera rectangle, raw-front hash, room/tick/phase, source game and executable hashes | Independent native-index acceptance |

The later investigator should instrument **only two initially relevant
channels**: object mutations (including changed peers), and the actual
object draw queue/full-pass results. Reuse existing actor/palette/frontbuffer
channels where available. Never force redraw, change ordering, or insert
extra actor updates. All captures and binaries belong in FIXTURE or TOOLS,
not Git.

## 5. Discriminating future comparisons

- Verify default versus runtime-relocated exact-rectangle peers;
  do not treat simple overlapping rectangles as equivalent to exact equality.
- Compare `o5_drawObject` versus `o5_setState` at the same script point,
  including zero-state peers, dirty flags and queue behavior.
- Check normal-pass `state=16` versus explicitly queued `IM10` selection
  *only when original gameplay supplies a valid path*. Do not inject states
  into the canonical fidelity capture.
- Preserve actor layer/order and palette phase separately and compare all
  native-index frontbuffer positions, not only visibly changed frames.
- A structurally valid archive record is **not** a validated runtime
  object transition or authentic frame duration.

## Evidence boundaries

`source_finding`: pinned C++ control flow above.
`archive_decoded`: room/object structural relationships in the companion
exact-rectangle candidate inventory.
`engine_observed`: existing Room 7 private captures only; no new data.
`hypothesis`: predicted graphical consequences of state=16, shared-peer
resets, and main-script phase delay pending capture.

No original game resources, third-party source files, private captures,
binaries, extracted pixels or speculative timelines were added.
