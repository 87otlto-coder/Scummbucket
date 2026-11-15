# P4 corpus validation and redraw-state research — 15 November 2026

Baseline: cccc373c53ea19476d8872e917db74e3374e26a7.
Branch research/p4-observed-event-replay; draft PR #18. No main merge.

## Original archive corpus actually executed

tools/audit_object_state_corpus.py inspected the immutable original DOS VGA
MONKEY2 pair once, rechecked both source fingerprints, and attempted every
stored object image state in the room inventory.

| Measure | Result |
| --- | ---: |
| Rooms inspected | 110 |
| Object records | 1,145 |
| Objects with stored image states | 595 |
| Object records without stored states | 550 |
| Stored states attempted / consistent | 1,047 / 1,047 |
| Failed / unsupported states | 0 / 0 |
| Decoded pixels | 3,356,800 |
| Native-to-legacy RGBA byte differences | 0 |
| Native-to-legacy mask pixel differences | 0 |
| Distinct strip codec numbers exercised | 25 |

See ../validation/P4_OBJECT_CORPUS_20261115.json for the observed aggregate
and strip-codec counts. Source index/opacity hashes and mask hashes are
recorded per state in the private report. No extracted pixels are emitted.

The differential compares native indices plus opacity mapped through the
archive CLUT against the existing RGBA decoder's PNG, and native masks
against its separated mask PNGs. **Both paths share low-level strip and
RLE decoders. This establishes high-level consistency and broad actual
source decodability, not independent codec correctness or runtime fidelity.**
No object selection, script execution, placement, draw order or timing was
observed in this corpus run. The 550 records without stored states are
reported explicitly; they are not fabricated as missing decodes.

Three synthetic corpus tests passed locally: both states/opacity/masks and
input immutability, one unsupported state beside a retained success, and
changed-archive rejection before decoding.

## Source-backed redraw finding

Private pinned ScummVM source:
TOOLS/ScummVM-P4-CrossRoom-767b677319ce4691953ca06dcf67811c
ScummVM version 2026.4.0. The relevant actor.cpp input SHA-256 is
0c9e75724d42d2d0ead63a31cfecd42e3ca091281848d9de031d49cd9a091c3b.

Source locations in that pinned build:
- actor.cpp:2314 processActors gathers actors in the current room, applies
  its historical sorting algorithm, and calls draw before animate for v5.
- actor.cpp:2522 drawActorCostume returns for costume zero, then returns
  when needRedraw is false. The existing draw_actor hook occurs after
  those returns and after normal scale/renderer preparation.
- actor.cpp:2573 prepareDrawActorCostume maps world position to screen
  anchor using virtual-screen xstart and actor elevation, and resolves
  the selected clipping plane through force-clip / never-clip / walkbox.
- actor.cpp:3108 resetActorBgs conditionally restores actor-background
  strips using usage bits and redraw/background-reset flags.
- scumm.cpp:4258 the v5 actor phase resets backgrounds before processing
  actors. The indexed recorder runs after actor processing, effects,
  palette update and dirty-screen output; current cursor state at that
  later point must not be assumed to be the previously displayed pose.

**Confirmed source finding:** the original draw log omits actors that
return at the redraw gate. Absence of a draw row therefore does not mean
absence of visible pixels. This supports the capture-completeness concern
identified in Room 7/12. It does not independently prove a particular
cached-pose correction or resolve all historical residual pixels.

## New bounded instrumentation preparation

tools/prepare_actor_state_capture.py generates a private actor.cpp overlay
only after exact source SHA-256 verification. It adds state_actor records
at the drawActorCostume entry, before the redraw gate, for the instrumented
MI2 v5 Rooms 7/12. It does not force redraw, advance animation, change
flags/cursors or invoke renderer preparation.

Records contain 27 explicit scalar fields plus 16 cursors and 32 palette
overrides: actor/world/screen coordinates, elevation, visibility, redraw
flags, scales, facing, costume/frame, walkbox/clip fields, layer, animation
progress/speed, stopped bits, selected plane, back-buffer/shadow mode and
last drawn vertical bounds. These rows are pre-draw actor-state candidates
in actual process order, **not draw operations and not automatic proof
of framebuffer presence**. Existing draw_actor rows remain distinct.

This observes only actors for which processActors calls drawActorCostume;
it is not a universal inventory of every engine actor or object. State
before scale preparation can differ from subsequent actual draw state.
Runtime comparison with actual draw rows is mandatory before using these
snapshots for reconstruction.

Three synthetic instrumentation tests passed locally: early-gate placement
and no forced rendering; pin failure before output creation; exclusive
non-overwriting overlay with explicit unverified-runtime status.

## Native checks and interruption — do not overstate

- Overlay actor.cpp hash observed:
  70843093326d5789823e3a3aab42bad1edf61ffe8be2f420f0912c0f1ec52945.
- Native Windows g++ syntax check passed.
- The same actor.cpp compiled to actor.o successfully.
- These checks used the existing pinned configuration, ENABLE_SCUMM as
  STATIC_PLUGIN, Windows/SDL2 defines and source/include paths.
- No newly linked executable was accepted; no version probe or runtime
  capture was obtained from this overlay.
- An experimental direct relink against 528 original object files failed
  because the response file contained literal backslash-n separators.
  The intended correction is to generate real newlines (e.g. chr(10)),
  but the execution transport disconnected before that correction ran.
  Do not treat a partial executable or any copied old executable as valid.
- Initial overlay preparation hit a CRLF/anchor mismatch; normalization
  fixed it, then the private syntax and compile checks passed. The failed
  first compile named the absent overlay file; those logs were preserved.

The Windows environment then became unavailable. Shell retries failed with
exec-server transport disconnected / recovery timed out. No native action
or capture can continue until a usable Windows environment returns.
Source/test text and observed aggregate findings were recovered from this
session's tool calls for GitHub preservation. Private outputs were not
subsequently readable; do not claim their final checksum or durable backup.

Last prior full local suite: 468 tests, 16 skipped, no failures.
New six targeted tests passed before environment loss. Hosted Windows CI
must independently validate the recovered source/test files.

Private locations (ChatGPT ScummBucket workspace, not F:):
- FIXTURE/REPORTS/P5/object-corpus-20261115-a.json
- FIXTURE/REPORTS/P5/actor-state-syntax-20261115-{a,b}.log
- FIXTURE/REPORTS/P5/actor-state-compile-20261115-a.log
- FIXTURE/REPORTS/P5/actor-state-link-20261115-a.log
- TOOLS/P4-ActorState-20261115-a/actor.cpp, actor.o, overlay.json,
  object-inputs.json and link.rsp.

No original F: inputs were changed. No private source, object files,
executables, game resources, pixel exports or capture records are committed.

## Reproduction / next work

~~~powershell
Set-Location -LiteralPath 'C:\Users\87otl\Documents\ChatGPT\ScummBucket\SOURCE\ScummBucket-P4-Continuation'
$game = 'F:\Dev\SCUMMBUCKET\FIXTURE\GAMES\MonkeyIsland2_DOS_VGA'
# Choose new, non-existing outputs; no overwrite.
python -B -m tools.audit_object_state_corpus --game $game --output 'C:\Users\87otl\Documents\ChatGPT\ScummBucket\FIXTURE\REPORTS\P5\object-corpus-NEW.json'
python -B -m tools.prepare_actor_state_capture 'F:\Dev\SCUMMBUCKET\TOOLS\ScummVM-P4-CrossRoom-767b677319ce4691953ca06dcf67811c' 'C:\Users\87otl\Documents\ChatGPT\ScummBucket\TOOLS\P4-ActorState-NEW'
python -B -m unittest discover -s tests -v
~~~

Next: restore native Windows execution; verify private output hashes; finish
a properly logged fresh link with original-object provenance; check the
new executable digest/version; implement/validate state_actor parsing; then
capture ordinary-input Room 7 behavior including non-redraw samples.
Compare pre-draw snapshots against actual draw rows on overlapping ticks.
Only then test archive reconstruction on non-redraw frames without a fitted
last-pose insertion. Room 12 residuals and Room 34 runtime remain deferred.
