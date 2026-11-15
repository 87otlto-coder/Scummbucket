# P4 ordered event compositor — incremental research checkpoint

15 November 2026. Branch: research/p5-cross-room-reconstruction.
This remains the P4 background-animation milestone, NOT the roadmap's P5 audio phase.

## Source/archive smoke performed outside the repository

Read-only private original-archive check against the user-supplied mi2.zip
containing MONKEY2.000 and MONKEY2.001. Both archive entries passed ZIP CRC.
The source files are original DOS VGA resources, not repository test fixtures.

- MONKEY2.000 SHA-256: cde7aa8980317e3a750fbb3b49884cdddaf1ff3d4231a0c840b22cceed9033f1
- MONKEY2.001 SHA-256: ad045372e0d49626503bb50fca29a687ec8e01ef75d9b8bca702a366d143819e
- Room 7, object 57: one stored IM01 state (8x16), one decoded, zero failures; one
  codec-68 strip and an all-zero ZP01 source mask. All 128 pixels opaque.
- Room 34, object 358: sixteen stored IM01-IM10 states (56x40), all sixteen
  decoded; zero decode failures. IM01-IM0F each have 923 opaque pixels and 1,317
  transparent pixels; IM10 has 2,240 opaque pixels and no transparent pixels.
  The sixteen ZP state masks are decoded separately.
- No original binary resource bytes or derived images were committed.

**Important limitation:** The above real-game smoke was performed by a
temporary independent Python harness mirroring the existing source strip
and RLE-mask decoding rules, NOT by executing the repository's complete
tools.probe_native_object_state against a checked-out game directory.
The latter should be rerun privately in the canonical F-drive workspace.
This confirms source syntax/decodability under those algorithms only.
It proves neither runtime-selected state nor runtime placement/order/timing.
Room 34 runtime holdout remains deferred.

## Implemented source-only engine seam

Added scummbucket/ordered_scene_events.py, a UI-independent, indexed
event iterator: render_scene_event_frames(scene, object_states, costumes,
events, viewport=...).

- Requires explicit, strictly increasing (tick, order) event ordering and
  provenance for every event: engine_observed, inferred, manual, or synthetic.
  No passage of engine time or animation advance is inferred from tick gaps.
- palette_patch modifies only the 256-entry RGB CLUT; source-index bytes remain
  unchanged when the palette changes.
- object_state chooses an already decoded (object ID, IMxx) state and an
  explicitly supplied room-pixel origin; object_hide removes that selection.
  Neither selection nor removal implies a SCUMM script execution.
- frame requires an explicit ordered draw list. Each object layer specifies a
  room occlusion plane (0 means none). Each actor layer supplies its original
  recorded draw-phase row; it delegates to the existing COST compositor,
  including its existing recorded palette override handling.
- Each frame starts from the same archive-derived indexed background and
  draws only listed layers. Prior selected objects are not automatically added
  to the draw order. No guessed object visibility, engine actor order, native
  timing, camera movement or source ZPxx interpretation is introduced.
- Returns native indices, live palette bytes, independent hashes, draw count,
  cumulative evidence labels and scene_fidelity=NOT VALIDATED. Does not write
  images or resource bytes. Source bounds, output budgets and unknown fields
  fail closed with coded diagnostics where feasible.

## Test and acceptance boundaries

Seven synthetic source-only tests cover indexed/palette independence,
nonautomatic object painting, state selection/hide, room-mask occlusion,
clipped viewport, explicit actor/object order, invalid state/order/provenance,
error propagation and non-mutating source buffers. The actor integration test
mocks the COST draw method, so it is a delegation contract test, NOT complete
cross-mechanism original-runtime fidelity.

Local temporary harness used a minimal stand-in for native object painting and
actor-import availability. It passed seven tests. Windows source-only CI
against actual repository modules is the required next independent gate.

Next: verify the full Windows CI result; run the repository object probe on
the operator's F-drive original DOS VGA fixture; then import observed Room 7
frame/palette/actor draw events into this schema (without invented timings),
and compare indexed outputs to independent original engine captures. Do not
expand the scope into Room12's residuals or Room34 runtime holdout.

Keep PR #17 draft, unmerged. No GitHub Actions artifact uploads and no game
assets in commits. Windows-only CI per standing project policy.
