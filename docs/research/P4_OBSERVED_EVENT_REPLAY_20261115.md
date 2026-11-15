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
