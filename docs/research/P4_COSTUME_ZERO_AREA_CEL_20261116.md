# P4 — COST cel zero-area source correction (16 November 2026)

Research branch `research/p4-observed-event-replay`, review-only PR #18.

## Observed archive and source evidence

Read-only independent structural audit of supplied original DOS VGA MI2 archive
`mi2.zip` (decoded MONKEY2.000/001, XOR 0x69, linked index DCOS entries):

- Original archive SHA-256 fingerprints: MONKEY2.000 `cde7aa8980317e3a750fbb3b49884cdddaf1ff3d4231a0c840b22cceed9033f1`; MONKEY2.001 `ad045372e0d49626503bb50fca29a687ec8e01ef75d9b8bca702a366d143819e`.
- 162 linked COST resources, of which 122 are format 0x58 (16-color) and 40
  format 0x59 (32-color). No missing DCOS-linked COST chunks.
- 7,193 declared selector slots attempted; 3,235 had nonempty limb ranges,
  12 failed while decoding referenced cels. All 12 failures are in COST 129,
  selectors 4–15, and are *not* masked by this patch.
- Zero-area referenced cels occur in COST 50 (selectors 6/7) and COST 61
  (selector 33); they were previously rejected by the Python `limb` decoder.
  The audit found 5 zero-area cel references, not 5 unique cel resources.
- COST 129 (room 91, source offset 7662434, COST size 169, SHA-256
  `6ba5fb15dd825567e521fb55c079dcb27ea88c3930fed3fd23cc13404d6f452b`)
  has a referenced 2x2 cel with only two remaining bytes of encoded RLE
  (`12 21`: lengths 2 and 1, three pixel slots). The current decoder reports
  `truncated cel`; no speculative filler or padding was introduced.

The audit above used a temporary read-only independent Python harness (not a
committed CI corpus test) to exercise *all* referenced positions in selector
ranges. The 7,193 count includes empty selectors, not 7,193 executable poses.

## Native source reference and interpretation

ScummVM v2026.4.0 pinned source
`engines/scumm/costume.cpp`, `ClassicCostumeRenderer::drawLimb`, updates
`_xMove` and `_yMove` from the 12-byte cel header before calling
`paintCelByleRLE`. `engines/scumm/base-costume.cpp`,
`BaseCostumeRenderer::paintCelByleRLECommon`, rejects drawing for
nonintersecting/empty rectangles. Consequently, an empty cel can legitimately
modify subsequent limb positioning without writing source-index pixels.

The Python `ClassicCostume.limb` now accepts area zero *without decoding any
RLE*, returning the original movement metadata and empty slots. `compose`
already accumulates the movement after processing each limb. A synthetic
regression uses an independently addressed second cel and verifies its
changed position and complete output buffer.

## Verification boundaries

This patch is source-backed and synthetically tested, not a fresh native-engine
pixel comparison for COST 50/61. Existing exact Room 7 evidence remains a
historical checkpoint. COST 129 remains explicitly failed and cannot be
classified as corrupt or harmless without deeper reference analysis.

No original game bytes, extracted art or private runtime captures enter Git.
No new workflow or CI artifact uploads. P4 Room 12 and Room 34 runtime
investigations remain deferred.
