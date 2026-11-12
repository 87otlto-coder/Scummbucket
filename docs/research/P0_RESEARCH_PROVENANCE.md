# P0 provenance — preserved historical format research

**Status:** historical evidence, **not** a current P0/P1 completion certificate. Original documents remain byte-for-byte identical to their 7 November 2026 source blobs.

## Sources and retained files

| Historical file | Original source | Blob SHA (identical content) |
| --- | --- | --- |
| [P0_INITIAL_FINDINGS.md](P0_INITIAL_FINDINGS.md) | [PR #2](https://github.com/87otlto-coder/Scummbucket/pull/2), `research/p0-scumm-v5-inventory` at `ea744eb7db1d03b9b6501f2c8fa18f676273b3b1` | `5cc27f7a71aae98295db6f77f55228825f8146f1` |
| [P0_ACCEPTANCE_AND_TEST_PLAN.md](P0_ACCEPTANCE_AND_TEST_PLAN.md) | Same PR #2 | `b249360a7268b230bc1d36879ffe8d28a4ea5674` |

The documents record source hashes, the preliminary 110-room structural inventory, 127 palette-cycle records, 158 multi-state image candidates, and the then-unverified behavior register. They contain **no original game-resource bytes**. The source ZIP findings are tied to those specific samples and not a claim about all game editions. The report also flags a mislabeled `mi1.zip` sample; it is a historical observation for that particular supplied ZIP, not a general statement about Monkey Island 1.

## How to read alongside later P4 research

- The P0 documents explicitly describe preliminary work as of **7 November 2026**. Several TODOs there were addressed by later code and private observations, but original words are deliberately preserved.
- For later Room 23 and Room 7 reconstruction evidence, see [Room 7 integration](P4_ROOM7_INTEGRATION.md), [Room 7 renderer source map](P4_ROOM7_RENDERER_SOURCE_MAP.md), and [portable preview diagnostics](P4_ROOM7_PORTABLE_PREVIEW.md).
- The older [P1 PR #3](https://github.com/87otlto-coder/Scummbucket/pull/3) at `a08ec9cc5477bd6f47343bd439c9a5aae4f80b30` is an **ancestor** of the active P4 branch. Do not merge its 161 commits again as a new independent contribution.
- Retire obsolete open PRs with links to this provenance and the retained descendant branch, not by rewriting history or deleting the evidence.
- This preservation step does **not** authorize promoting P0/P1/P4 development into `main`. The current Windows integration procedure is documented in [P4 branch integration plan](P4_BRANCH_INTEGRATION_PLAN.md).

## Current and historical verification boundaries

Preserved P0 counts are *archive-decoded facts* for the pinned original DOS MI2 files. Runtime behavior of every other room, natural entry to Room 7, and cross-edition compatibility remain unverified. The 87/87 Room 7 indexed result is an observed debugger-equivalent 23→7 sweep with independent composition, **not** an autonomous full SCUMM execution or a proof of comprehensive game support.
