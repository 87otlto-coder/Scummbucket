# P0 — Acceptance Criteria & P1 Test Plan

**Project:** ScummBucket  
**Status:** Draft acceptance plan; preliminary research pass, 2026-11-07

## 1. P0 exit criterion

P0 can close when the team has:

- A documented, verified source map for the first target's archive, index and room structures.
- A bounded edition-detection policy that rejects unsupported/mismatched input transparently.
- An explicit inventory schema with byte provenance and resource status.
- An initial classification of background-animation mechanisms and verified candidate resources.
- Synthetic and private-integration test specifications with failure reporting.
- An uncertainty register identifying what still requires original-game or ScummVM comparison.

Current state: the basic chunk, directory and room-container layout has been tested on one private sample; exact edition matching, script interpretation, pixel decoding and runtime comparison are pending.

## 2. P1 implementation boundary

**In scope:** read-only file detection, protected opening, optional XOR decoding, chunk walking with bounds checks, `.000` index directories, `.001` `LECF/LOFF/LFLF/ROOM` inventory, valid source offsets, raw resource extraction by explicit user request, JSON diagnostics, CLI.

**Explicitly out of scope for P1:** rendering images, interpreting gameplay scripts, producing animations, audio conversion, HD filters and GUI.

Architecture should preserve links needed for P4: room ID; `CYCL` offset; `OBIM/OBCD` identity and state tags; `ENCD/EXCD/LSCR` and other scripts; palette, mask and image-container locations.

## 3. Archive detection and validation

- Verify matching resource-index and resource-container inputs using content, not just filename.
- Treat the `mi1.zip` sample as **unsupported/non-SCUMM**, not a valid MI1 regression fixture.
- Avoid reading unbounded or untrusted chunk lengths.
- Enforce maximum bytes, offsets and iteration limits; reject invalid bounds safely.
- Never write into input archives.
- Report unsupported compression/encryption/edition variants rather than guessing.
- Capture source SHA-256, file length and detected encoding/version confidence.

## 4. Reproducible private MI2 regression

**Sample fingerprints:** `MONKEY2.000` SHA-256 `cde7aa8980317e3a750fbb3b49884cdddaf1ff3d4231a0c840b22cceed9033f1`; `MONKEY2.001` SHA-256 `ad045372e0d49626503bb50fca29a687ec8e01ef75d9b8bca702a366d143819e`.

Expected preliminary inventory for these exact fingerprints:

| Check | Expected |
| --- | ---: |
| Decoded `.000` byte length | 11,135 |
| Index top-level chunks | 8 |
| Decoded `.001` byte length | 9,080,329 |
| `LECF` children | 111 (1 `LOFF` + 110 `LFLF`) |
| Distinct LOFF room IDs/offsets | 110 / 110 |
| LOFF targets matching ROOM start | 110 |
| Valid ROOM boundaries | 110 |
| `RMIM` | 110 |
| `CYCL` blocks | 110 |
| Rooms with nonempty `CYCL` lists | 21 |
| Palette-cycle records | 127 |
| `OBIM` / `OBCD` | 1,145 / 1,145 |
| Multi-state `OBIM` blocks | 158 |
| `LSCR` | 612 |

**Careful:** A clean chunk walk is not a complete decode. Resource-directory capacities must not be reported as extracted asset counts. No `CYCL` or multi-image `OBIM` record should automatically be reported as an active animation.

## 5. Negative cases to implement

At minimum test and give each a named diagnostic code:

1. Truncated `LECF` chunk / overrun.
2. Chunk length below its eight-byte header.
3. Invalid or overflowing directory record length.
4. Duplicate room IDs and duplicate offsets in `LOFF`.
5. `LOFF` pointing outside file or at a non-`ROOM` tag.
6. Missing `.000` or `.001` counterpart.
7. Misnamed archive that contains a different game (e.g., supplied `mi1.zip`).
8. Unsupported edition or unknown byte-encoding key.
9. Truncated `CYCL` record / unknown tag (preserve raw reference).
10. Requested raw extraction encountering failed I/O or insufficient storage.

## 6. Diagnostic schema and operation status

Every diagnostic should carry, where applicable:

`severity` (`info|warning|error|fatal`), `code`, `operation`, `source_path`, `source_sha256`, `resource_id`, `tag`, `offset`, `length`, `message`, `recovery`, and `evidence`.

Every operation must distinguish `success`, `partial`, `failed`, `skipped` and `unsupported`. Batch summaries must count each separately.

- Never silently catch and discard an exception.
- Recoverable failures should not prevent safe processing of unrelated resources, but remain visible in output.
- Fatal corruption stops the affected operation safely.
- A fallback must be logged and labeled.
- No unconditional success messages for incomplete runs.
- Both machine-readable JSON and concise human-readable summaries should be supported.
- Test failures must be reported even if unrelated to the current code change.

## 7. Minimum exit tests for P1

A P1 implementation is not accepted until:

- It reproduces the private MI2 structural counts above, without copying private assets into the repo.
- Synthetic fixtures exercise all negative conditions, verifying exact diagnostic codes.
- Raw extraction produces byte-for-byte reproducible results and a manifest tied to original source offsets/hashes.
- Unsupported inputs are classified visibly.
- A clean report explicitly states the number of inventory entries, decoded assets (**zero at P1**), unsupported items and failures.
- A simple smoke test can be run in a fresh checkout without commercial source data.
- Docs explain how to run private integration tests with user-owned archives.
- No unresolved serious failure is hidden behind a passing aggregate status.

## 8. P4 preservation checks starting in P1

Before declaring P1 done, ensure the manifest can represent:

- `CYCL` per-room cycle records and flags without interpreting them as demonstrated animation;
- `OBIM` image-state IDs and links to `OBCD`;
- `ENCD`, `EXCD`, `LSCR`, `SCRP` references;
- spatial metadata and room palette/mask references when available;
- observed vs decoded vs inferred status and unresolved diagnostics.

These fields are deliberately kept in scope because background animation is a first-class project priority.
