# P4 — Observed complete actor-state composition, 16 November 2026

**968/968 new Room 7 indexed samples match exactly.** This validates one
original DOS VGA MI2 capture, not every room, script, object or timing mode.
The old Room 7 and Room 12 capture residuals remain unchanged.

## Recovered environment and native recorder

The local Windows workspace returned. The private 1,047-state corpus JSON
was readable again: SHA-256
6595ddb3034e6401c10868ffc3938bc3d9e8143c348e48203a781cdcbeFA1979
(case-insensitive hexadecimal). The prior actor.cpp overlay still matched
70843093326d5789823e3a3aab42bad1edf61ffe8be2f420f0912c0f1ec52945;
its compiled actor.o matched
17143c741f88fa97099ba68e2dab510fec7ba9cabdc7b43d456cb97d882cf3e2.

The failed response file was preserved. A NEW link-b.rsp replaced its
literal backslash-n separators with actual newlines. Native g++ linked
successfully against the existing 528 source-build object files, substituting
only the newly compiled actor.o. All original object hashes were rechecked
against the saved object-inputs.json and were unchanged. No original TOOLS
file was modified. This was an explicit direct-object relink, not a clean
source rebuild. The retained version.o has the old build timestamp.

New executable SHA-256:
0ec6e171a010211fd0135c8832d4da48df776aaf1d31624a4d5f5ce7084b349f.
Its --version probe succeeded: ScummVM 2026.4.0 / SDL 2.32.10.
Executable/overlay/object manifests remain private beneath
TOOLS/P4-ActorState-20261115-a.

## Actual capture

tools/capture_actor_state.py created isolated saves/config/markers and
recorded the immutable original game/archive hashes, executable digest and
private Room 7 save. The original F: game/save files were not modified.

An initial run with music-driver=null hit the saved-game AdLib compatibility
warning and produced no indexed frames. It was closed and preserved at
actor-state-18abe877fe654ee088b34d8f8d2ec954. It is NOT accepted evidence.
The corrected run used --music-driver=adlib and loaded Room 7 successfully.
Guybrush was moved right and back with ordinary point-and-click controls;
no debugger room jump, injected path or automatic pose substitution was used.

Accepted capture: FIXTURE/CAPTURES/Room7/
actor-state-b46a3b4f5f6b4db89a60fd6454eebed8 (ChatGPT workspace).
The application closed normally with exit code zero. No new Room 12 or
Room 34 runtime investigation was introduced.

## Structural and native-pixel checks

tools/index_actor_state_capture.py checks closed-run metadata, executable
hash, sequential raw files, scene/tick identity and front/backend crop.
tools/audit_actor_state_capture.py then checks each pre-redraw state against
the original ordered draw records and source-defined redraw gate.

| Measure | Result |
| --- | ---: |
| Room 7 indexed samples | 968 |
| Actor states | 1,936 |
| States accompanied by actual draw operations | 1,795 |
| States without a draw operation | 141 |
| State/draw preparation differences | 0 |
| Exact complete-state indexed frames | 968 / 968 |
| Indexed pixel observations | 44,605,440 |
| Complete-state indexed discrepancies | 0 |
| Archive background discrepancies | 0 |
| Observed palette transport discrepancies | 0 |
| Draw-only reconstruction discrepancies | 183,279 |
| Draw-only non-exact frames | 73 |
| Mask-disabled control discrepancies | 88,510 |
| Actors shifted right one pixel discrepancies | 1,416,914 |
| Distinct indexed frontbuffers | 25 |
| Distinct camera rectangles | 1 |
| Observed final palettes | 96 |

Repeated frames are included in the observation total; it is not 968 unique
poses. Actor 1 had seven cursor combinations; actor 11 had one. Every
observed animation speed/progress was zero. Nonzero animation-speed cadence
and animation event side effects are not established by these results.

tools/compare_actor_state_scene.py composes archive-derived room/COST pixels
using each frame's own observed pre-redraw actor state in recorded process
order. It compares the candidate with the independent indexed frontbuffer.
It does not borrow the last recorded draw pose, copy reference pixels, fit
RGB palettes, alter old results, interpolate or invent object state.

The candidate mapping rejects invisible, shadow, back-buffer and nonuniform
scale cases pending appropriate rendering semantics. Actual draw observations
remain separately labeled from pre-redraw composition candidates. The zero
pixel result independently verifies the candidate for this observed route.

## Offline reproduction

A fresh private source/event/COST package was exported at
FIXTURE/OUTPUT/P5/room7-complete-state-20261115-a. Verification in a separate
Python process re-decoded source room images/masks and reproduced all 968
candidate frames without original game/capture access. Historical direct
reference acceptance remains separate: the package does not contain original
engine frontbuffers and does not revalidate them during offline checking.

Private report hashes:
- actor-state-scene-20261115-a.json:
  0f3aff607e98967ef5cba5edabe4d87d0a97e01b92fdc52837e4a330ae758a6f
- actor-state-channel-20261115-a.json:
  91f87f69648c65e84988d02bab7772577291348a9252bd0b899f2acc94db5069
- package replay.json:
  654aae07fb663a2d40e784950f183b0ea14b8158d3d0a244afce7b44d01d9d7e

Actual local Windows full suite after this increment: **493 tests, 16 skipped,
no failures**. An initial new test expected a hyphenated phase label while
the schema uses underscores; its assertion was corrected to the exact schema
value, and the full suite passed. Pixel/reference assertions were unchanged.

## Boundaries and next research

Native indices, archive masks and layering are verified for the new observed
route. Palette values are observed inputs, so their equality does not verify
autonomous cycle execution. Engine ticks are identities, not exported frame
durations. No SDL display-phase/RGB equivalence or original DOS executable
equivalence is implied. Runtime object-state transitions remain unverified.

Next use this capture's directly observed pre-update cursors/progress/speed
to differentially investigate COST advancement. Preserve initialization and
script-driven selector changes as separate boundaries. Do not promote a
zero-speed sample into proof for nonzero-speed cadence or sound events.
