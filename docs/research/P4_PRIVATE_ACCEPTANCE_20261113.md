# P4 Room 7 — independent Windows private acceptance, 13 November 2026

**Evidence class:** user-executed Windows PowerShell 5.1 terminal transcript, supplied to the project conversation on 13 November 2026. This document is an *evidence summary* of that transcript, **not** a second execution by hosted CI or a direct reinspection of the private manifest/binary captures by the reviewer.

## Authenticated run scope

- Repository: `87otlto-coder/Scummbucket`; branch: `research/p4-engine-palette-trace`.
- Exact checked-out HEAD: `4ffac2a2bcba6e19508bb4098d34da8ee57fab7b`; user fetched `origin`, checked a clean tree and performed `git merge --ff-only` from prior `84e557a`. No force push, reset or workspace migration.
- Acceptance entry point: `F:\Dev\SCUMMBUCKET\SOURCE\ScummBucket\tools\p4_private_acceptance.ps1 -WorkspaceRoot F:\Dev\SCUMMBUCKET -Full` in a child `powershell.exe -NoProfile -ExecutionPolicy Bypass -File ...` process. This does not permanently change the user's execution policy.
- Read-only preflight reported **ready**. The script hashes the pinned original DOS VGA archive pair and 87 engine captures against the private sweep report. This transcript shows the aggregate preflight result, **not** the individual file hashes.
- Pillow version printed: **13.0.0**.

## Observed outcome

| Check | Observed terminal result |
| --- | --- |
| Python test discovery | **288 tests** in **13.268 s**, **OK (skipped=7)**; no unexpected failures |
| Room 23 private costume-vs-engine comparison | `test_all_original_frame_pairs` **ok** — no longer silently skipped |
| Original-game Room 7 scenery COST[142] | `test_only_two_animation_entries_address_the_same_cel` **ok** |
| Other pinned private MI2/Room 23 palette and walking tests | **ok** where configured |
| Independent Room 7 scene verification | **87 frames**, **0 indexed front-buffer mismatches** |
| Frame raster comparison extent | **87 × 320 × 144 = 4,008,960** indexed-pixel comparisons |
| ZP01 clipping negative control | **778 mismatches** when disabled, as expected |
| Standalone HTML preview | Created; **no new human Firefox/file:// playback confirmation** in this transcript |

Private outputs were written without overwriting the previous accepted run:

- `FIXTURE/OUTPUT/Room7/acceptance-20261113T065104013Z/`
- `FIXTURE/OUTPUT/Room7/acceptance-20261113T065104013Z/preview.html`

These private outputs remain **outside Git**. The printed `ERROR MANIFEST_EXISTS`, `ERROR OUTPUT_WRITE_FAILED` and `ERROR OUTPUT_COLLISION` strings occurred inside *intentional negative tests* that subsequently reported `ok`; they were not acceptance failures.

## Seven explicit skips

1. `test_symlink_destination_is_blocked` — Windows symlink support unavailable.
2. `test_room34_object358_instruction_alignment` — external `descumm` and private integration fixture not supplied together.
3. `test_six_unit_model_preserves_all_100ms_samples` — private pair of Room 23 GIF paths not configured.
4. `test_source_backed_rgb_frames_and_event_durations` — private Room 23 event-bundle path not configured.
5. `test_pinned_mixed_trace_predicts_entire_slow_suffix` — private mixed-trace path not configured.
6. `test_all_exported_pngs_against_original_observations` — private mixed-trace/export reference paths not configured.
7. `test_recorded_room23_reference` — private reference capture and native-export paths not configured.

These skips do **not** invalidate the bounded Room 7 indexed-scene acceptance; they **do** limit claims of full optional regression coverage. Any follow-up must retain their skipped status rather than silently counting them as passes.

## Acceptance boundary and remaining decisions

**Accepted for the pinned debugger-equivalent Room 23 → Room 7 entry, original MI2 DOS VGA only:** archive source integrity preflight, private Room 23 costume regression, private COST[142] structure regression and exact independent reconstruction of 87 observed indexed engine front buffers.

**Still unverified or outside scope:** natural in-game Room 7 entry, other paths/durations/actor states, other original game editions, arbitrary Room 7 animations, user-visible browser playback of this new HTML export and the seven optional tests above. A **real browser playback check** and a new normal-entry capture should be recorded separately, not retroactively inferred from this pass.

**Not cleared:** draft integration PR #8 still requires full technical review, source-lineage/license/attribution decision and **explicit owner authorization** for merge. The acceptance run does not settle GPL obligations or asset redistribution rights.

Source: user's complete PowerShell transcript in the ScummBucket project conversation, 13 November 2026. Original archives, engine binaries, frame PNGs, generated HTML, and local screenshot evidence are intentionally not committed.
