# P4 native animation-call differential — 16 November 2026

**1,132/1,132 observed calls match the bounded v5 model.**
This advances actual runtime validation beyond the earlier synthetic-only model.

## Recorder and provenance

tools/prepare_animation_step_capture.py consumes actor-state overlay SHA-256
70843093326d5789823e3a3aab42bad1edf61ffe8be2f420f0912c0f1ec52945.
It adds read-only logs immediately before/after Actor::animateCostume,
without invoking extra updates or modifying normal draw/animate order.

Each anim_step row records phase, actor/costume, progress/speed, stopped bits,
animation/sound counters and 16 cursor/start/end/limb-frame quadruples.
Execution ranges are observed, not guessed from a logical animation selector.

The patched actor.cpp compiled and linked in a fresh private TOOLS folder,
using the original 528-object recipe with the new actor.o. This is a
direct-object relink, not a clean rebuild; original files were not modified.
Its native --version probe succeeded.
- actor.cpp SHA-256: c216a00abf59f7d6ce0c3be6a251935fe868a67b5b97be14b5f1f8efeb135553
- executable SHA-256: c96c23d93d5685be2af23289f66b83512b7947242c07bc37245eb00b9f9fd835
- private build: TOOLS/P4-AnimationStep-20261116-a
- capture: FIXTURE/CAPTURES/Room7/actor-state-ef14fd21090e45468c79d9aab416e637

The original Room 7 save loaded with compatible AdLib settings. Two ordinary
point-and-click movements exercised right/left walking. No debugger, injected
path or state-changing instrumentation was used. The process closed normally.

## Actual execution differential

tools/audit_animation_steps.py checks raw/frame identity, pairs before/after
records and compares archive command execution from each before observation
against its independent after observation.

| Measure | Result |
| --- | ---: |
| Indexed frames | 566 |
| Actor 1 / COST 1 calls | 566 |
| Actor 11 / COST 142 calls | 566 |
| Matched calls | 1,132 / 1,132 |
| Limb cursor comparisons | 18,112 |
| Model mismatches / errors | 0 / 0 |
| Updates / cel changes | 1,132 / 25 |
| Observed animation speeds | 0 only |
| Sound / animation-counter changes | 0 / 0 |
| Actor 1 / 11 cursor combinations | 7 / 1 |

The model also compares preservation of ranges, limb-frame values, costume,
stopped state, speed and final progress/counters. This validates sampled
one-call advancement at speed zero. It does not prove autonomous initialization,
script decisions, nonzero cadence, stop/resume, sound events or wall-clock timing.

## Separate indexed-scene holdout

The complete-state compositor was rerun unchanged on this second recorder
capture: **566/566 indexed fronts match**, over 26,081,280 pixel observations.
Background and observed palette transport differences are zero.
- Draw-only control: 555,855 discrepancies.
- Mask-disabled control: 95,450.
- Actors shifted right one pixel: 797,096.
- Pre-redraw states: 1,132; actual draws: 687; states without draws: 445.
- Observed final palettes: 91.

Across the two new captures, 1,534/1,534 samples match (70,686,720 pixel
observations including repeated buffers). Repeated idle pixels are not unique
poses. This is additional Room 7 evidence, not acceptance for a new room.
Historical Room 7/12 residuals remain unchanged.

## Source-backed correction and controls

Pinned actor.h CostumeData declares a uint16 animation counter, byte sound
counter, and byte actor progress/speed. Existing Python counter increments
were unbounded. advance now wraps counters at 16/8 bits, with synthetic
overflow tests. No native counter wrap or event was observed in this capture.

scummbucket/classic_animation_step.py models byte-progress increment,
threshold gating and at most one COST update per observed call. Synthetic
tests cover nonzero thresholds, progress wrap, event skipping, counter wrap,
terminal one-shot/stopped state, unchanged inputs, malformed identities,
missing pairs and explicit mismatches. Patcher tests preserve exactly one
original increment. Actual full Windows local suite: **500 tests run,
16 skipped, no failures**. Later hosted results are tracked in PR #18.

## Private results and next work

Under FIXTURE/REPORTS/P5:
- animation-step-indexed-20261116-a.json
- animation-step-audit-20261116-a.json
- animation-step-scene-holdout-20261116-a.json
- animation-step-{compile,link,tests}-20261116-a.log

All captures, third-party overlays, object files, binaries and original
resources stay outside Git/CI. Source tools, synthetic tests and aggregate
findings are public checkpoints. No workflows/artifact uploads were added.

Next broaden source COST frame/cel coverage while preserving failures.
Acquire nonzero-speed/event/stop-resume observations as separate gates.
Live object-state selection/order/timing remains unverified. Room 12
residuals and Room 34 runtime stay deferred.
