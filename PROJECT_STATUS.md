# ScummBucket status â€” 15 November 2026

**Current milestone: P4 background animation. Overall project incomplete.**
Primary validated edition: Monkey Island 2, original DOS VGA. This checkpoint
does not extend compatibility to MI1, other platforms, or Curse of Monkey Island.

## Expanded research checkpoint

Original archive corpus audit passed **1,047/1,047 stored states** across
**595 objects / 110 rooms**, covering 3,356,800 pixels, with zero RGBA/mask
assembly disagreements. Both paths share low-level decoders; runtime fidelity
and state selection remain unverified. Six new targeted synthetic tests passed.

Pinned ScummVM source confirms that the existing draw hook follows a redraw
early return. A new pre-gate actor-state overlay passed native syntax and
object compilation, but **linking/runtime capture are not validated**.
The Windows execution environment became unavailable before the next step.
Private outputs were not subsequently re-readable; observed aggregates and
source/tests were recovered into GitHub. See
[corpus and redraw research](docs/research/P4_CORPUS_AND_REDRAW_RESEARCH_20261115.md).
Earlier validation totals below are retained as historical checkpoints.

## Current review checkpoint

- Branch: `research/p4-observed-event-replay`.
- Draft PR: https://github.com/87otlto-coder/Scummbucket/pull/18
- Base: `research/p5-cross-room-reconstruction` at `8b62784`.
  That branch's P5 name is historical; it is not the roadmap's audio milestone.
- No merge into main. Existing PRs #8 and #17 are untouched.
- Detailed evidence, private paths, reproduction commands and limitations:
  [Observed event replay checkpoint](docs/research/P4_OBSERVED_EVENT_REPLAY_20261115.md).

## Implemented in this increment

1. Rebind existing indexed capture records to their raw SHA-256, room/tick,
   camera rectangle, ordered actor draws, source background and final palette.
2. Replay those explicit snapshots through the reusable native event compositor.
   Screen-coordinate actor anchors are kept separate from room-coordinate
   background/mask cropping. No missing actors or object visibility are guessed.
3. Package source room data, masks, palettes, required COST resources and events
   for offline replay. Verify inventory/hashes, independently re-decode room
   graphics/masks, and reproduce candidate frames without game/capture access.
4. Detect archive changes between inspection, costume extraction and scene loading.

## Verification actually performed

- Actual Windows Python suite: **468 tests run, 16 skipped, no failures**.
  Includes 13 new synthetic integration/provenance/package tests. Skips remain
  explicit optional-private-fixture/environment limits.
- Original source object probes: Room 7 object 57 **1/1 states decoded**;
  Room 34 object 358 **16/16 decoded**, no failed/unsupported states.
  This is archive decoding, not observed object animation/state selection.
- Room 7 original indexed capture: **170/228 exact frames**;
  **15,718 remaining native-index mismatches** over 10,506,240 pixel observations.
  Source backgrounds match all 228 samples. Every non-exact sample lacks
  actor 1's draw record; every sample containing that record is exact.
- Controls: disabling masks produces 29,071 errors; shifting all actors right
  one pixel produces 95,381. Observed palette snapshots round-trip exactly;
  palette-cycle timing is not independently predicted by this new adapter.
- Private offline package reproduces all **228 candidate frames**, including
  failures. Its successful integrity/replay result retains **PARTIAL** scene
  acceptance. It does not revalidate raw engine references that are not packaged.
- First new-code hosted Windows CI passed. Check PR #18 for the final-head run;
  never infer hosted success from local tests alone. No artifact uploads.

## Remaining milestone boundaries

| Milestone | Current evidence / remaining boundary |
| --- | --- |
| P0 format research | Substantial v5 research; compatibility remains edition-specific. |
| P1 archive reader | Implemented read-only detection, inventory, extraction and provenance; retain visible unsupported/error cases. |
| P2 graphics | Background/object decoders exist; all-resource/all-edition fidelity is not established. |
| P3 characters | COST decoding/composition verified on representative captures; general animation timing/execution incomplete. |
| P4 background animation | Room 7 palette/scenery mechanisms verified on prior representative exports; reusable snapshot playback now tested. Complete general scene-state acquisition and object-runtime interaction remain incomplete. |
| P5 audio | Not advanced in this pass. |
| P6 explorer UI | Deferred until validated engine capabilities support it. |
| P7 HD rendering | Deferred; fidelity remains the priority. BigR is a separate project. |
| P8 extensions | Deferred; no additional game/edition support claimed. |

Room 12 retains its previously reported 12 absent-draw failures (232/244 exact).
Room 34 runtime holdout remains deferred. Do not combine partial results into
a blanket claim of complete background-animation support.

## Next discriminating work

Capture complete scene-state at indexed frontbuffer phase, including visible
actors that did not redraw, or independently record dirty-region/framebuffer
updates. Draw-operation records are not guaranteed to enumerate every visible
actor. Establish the source-backed rendering semantics before any persistence
implementation; do not fit a last-pose correction to known failures.

Then reverify every sample, preserve the existing partial baseline, and connect
observed object states/order/masks to the event compositor. Native timing,
script-triggered object transitions and independent general-room acceptance
remain separate gates. Do not introduce a general SCUMM interpreter.

## Workspace continuity

Writable source: `C:\Users\87otl\Documents\ChatGPT\ScummBucket\SOURCE\ScummBucket-P4-Continuation`.
Private generated results: sibling `FIXTURE\REPORTS\P5` and `FIXTURE\OUTPUT\P5`.
F: game/capture inputs were read only; its canonical source checkout could not
be opened. Older local worktrees/untracked files were not altered.

The continuation checkout has a local synthetic snapshot history. **Never push
that history over upstream.** GitHub commits use real upstream ancestry through
the connected tools; GitHub is the durable source/research checkpoint. Keep
original game archives, COST binaries, replay packages and private captures
outside Git. See AGENTS.md and the standing project/CI instructions.
