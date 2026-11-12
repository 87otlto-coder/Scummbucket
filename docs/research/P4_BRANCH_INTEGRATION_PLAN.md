# P4 research → main: integration plan (12 November 2026)

> **Current state — 12 November 2026:** The historical plan below has been executed through the review checkpoint. [PR #6](https://github.com/87otlto-coder/Scummbucket/pull/6) merged Windows CI plus the main governance history into P4; [PR #7](https://github.com/87otlto-coder/Scummbucket/pull/7) preserved the two P0 research files unchanged. Historical PRs #2 and #3 were closed as superseded with their branches kept intact. [Draft PR #8](https://github.com/87otlto-coder/Scummbucket/pull/8) now proposes P4→`main`, and `main` remains untouched. The [Windows CI run](https://github.com/87otlto-coder/Scummbucket/actions/runs/43169347907) passed (278 tests; 14 skipped; zero failures; no artifacts). The remaining gates are a content/licensing review, private F-drive regression, browser playback of the new standalone preview, and explicit owner approval for the actual merge. The older steps below are preserved as a dated planning record.

This is **an integration plan, not approval to merge the research branch into main**. Preserve the working P4 branch while governance and Windows CI are reconciled.

## Branch ancestry at preparation

- `main` was `4d4aa25c3e259299743d1bd8b7d85f9889d302f3`, including merged Actions-policy PRs #4 and #5.
- `research/p4-engine-palette-trace` was `d3bc71e9bc33e5279aa0742b6527c1447585c817`, with independent Room 23/7 reconstruction and portable preview, 294 commits ahead and 7 behind main at that point.
- `feature/p1-scumm-v5-inventory` (`a08ec9c`) is an **ancestor** of the P4 research branch and is the head of open PR #3.
- `research/p0-scumm-v5-inventory` is the head of open PR #2 and is on a different line of history.

These identities are historical checkpoints; verify current refs before acting.

## Immediate maintenance PR

A review branch based on P4 research should merge the exact main governance policy files and **preserve** P4's additional canonical F-drive layout instructions in `docs/PROJECT_INSTRUCTIONS.md`.

The only functional change should be migrating `.github/workflows/python-tests.yml` from Ubuntu to `windows-latest`, with the same synthetic regression suite (no new matrix, no automatic artifact uploads). Read `AGENTS.md` and `docs/ACTIONS_INCIDENT_2026-11-11.md`. Validate the workflow on an actual GitHub-hosted Windows runner **before** merging the maintenance PR into P4 research. Inspect test count, skipped count, outcome, artifact list and runner label.

This maintenance work must **not** be merged directly into `main` as an accidental 294-commit code promotion.

## Proposed staged code integration after Windows CI

1. Review open [PR #2](https://github.com/87otlto-coder/Scummbucket/pull/2) (P0 research). Confirm whether its two files remain unique/valuable and check for conflicts with current docs. Close as superseded with an explanation, or merge if appropriate; do not blindly assume newer work contains the exact P0 docs.
2. Review open [PR #3](https://github.com/87otlto-coder/Scummbucket/pull/3) (P1/P2/P4 early feature branch). Its commits are already ancestry of the newer P4 branch. Decide whether to merge it first as a smaller milestone; perform security/provenance review and Windows tests before authorizing a merge to main.
3. Prepare a separate **draft** P4 integration PR from the current P4 branch into `main` *after* resolving earlier PRs, or split into reviewable milestone PRs where possible. The branch currently carries large research history; do not imply the entire 87-frame reproduction is a generic engine guarantee. Require exact private Room 23 and Room 7 regression instructions, limitations, and reproducibility metadata.
4. Preserve read-only game fixtures under `F:\Dev\SCUMMBUCKET\FIXTURE`; no original archives or generated frames in commits, PR attachments, CI artifacts/logs, or releases.
5. Avoid force-pushes, blind history rewriting or deleting branches with unique evidence. Keep original builds in `TOOLS`, and do not rearrange the three-root Windows workspace.

## Gates for considering P4 ready to integrate

- Hosted Windows regression suite succeeds with the same test coverage and no Linux runner.
- F-drive source checkout cleanliness and fast-forward state are verified locally, before altering local files.
- Private Room 23/7 fixtures produce the documented zero-index-mismatch results in their verified modes; normal Room 7 entry remains unverified.
- Standalone HTML preview is **packaged and opened** from the actual 87 reconstructed PNGs, not just synthetic packaging CI; until then, browser playback remains unverified.
- Exact resource offsets/hashes, archive edition, ScummVM instrumented build, camera/actor evidence and tests are recorded. Unsupported behavior stays visible.
- User explicitly approves each actual merge to `main`.

**No edits to reconstruction algorithms are proposed as part of the Windows CI/policy reconciliation.**
