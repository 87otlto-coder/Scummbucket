# P4-to-main integration — source lineage and distribution gate

**Review date:** 12 November 2026. **Scope:** `87otlto-coder/Scummbucket`, P4 branch following provenance fix PRs [#14](https://github.com/87otlto-coder/Scummbucket/pull/14) and [#15](https://github.com/87otlto-coder/Scummbucket/pull/15); integration remains [draft PR #8](https://github.com/87otlto-coder/Scummbucket/pull/8).

**Classification:** engineering source-lineage register, **not** a legal opinion, license grant, claim of independent authorship, or permission to distribute modified third-party work.

## Verified facts

1. The ScummBucket root has **no LICENSE or COPYING file**, and `pyproject.toml` has no declared license metadata (verified against the research branch on 12 November). This is a distribution-clarity blocker; absence alone does not establish whether a particular act of copying/distribution was lawful.
2. Pinned ScummVM `v2026.4.0` source files [`engines/scumm/costume.cpp`](https://github.com/scummvm/scummvm/blob/v2026.4.0/engines/scumm/costume.cpp), [`base-costume.cpp`](https://github.com/scummvm/scummvm/blob/v2026.4.0/engines/scumm/base-costume.cpp), [`actor.cpp`](https://github.com/scummvm/scummvm/blob/v2026.4.0/engines/scumm/actor.cpp), [`palette.cpp`](https://github.com/scummvm/scummvm/blob/v2026.4.0/engines/scumm/palette.cpp) and [`scumm.cpp`](https://github.com/scummvm/scummvm/blob/v2026.4.0/engines/scumm/scumm.cpp) all contain **GNU GPL version 3 or any later version** notices. They refer to the upstream ScummVM COPYRIGHT file for authors.
3. The repository's [Room 7 renderer source map](P4_ROOM7_RENDERER_SOURCE_MAP.md) expressly identifies upstream functions and source mechanics used to design the COST, palette, scaling and actor-composition investigations. Documenting a source reference is **not itself a complete copyright/licensing analysis**.
4. The research repository contains Python patch generators that inject C++ snippets into separately installed/instrumented ScummVM copies. Those ScummVM source copies and compiled binaries belong in `F:\Dev\SCUMMBUCKET\TOOLS`, not in ScummBucket's Git tree. Whether the *committed injection snippets* contain protectable upstream expression, and obligations associated with distributing a modified build, still need review.
5. The proposed PR #8 file diff contains development source, tests, docs and config; the previous [targeted exposure scan](P4_INTEGRATION_SOURCE_AUDIT_20261112.md) found no obviously committed game archives, screenshots, output PNGs, long embedded base64 blobs or common credential markers. This is **not** a full licensing or secrets audit of all historical commits.

## Prioritized lineage map (engineering findings, not license conclusions)

| ScummBucket files | Pinned upstream source | Verified relationship | Open review |
| --- | --- | --- | --- |
| `scummbucket/classic_scale.py` | `costume.cpp`, `base-costume.cpp` | Implements a calculated 256-entry scaling threshold schedule whose output matches the ScummVM `smallCostumeScaleTable`; uses the same phase/scale interpretation for the pinned scene | **High**: compare expressive code lineage and document any adaptations; no automatic exemption just because source is Python or computes the table rather than storing it |
| `scummbucket/classic_costume.py` | `costume.cpp`, `base-costume.cpp` | Decodes classic COST pointers, 16/32-color packed RLE, transparent slot zero and actor limb cels, based on format/source research and observed fixture tests | **High**: classify facts of a file format vs potentially adapted expression, add attribution where appropriate |
| `scummbucket/palette_probe.py`, `palette_sequence.py`, `palette_events.py`, `palette_gif.py`, `palette_trace.py` | `palette.cpp`, `scumm.cpp` | Experimental native palette models and trace checks explicitly reference ScummVM cycle mechanics; their timing hypotheses/observations are separately documented | **Medium/high**: compare implementation expression to upstream, preserve observation-vs-model distinctions |
| `scummbucket/object_images.py`, `inspector.py`, `linking.py`, `scene_inventory.py` | SCUMM v5 format/source investigations; exact lineage not fully reviewed in this pass | Archive parsing, state image decoding, object linking and provenance, with synthetic and private regression coverage | **Medium**: confirm format references, exact source citations and licenses, and unsupported-edition diagnostics |
| `tools/instrument_scummvm_palette.py`, `instrument_room23_frames.py`, `instrument_room7.py`, `instrument_room7_actor11.py` | `scumm.cpp`, `actor.cpp`, relevant SDL/engine sources | Git-tracked Python patch generators contain C++ snippets and/or pinned upstream matching anchors; intended to modify *separate* third-party checkout only | **High**: check embedded C++ text and attribution; review requirements if modified ScummVM tools/builds are ever distributed |
| `scummbucket/standalone_preview.py`, `tools/package_room7_preview.py` | No ScummVM source copying identified during this targeted review | Self-contained HTML packaging of user-supplied, privately derived indexed images | **Lower** source-lineage concern; copyright in *generated game artwork* still means exports stay in `FIXTURE` and out of Git |

The table is **triage**, not a conclusion that any module is either GPL-governed or independently licensed. Technical equivalence, direct source consultation, and derivation of copyrightable expression are different questions.

## Integration and regression findings

- [PR #14](https://github.com/87otlto-coder/Scummbucket/pull/14) fixed the P1/P2 race between inventory and input re-open: both index (`MONKEY2.000`) and resource (`MONKEY2.001`) SHA-256 values are verified before writing chunks/images. Its two synthetic negative tests passed.
- [PR #15](https://github.com/87otlto-coder/Scummbucket/pull/15) extended the **same index member check** to eight P4 analysis, palette export, disassembly and trace modules. Five new synthetic negative tests passed for the five palette export commands. Existing original-edition private tests were **not** rerun by hosted CI.
- The [hosted Windows PR #15 run](https://github.com/87otlto-coder/Scummbucket/actions/runs/43308407273) passed **285 unit tests (14 skipped, 0 failures)** plus PowerShell 5.1/7 Pillow probes, with **zero workflow artifacts**. This is technical regression evidence, **not** a license compliance test.
- Revisit P4 research-only code paths and other modules during the remaining PR #8 review; this pass **does not claim line-by-line clearance of all source files**.

## Decisions needed before authorizing publication or promotion into main

1. **Owner licensing decision:** determine a project license and accompanying attribution/NOTICE policy *after* resolving whether any code incorporates protectable GPL-covered expression. Consider legal expertise where necessary; do not copy in a LICENSE file or choose an SPDX identifier by guesswork.
2. **File-level source provenance:** for the high-priority modules above, record which upstream lines/algorithms were examined, whether any source text or distinctive implementation was carried over, and which file-level notices are required. Retain pinned source commit/blob fingerprints, not proprietary game bytes.
3. **Third-party build distribution policy:** keep full ScummVM source and patched binaries under `TOOLS` locally. If any instrumented build is distributed, explicitly review applicable ScummVM notice, source-availability and GPL obligations first.
4. **Private acceptance evidence:** preserve the complete F-drive private test transcript and checksums for Room 23/7; uploaded HTML/manifest and Chromium playback are strong downstream evidence but do not replay the original engine buffers.
5. **Integration approval:** retain [draft PR #8](https://github.com/87otlto-coder/Scummbucket/pull/8) until the code/lineage audit and local acceptance gates are resolved and the owner expressly authorizes that specific merge. Do not silently merge to `main`.

## Disposition

**Status: OPEN — needs owner decision and targeted source-expression review.** Current P4 source should be retained and tested. No third-party sources or game resources are moved, overwritten or committed by this audit.
