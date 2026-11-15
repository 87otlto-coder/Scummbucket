# Generalised scene reconstruction: first execution checkpoint

15 November 2026. Primary edition: Monkey Island 2, original DOS VGA.
**Overall: PARTIALLY VERIFIED. Full Room 12 scene acceptance is NOT achieved.**

The handoff calls this investigation P5. This is a research label, not a
renaming of the standing roadmap's P5 audio milestone. Native scene fidelity
remains the priority; no BigR or enhancement work was introduced.

## Baseline and preservation

Remote P4 HEAD was independently read through GitHub as
`a536b8e976e8ed59903925774ff821776e7b45c7`. Draft integration PR #8 is the
only open PR observed at startup and remains untouched. The F-drive source
snapshot reports `b4f7281`; the older chat checkout reports `965424e` and
has five untracked navigation files. Neither was switched, reset or overwritten.

Shell Git cannot resolve github.com. Local clone attempts also fail in Git's
MSYS subprocess (`NtCreateDirectoryObject ... 0xC0000022`). A writable source
snapshot was made with `git archive` from the F-drive commit; GitHub's compare
API enumerated the five changed files to the pinned remote HEAD, and those
five were refreshed through the connected GitHub API. Its newly initialized
local Git history is a **snapshot history**, not upstream history. New remote
research commits must use the real upstream commit/tree as their parent/base;
never push this synthetic snapshot root over an existing branch.

Working source:
`C:\Users\87otl\Documents\ChatGPT\ScummBucket\SOURCE\ScummBucket-P5`.
New private results are under the same workspace's `FIXTURE`; prepared
third-party source overlays are under `TOOLS`. Original F-drive inputs were
read only. No original archives, captures, extracted pixels or patched C++
files belong in the public research commit.

## A. Reusable rendering relationships

`scummbucket/scene_source.py` reuses the existing archive inspector,
background-strip decoder, Z-plane decoder and costume painter. It adds a
room-neutral source loader, strict v5 BOXD/SCAL readers and one explicitly
supplied draw-phase actor compositor. No room ID is hardcoded in that loader.

Pipeline established by source inspection:

1. Directory/room offsets locate immutable resources; hashes bind both inputs.
2. RMIM/IM00/SMAP produces indexed room pixels; CLUT remains a separate input.
3. BOXD supplies geometry, box mask plane, flags and raw scale selector.
4. A scale selector with bit 15 set references SCAL slot `(raw & 32767)+1`.
5. Actor draw state supplies transformed anchor, costume, facing, scales,
   selected depth plane and limb cursors. Those values must not be inferred
   merely from costume storage in a room bundle.
6. COST cels paint nonzero local slots through their palette mappings.
7. Foreground masks suppress actor pixels according to the selected plane.
8. Final palette state and backend conversion determine displayed RGB.

Steps involving live actor/object ordering, script mutation, palette overrides
and animation scheduling still require runtime state. This is not a SCUMM VM.

Technical references: local ScummVM `v2026.4.0` `engines/scumm/{room.cpp,
boxes.cpp,boxes.h,actor.cpp,costume.cpp,script_v5.cpp,palette.cpp}` and the
existing P4 renderer/source-lineage notes. These are ScummVM relationships;
original LucasArts DOS executable equivalence is not established.

## B. Room 12 resources and reconstruction experiment

Original archive SHA-256 values match the established edition:

- MONKEY2.000: `cde7aa8980317e3a750fbb3b49884cdddaf1ff3d4231a0c840b22cceed9033f1`
- MONKEY2.001: `ad045372e0d49626503bb50fca29a687ec8e01ef75d9b8bca702a366d143819e`

Room 12 ROOM: decoded archive offset **910519**, length **32691**,
SHA-256 `75e48923aeb8e97bf4826135338588e2c84f43adce554aef194aae2e4943e553`.
Background: **320 x 144**,
indexed SHA-256 `4299b2ad3aff94e3ae222fea3bf4ffdf5a773da598a01c22b8131358764aed2e`.
No background decoder diagnostics. Three decoded depth planes contain
**6489 / 11174 / 8563** set pixels. There are **15 walkboxes**, no CYCL
records, and eight paired object records (100-107). Objects 100 and 106 each
store one image state; the other six store no image state. These counts do
not establish their live visibility or execution.

The original continuous `doorway-4ecbce57669248bc816e4993b3306ca9` capture
contains 72 interior engine ticks (140-211) and 213 corresponding SDL
presentations with recorded Guybrush draw state, covering 67 distinct poses.
Source background + COST[1] + selected depth plane were reconstructed using
that observed pose. The reusable compositor and the separate exploratory
composition agree on their candidate index arrays.

**Reference boundary:** the doorway capture has RGB presentations, not the
Room 12 indexed engine buffers needed for strongest acceptance. Inverting the
known RGB565 display quantization by nearest representable channel compares
RGB565-equivalent colour words. This cannot identify original palette indices
when colours collide and cannot verify the exact RGB conversion pipeline.
Two earlier colour-expansion hypotheses were retained as failed/partial
experiments; no fitted palette is used for the candidate indexed raster.

| Experiment over 213 presentations | RGB565-equivalent mismatches |
| --- | ---: |
| Candidate background + Guybrush + depth | 163943 |
| Disabled depth control | 171505 |
| Actor shifted right by one pixel control | 227319 |

Extent: **9,815,040** colour-word observations, including repeated frames.
Per-presentation residual: **679-883**. Applying the mask changes **7562**
candidate indexed observations. Source-identified actors 7/8 and the mouse
cursor are omitted. Tick-end state versus SDL presentation phase remains a
possible additional discrepancy source. Residuals are not silently excluded
from acceptance. Exact RGB comparisons also fail. Every row records source
candidate hash, reference hash, counts, first differing coordinate and bbox.

Private outputs: `FIXTURE/REPORTS/P5/room12-probe-{a,b,c,d}`. The first three
preserve exploratory conversion hypotheses. `room12-probe-d/probe.json` is
the detailed partial comparison; candidate/reference/error PNGs remain private.

## C. Costume execution

`classic_animation.py` models v5 directional animation selection, limb masks,
start/end cursors, looping and terminal holds, inherited limbs, stopped-limb
preservation/resumption, and 0x78/0x7c sound/animation-counter effects. It
rejects control-only cycles instead of hanging. Five synthetic tests pass.
Source animation initialization was exercised against real COST[20] frame 12
and COST[41] frame 6, retaining their different limb programs.

**PARTIALLY VERIFIED:** source-backed bounded model and synthetic controls.
No new Wally/actor-8 runtime cursor sequence, native update cadence or
frame-by-frame costume execution has been independently verified. Update
steps are not milliseconds or engine ticks. Do not promote Gate 3.

## D. Source-aligned actor/script behaviour

`tools/audit_room12_actor_sites.py` aligns **11 executed actor instruction
sites** from the opcode log to their original Room 12 LSCR chunks, checks
the actual opcode byte and decodes the supported direct operands.

| Executed script | Source-aligned effect |
| --- | --- |
| 201 | Actor 7 defaults; costume 20; ignore boxes; force plane 2; room 12; position (119,101); animation command 250 |
| 204 | Actor 7 stand frame 11, talk frames 6/7, animation 12 |
| 203 | Actor 8 defaults; costume 41; ignore boxes; never Z-clip; room 12; position (220,136); animation 6 |

This explains why a Guybrush-only candidate omits two scripted costume layers.
It does not determine their first displayed pose, scaling inherited between
operations, update phase, or exact ordering within a tick. Command 250 must
be interpreted through `Actor::animateActor`, not treated as COST frame 250.
The parser deliberately rejects unsupported actor suboperations; it is not a
general disassembler. Private report: `FIXTURE/REPORTS/P5/room12-actors-a.json`.

No new object-state change is accepted. The existing Room 12 object-102
raw-pattern candidate is still not instruction-aligned/runtime verified.
Room 7 object 57's conditional activation remains untested.

## E. Cross-room movement, scale and selected depth

`tools/audit_cross_room_navigation.py` compares archive rules directly with
independent tick/draw fields. Room 12 SCAL slot 1 is `(190,65)->(255,103)`.
The model uses C++ integer truncation toward zero and clamps slot results
to 1-255. For example, Y=58 gives **179**; Y=74 gives **205**.

| Private capture suffix | Ticks | Scale components | Fresh draw planes | Errors |
| --- | ---: | ---: | ---: | ---: |
| 4ecbce57669248bc816e4993b3306ca9 | 274 | 548 | 234 | 0 |
| 9e2a36535af54a9ca2f75a1d0be1aebb | 291 | 582 | 258 | 0 |
| bc4cdb5815704230a8eb0f636f45744d | 339 | 678 | 255 | 0 |
| Total | **904** | **1808** | **747** | **0** |

Each complete round trip includes Rooms 7 and 12; no parameters were fitted
between captures. Capture 4272de13544647b4a5b83ea727d79c63 contains only Room 7
and was correctly rejected for cross-room acceptance. The old 9e2 capture
still lacks opcode-channel evidence; that does not invalidate its separately
recorded navigation fields. No missing opcode evidence was promoted.

**VERIFIED for these routes:** source BOXD/SCAL relationships reproduce scale
and selected planes. **Not verified:** arbitrary pathfinding, all clipping
exceptions, changed live matrix/scale slots, elevation in other states, or
exact full-scene Room 12 occlusion pixels.

The new Room 7 loader's background and unpacked ZP01 bytes also exactly match
the accepted `native-20261110-a` export (112896 pixels each).

## F. Portable source representation

`scene_package.py` and `tools/research_scene_package.py` export one schema for
Rooms 7, 12 and 34. Files: source ROOM chunk, immutable background indices,
CLUT bytes, unpacked depth masks, and `source.json` with source hashes,
offsets, geometry, BOXD/SCAL, object/script inventory and diagnostics.
All outputs use exclusive creation. No original game data is embedded in code.

Source package, scene state and playback evidence are separate manifest fields;
the latter two are **null**, not fabricated. A source package alone does not
play a scene. No actor COST bundle or script interpreter is claimed complete.
Integrity verification checks file inventory, sizes, hashes and source-manifest
bindings. Tests reject byte tampering, a self-rehashed file-record mutation
and an unexpected traversal entry. These are integrity checks, not an
independent re-decoder or proof against an entirely forged manifest.

Private prototypes: `FIXTURE/OUTPUT/P5/source-packages-a/room-{007,012,034}`.
All three passed integrity verification. Complete scene fidelity remains
VALIDATION PENDING. Packages contain proprietary derivatives and stay local.

## G. Holdout and verification matrix

Room 34 was selected because object 358 has **16 stored states**, unlike
the single-state examples above. The unchanged loader accepts its background,
three masks and eight walkboxes, and exports the same package schema.
**Only source loading/package integrity was tested.** Multi-state object
composition, state selection and a full Room 34 runtime scene remain UNKNOWN.

| Gate | Status | Missing evidence |
| --- | --- | --- |
| 1 Cross-room full scene | INCOMPLETE | Indexed Room 12 front + all active actors/objects |
| 2 Reusable rendering | PARTIALLY VERIFIED | Full composition beyond single observed actor |
| 3 Animation execution | PARTIALLY VERIFIED | Independent live cursor/event/phase comparisons |
| 4 Runtime state | PARTIALLY VERIFIED | Script-aligned complete instantaneous state |
| 5 Camera/depth | PARTIALLY VERIFIED | Scales/planes verified; full Room 12 pixels pending |
| 6 Portable representation | PARTIALLY VERIFIED | Integrity passed; runtime/playback not implemented |
| 7 Generalisation | PARTIALLY VERIFIED | Holdout complete-scene comparison |
| 8 Reproducibility | PARTIALLY VERIFIED | Offline procedures rerun; new recorder runtime pending |

## H. Next discriminating capture and failures

`tools/prepare_cross_room_capture.py` creates a fresh overlay from the pinned
doorway-b source. It extends the existing indexed recorder to Rooms 7/12 and
records ordered `draw_actor` rows before drawing: actor ID, transformed anchor,
plane, scales, facing, costume, logical frame, stopped bits, 16 cursors and
32 palette overrides. It also emits explicit room and engine-tick identities.
It never modifies the original third-party checkout.

Prepared private overlay: `TOOLS/P5-CrossRoom-Overlay-a`.
Both changed C++ translation units **passed native Windows g++ 16.2.0
syntax checks** with the build's SCUMM/SDL defines. Existing multi-character
literal warnings remain. There is **no linked new executable and no runtime
capture** from this overlay. Syntax success is not build/runtime acceptance.

Preserved failures: initial source pins mistakenly referenced the navigation
base instead of doorway-b and correctly failed closed; corrected pins use
the inspected doorway-b files. First native compiler invocation lacked the
toolchain PATH and failed without diagnostics; the next lacked ENABLE_SCUMM
and reported ScummFile errors. Correct build defines resolved that check.
All attempted compile logs remain under `FIXTURE/REPORTS/P5`.

Do not use the doorway launcher unchanged with this overlay: it lacks
`capture.enabled` for indexed output, and its RGB/indexed presentation IDs
must be reconciled explicitly. Install the overlay only into a fresh TOOLS
copy, compile/link, then use a new capture directory containing both markers.
Preserve Room 7->12->7 ordinary-input provenance and avoid inferred intermediate
transition frames. Compare indexed buffers before investigating backend RGB.

## I. Implementation priorities / completion conditions

1. **Compile and validate the extended recorder.** Modules: prepared patcher,
   existing capture launcher and engine parser. Completion: fresh linked build
   fingerprint, all actor draw rows, scene/tick identities, complete indexed
   buffers and trustworthy presentation association in a new capture.
2. **Reconstruct complete Room 12 states.** Modules: scene_source, costume
   painter, object decoder. Completion: archive-derived actors/objects in
   observed order, actual palette overrides/stopped bits, zero unexplained
   indexed mismatches and mask/geometry negative controls.
3. **Differentially validate animation updates.** Module: classic_animation.
   Completion: independently observed cursors/events for COST 1,20,41,142,
   initial/stop/resume/loop paths and actual update cadence; no phase fitting.
4. **Add indexed object layers/state input.** Existing object decoder currently
   exports RGBA. Completion: preserve original indices/transparency and observed
   state selection, then verify a real state change (Room 34 object 358 is a
   justified holdout). Stored state count is insufficient.
5. **Complete scene-state/playback schema.** Modules: scene_package and existing
   event exporters. Completion: package round trip for both rooms with supported
   costumes, state origins, camera/order/palette instructions and an independent
   verifier. Do not turn source metadata into synthetic gameplay.

## Reproduction

Run from the writable research source (or the eventual research checkout):

```powershell
Set-Location -LiteralPath 'C:\Users\87otl\Documents\ChatGPT\ScummBucket\SOURCE\ScummBucket-P5'
$game = 'F:/Dev/SCUMMBUCKET/FIXTURE/GAMES/MonkeyIsland2_DOS_VGA'
$capture = 'F:/Dev/SCUMMBUCKET/FIXTURE/CAPTURES/Room7/doorway-4ecbce57669248bc816e4993b3306ca9'
# Choose NEW, non-existing paths beneath FIXTURE for every output.
python -B -m tools.audit_cross_room_navigation $game $capture 'C:/Users/87otl/Documents/ChatGPT/ScummBucket/FIXTURE/REPORTS/P5/navigation-NEW.json'
python -B -m tools.audit_room12_actor_sites $game $capture 'C:/Users/87otl/Documents/ChatGPT/ScummBucket/FIXTURE/REPORTS/P5/actors-NEW.json'
python -B -m tools.probe_room12 $game $capture 'C:/Users/87otl/Documents/ChatGPT/ScummBucket/FIXTURE/REPORTS/P5/probe-NEW'
python -B -m tools.research_scene_package export 'C:/Users/87otl/Documents/ChatGPT/ScummBucket/FIXTURE/OUTPUT/P5/room12-NEW' --game $game --room 12
python -B -m unittest discover -s tests -v
```

Final full Python run at this checkpoint: **408 tests, 16 skipped, no unexpected
failures**. Skips retain optional private-fixture/environment limitations; this
is not a claim that all private regressions ran. No workflows were modified,
no CI artifacts uploaded, no main integration/merge or licensing decision made.
