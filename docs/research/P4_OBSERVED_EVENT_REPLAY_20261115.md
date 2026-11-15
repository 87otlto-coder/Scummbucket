# P4 observed-event replay — continuation checkpoint

15 November 2026. Baseline: 8b62784ba464c9d30dd8b9a4ba8b9769c4bc7769.

## Verified baseline on the actual Windows checkout

- Synchronized all 42 changed upstream files into an isolated writable SOURCE checkout; older working trees are untouched.
- Ran the actual repository unittest suite: 455 tests, 16 skipped, no unexpected failures. Error text from intentional negative tests is expected.
- Ran tools.probe_native_object_state against original DOS VGA MONKEY2 files on F:, without modifying them. Room 7 object 57: 1/1 decoded. Room 34 object 358: 16/16 decoded, no failed or unsupported states. This replaces the previous stand-in harness limitation for these source-decode cases only.
- Resource hashes match the established edition. No original bytes or extracted images are included in this commit.

## Next authorized increment

Import the existing original Room 7 indexed capture's explicit actor rows and palette snapshots into the ordered-event compositor. Preserve camera origin, raw-record hashes, observed tick ordering, and unexplained mismatches. Add meaningful source-only tests and compare native indices against the independent engine front buffers. No invented object state, frame timing or missing-actor persistence.

Room 12's 12 absent-draw frames remain deferred. Room 34 runtime acceptance remains deferred. This is P4 animation work; roadmap P5 audio is unchanged. No merge into main.

## Environment

F: game and capture files are readable, but the canonical source checkout cannot be opened. Shell Git remote access fails in its MSYS subprocess. Use connected GitHub operations with real upstream ancestry; never push the older local snapshot history over upstream.

## Implemented and verified continuation

- Added scummbucket/observed_scene_replay.py. Converts each observed indexed snapshot into an explicit palette snapshot and ordered actor frame; recorded screen coordinates are not camera-transformed twice. No cached actor or object visibility is inserted.
- Added tools/replay_observed_scene.py. Rebinds frame/room/tick identity, complete ordered draw records, palettes, backgrounds and raw hashes to the original engine records before comparing native indices. Reports all samples, never just a selected passing subset.
- Added scummbucket/observed_scene_package.py and tools/package_observed_scene.py. Exports private source ROOM/background/palette/masks, required original COST resources, observed events and the original comparison into a new directory. Offline verification independently re-decodes the ROOM background and depth masks and re-renders every candidate. Native playback duration is not inferred.
- Hardened costumes_from_archive against changed resources after inspection and source/costume archive disagreement.
- Tests cover actual actor compositor integration, camera cropping, order, masks, stopped limbs, source/record tampering, no inserted missing pose, package corruption, rehashed event mutation and rehashed background mutation.
- Offline package hashes are integrity/reproducibility checks, not signatures. The package does not include original frontbuffers. Its reference error counts remain historical evidence, not a fresh direct raw-reference validation.

## Actual private Room 7 comparison

Original capture: cross-room-e4deddf716114bc9907d5d99e1b85232.
228 Room 7 samples; 10,506,240 indexed pixel observations.

| Check | Result |
| --- | ---: |
| Exact reconstructed frames | 170 / 228 |
| Remaining native index mismatches | 15,718 |
| Source background mismatches | 0 |
| Palette snapshot byte mismatches | 0 |
| Mask-disabled negative control errors | 29,071 |
| All actors shifted right one pixel errors | 95,381 |

Every frame containing actor 1's draw record is exact (169 frames).
The other exact frame contains no actor draws. All 58 non-exact frames
lack actor 1's draw record: seven include actor 11 only and 51 have no
actor draw records. This is evidence that draw records are insufficient
as complete scene snapshots in those samples, not proof of a particular
missing-pose correction. No residuals are excluded or fixed by inference.

Palette snapshots are observed inputs, so zero palette errors establish
transport fidelity only. They do not independently establish cycle timing.
The comparison CLI returns failure/partial (code 2) when any discrepancies
remain. The package verifier can succeed at reproducing a PARTIAL candidate;
its result explicitly retains that historical scene status and errors.

Private artifacts remain outside Git:
- FIXTURE/REPORTS/P5/room7-event-replay-20261115-a.json
- FIXTURE/REPORTS/P5/room7-observed-events-20261115-a.json
- FIXTURE/REPORTS/P5/object358-repository-probe-20261115.json
- FIXTURE/OUTPUT/P5/room7-observed-replay-20261115-a/
- FIXTURE/REPORTS/P5/event-replay-tests-20261115-{a,b}.log

These paths are relative to the ChatGPT ScummBucket workspace, not F:.
No canonical F: files were modified.

## Reproduction (Windows PowerShell)

~~~powershell
Set-Location -LiteralPath 'C:\Users\87otl\Documents\ChatGPT\ScummBucket\SOURCE\ScummBucket-P4-Continuation'
$game = 'F:\Dev\SCUMMBUCKET\FIXTURE\GAMES\MonkeyIsland2_DOS_VGA'
$capture = 'F:\Dev\SCUMMBUCKET\FIXTURE\CAPTURES\Room7\cross-room-e4deddf716114bc9907d5d99e1b85232'
$indexed = 'F:\Dev\SCUMMBUCKET\FIXTURE\REPORTS\Room7\cross-room-e4deddf716114bc9907d5d99e1b85232\cross-room-indexed.json'
# Use a fresh destination; original resources and old outputs are never overwritten.
$destination = 'C:\Users\87otl\Documents\ChatGPT\ScummBucket\FIXTURE\OUTPUT\P5\room7-replay-NEW'
python -B -m tools.package_observed_scene export $destination --game $game --capture $capture --indexed-report $indexed --room 7
python -B -m tools.package_observed_scene verify $destination
python -B -m unittest discover -s tests -v
~~~

The second command needs neither original game files nor capture directory.

## Next work and acceptance boundary

The next discriminating input is a complete scene-state snapshot at indexed
frontbuffer phase, including active actors that did not redraw, or separately
observed dirty-region/frontbuffer update operations. Existing draw_actor rows
describe draw operations and must not automatically be treated as all visible
actors. Preserve the current partial baseline and verify any source-backed
state acquisition/model against every original sample. Do not introduce a
last-pose workaround based solely on its ability to fit known residuals.

Room 12's residual investigation remains deferred. Room 34's source decode
succeeded but live state/placement/order/timing are unverified. Object-state
runtime integration and full-scene acceptance remain open.

Working tree SOURCE/ScummBucket-P4-Continuation has a local synthetic snapshot
history, not upstream ancestry. Use the real GitHub branch commits as parents
for connected writes. Review branch: research/p4-observed-event-replay.
Draft PR #18 targets research/p5-cross-room-reconstruction; main is untouched.

## Final validation

Actual Windows full suite after all code changes: **468 tests run, 16 skipped, no failures**.
Hosted Windows regression run [293](https://github.com/87otlto-coder/Scummbucket/actions/runs/43757647473) passed for code commit `10cb5739f5f859669dca7546819ed12ab6311b48`.
Offline package verification was rerun in a fresh process and reproduced all 228 candidates, retaining PARTIAL historical scene acceptance.
