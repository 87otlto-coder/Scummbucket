# ScummBucket status — 16 November 2026

**Current milestone: P4 background animation. Overall project incomplete.**
Primary edition: Monkey Island 2, original DOS VGA. No new edition/platform
compatibility or automatic SCUMM script interpretation is claimed.

## Review and continuity

- Branch: research/p4-observed-event-replay.
- Draft PR: https://github.com/87otlto-coder/Scummbucket/pull/18
- Base: research/p5-cross-room-reconstruction at 8b62784. Its historical P5
  name does not rename the roadmap's P5 audio milestone.
- Main and existing PRs #8/#17 remain unchanged and unmerged.
- Checkpoint using real upstream ancestry; never push the local synthetic
  snapshot history over upstream.

## Latest native validation

1. Complete pre-redraw actor state plus archive backgrounds/COST cels/masks
   matches **968/968 original Room 7 indexed samples**. No cached poses,
   reference-pixel copies, palette fitting or interpolation. There are
   25 distinct indexed fronts, one camera rectangle, 96 observed palettes
   and 44,605,440 pixel observations including repeated frames.
2. An unchanged-compositor holdout matches **566/566 additional indexed
   fronts**, 26,081,280 pixel observations. Both captures include ordinary
   right/left movement and actors without draw operations.
3. Independent before/after animation state matches the bounded v5 model
   for **1,132/1,132 calls**, 18,112 limb cursor comparisons and 25 cel changes.
   All sampled speeds were zero; no sound/counter events were observed.
   Initialization, nonzero cadence, events and stop/resume remain unverified.
4. Archive object corpus: **1,047/1,047 stored states**, 595 objects, 110 rooms,
   3,356,800 pixels, 25 codec numbers. Native/legacy RGBA/mask assembly agrees
   but shares low-level decoders: consistency, not independent runtime fidelity.
5. A private offline source/event/COST package independently re-decodes room
   images/masks and reproduces all 968 candidates without game/capture access.
   Original engine reference buffers are not revalidated offline.
6. Archive-only linked COST audit independently reproduced: 162 costumes,
   3,462 consistent defined selectors, 12 failed selectors resolving to one
   COST 129 limb/command reference. Five zero-area references accept movement
   without drawing pixels. A structured, source-hashed metadata summary is
   retained at docs/validation/P4_COSTUME_CORPUS_INDEPENDENT_20261116.json.
   The committed CLI has not yet been run on the private original archive.

Actual earlier full local Windows suite after animation-step changes: **500 tests,
16 skipped, no failures**. Latest hosted Windows CI after repeated-fault grouping:
**507 tests run, 15 skipped, no failures**, no CI artifacts.
No workflow changes. Optional private/environment skips remain.

## Evidence

- [Complete actor-state capture and pixels](docs/research/P4_COMPLETE_ACTOR_STATE_20261116.md)
- [Native animation calls and holdout](docs/research/P4_NATIVE_ANIMATION_STEPS_20261116.md)
- [Object corpus and redraw source research](docs/research/P4_CORPUS_AND_REDRAW_RESEARCH_20261115.md)
- [Earlier event/offline-package foundation](docs/research/P4_OBSERVED_EVENT_REPLAY_20261115.md)
- [COST archive selector corpus and remaining failures](docs/research/P4_COSTUME_CORPUS_20261116.md)
- [Independent COST corpus metadata summary](docs/validation/P4_COSTUME_CORPUS_INDEPENDENT_20261116.json)
- [Zero-area-cel source correction](docs/research/P4_COSTUME_ZERO_AREA_CEL_20261116.md)

The old Room 7 capture remains 170/228 exact; old Room 12 remains 232/244.
Their missing channels cannot be retroactively supplied from new captures.
Room 34 has source decoding but no live state/order/timing acceptance.

## Roadmap boundaries

| Phase | Current boundary |
| --- | --- |
| P0 research | Substantial edition-specific archive/source/runtime evidence. |
| P1 archives | Read-only detection, inventory, extraction and provenance implemented; visible unsupported/errors retained. |
| P2 images | Representative rendering and broad object source decoding validated; all-edition accuracy unclaimed. |
| P3 costumes | Native composition, zero-area movement and bounded speed-zero advancement tested; source-only selector corpus has 12 explicit COST 129 failures. General init/timing/events incomplete. |
| P4 scenery | Room 7 observed-state palette/scenery/actor/mask composition verified. Live object-state transitions and general scene-state acquisition incomplete. |
| P5 audio | Not advanced in this work. |
| P6 explorer | Deferred until engine acceptance supports it. |
| P7 enhancement | Deferred; native fidelity first; BigR stays separate. |
| P8 extensions | Deferred; no new game/platform acceptance. |

Next run committed source COST corpus tool privately, investigate COST 129's
remaining 12 bounded-RLE failures, then close live object-state/order/timing gaps. Nonzero-speed/event/stop-resume
native checks are separate gates. Do not build a general interpreter.

## Workspace

Writable source:
C:\Users\87otl\Documents\ChatGPT\ScummBucket\SOURCE\ScummBucket-P4-Continuation.
Private results/builds: sibling FIXTURE and TOOLS. F: originals were read only.
The Windows interruption ended: private source/build/corpus hashes were
recovered, native linking/capture resumed. Corpus report SHA-256:
6595ddb3034e6401c10868ffc3938bc3d9e8143c348e48203a781cdcbefa1979.
Keep copyrighted resources, private raw capture rows, third-party overlays,
objects and executables out of Git. Follow AGENTS and standing CI policy.
