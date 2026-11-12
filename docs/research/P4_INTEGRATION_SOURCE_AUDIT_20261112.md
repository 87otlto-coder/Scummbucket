# P4 → main draft integration: public source-content review

**Date:** 12 November 2026. **Scope:** [draft PR #8](https://github.com/87otlto-coder/Scummbucket/pull/8), `main` → `research/p4-engine-palette-trace` at `a9c3bbe06733b367d34f322566d777d12c6fbe49`. This is a **targeted source exposure and documentation check**, not a legal sign-off or private runtime regression.

## Public GitHub diff inspection

- Diff: **298 commits / 119 files**, all with text-source or text-config/document extensions (`.py`, `.md`, `.json`, `.ps1`, `.sh`, `.toml`, `.yml`, `.gitignore`).
- The GitHub per-file patch API returned **all 119 patches** (about 993k characters of text) with **no missing patches**. The diff contained no committed ZIP, PNG, GIF, movie, game archive, executables or raw fixture file paths.
- Targeted text scan across added lines found **no** embedded run of 256+ hex characters, 300+ base64 characters, embedded null byte, PEM private-key marker, obvious GitHub personal access token, or AWS access-key ID pattern. One ~4k-character README paragraph is lengthy prose rather than encoded data.
- Source game archive names, filenames, source hashes, offsets, room IDs, CLI examples, synthetic byte arrays and a machine-readable derived script-event manifest are present. These are **metadata/evidence**, not confirmed original game-resource binaries.
- This scan **does not rule out** smaller copied copyrighted passages, non-obvious secrets, misclassified source snippets, historical exposure outside the PR, or confidential material hidden in prose. Do not treat this as a full repository-history secrets audit.

## Licensing review — unresolved before public release

The project references and reconstructs classic SCUMM behavior using source comparisons to ScummVM. The pinned upstream `v2026.4.0` files [`costume.cpp`](https://github.com/scummvm/scummvm/blob/v2026.4.0/engines/scumm/costume.cpp), [`base-costume.cpp`](https://github.com/scummvm/scummvm/blob/v2026.4.0/engines/scumm/base-costume.cpp), and [`actor.cpp`](https://github.com/scummvm/scummvm/blob/v2026.4.0/engines/scumm/actor.cpp) carry **GPL version 3 or later** notices.

`scummbucket/classic_scale.py` computes an exact 256-entry threshold schedule matching the pinned upstream renderer, rather than storing the original C++ table literally. `scummbucket/classic_costume.py` implements compatible COST parsing and RLE, and scripts under `tools/instrument_*` generate local patches to separately installed ScummVM builds. The current repository root does **not** include a `LICENSE` or `COPYING` file. **No conclusion is made here** that these modules are exempt from or subject to a particular copyleft obligation; source lineage, expression similarity, author attribution, and distribution terms require deliberate review.

Suggested gate: inspect each relevant decoder/renderer and patch generator against upstream code, record any directly adapted expression with its license/attribution, choose and document a compatible project license (with approval), and keep modified third-party source in `TOOLS`, not Git. Do **not** insert a license blindly.

## Functional readiness — remaining private gates

- The public synthetic tests succeeded on hosted **Windows Server 2025**, Python 3.11, [PR #8 CI](https://github.com/87otlto-coder/Scummbucket/actions/runs/43169347907): **278 tests, 14 skipped, 0 failures**, with no workflow artifacts.
- The **private Room 23 and Room 7 captures were not present** on hosted CI and were not rerun during this audit. Work previously reported exact matches for the particular pinned captures; that is not normal-entry proof.
- Standalone Room 7 HTML exporter has synthetic coverage, but **real browser playback of a regenerated self-contained file remains unconfirmed**. Validate with all 87 privately reconstructed PNGs.
- F-drive checkout cleanliness/fast-forward state is **unknown remotely**. Never overwrite source or game fixtures.
- Historical research docs and README have been annotated to distinguish subsequent verified capabilities from their original provisional status; no renderer code is modified in this review.

## Decision

**Leave PR #8 as draft.** Proposed next evidence: an independent Windows private fixture regression, a real standalone-preview playback check, a reviewer-driven code-license decision, then explicit user approval to merge to `main`. No forced pushes, fixture redistribution or destructive migration.
