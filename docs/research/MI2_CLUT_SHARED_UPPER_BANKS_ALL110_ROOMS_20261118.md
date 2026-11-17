# MI2 archive-wide CLUT bank reuse and dynamic-lighting palette boundaries (18 November 2026)

**Archive-decoded evidence:** original DOS VGA MONKEY2.001 (SHA-256 ad045372e0d49626503bb50fca29a687ec8e01ef75d9b8bca702a366d143819e) and paired MONKEY2.000 LOFF room inventory, private read-only extraction; 110 physical LFLF/ROOM bundles. **No live engine test, independent original DOS render, pixel-level acceptance, or inferred source-animation execution.** Original copyrighted palette resource bytes are NOT committed.

## Full 110-room CLUT fingerprint survey

Every one of the **110 indexed physical ROOM resources** has a tagged **CLUT** resource of exactly **776 bytes** (8-byte tag/size and 256×RGB, 768 palette bytes). Treat the original 256-entry room palette as a native source resource, not as a generic 256-color VGA system palette.

Read-only byte-exact grouping of per-room CLUT slices:

| Original palette index range | Number of bytes | Distinct byte-exact patterns across 110 rooms | Largest pattern-group sizes |
| --- | ---: | ---: | --- |
| **0–15** | 48 | **1** | 110 rooms identical |
| **16–191** | 528 | **97** | 5,5,2,2,2,2,2, then individual rooms |
| **192–207** | 48 | **11** | 46,42,10,5, then 7 unique-room variants |
| **208–255** | 144 | **10** | 47,46,10, then 7 unique-room variants |
| **192–255** | 192 | **11** | **46,42,10,5** plus **seven singleton variants** |
| **Whole CLUT 0–255** | 768 | **97** | 5,5,2,2,2,2,2, then individual rooms |

This is an **exact original archive data pattern**, not an assertion about the intentions of the original game authors or proof that upper palette entries are exclusively reserved for actors. The strongly repeated high-64-color slices are consistent with reusable palette banks, and independently verified original scripts directly animate the two neighboring subranges.

### The four largest 192–255 pattern classes

Hashes below are SHA-256 **prefixes of the 192-byte raw RGB slice 192–255**, so comparisons can be reproduced directly from read-only CLUT data without sharing copyrighted palette tables.

| Upper-64 palette class | Distinct rooms | SHA-256 prefix | Notable covered rooms |
| --- | ---: | --- | --- |
| **A** | **46** | **c99adbb57f67** | Rooms9,13,22,26,48,55,71,73; both actor-X script54 examples Rooms9/13 are classA |
| **B** | **42** | **6cd15c6fc8be** | **Room72**, Room35, 36, 44, 81, 98, 108 |
| **C** | **10** | **7886ad5f1ced** | **Room93**, 33, 40, 79, 88, 90, 91, 92, 103, 110 |
| **D** | **5** | **aea90c9431bb** | Room19 and 104–107 |
| **Seven singletons** | **7** | distinct hashes | Rooms1,25,67,78,84,95,109 |

The classA examples deliberately avoid claiming Room35 uses the same upper palette as Room9/13: it does **not**. This is a potentially useful check against copying arbitrary high-color banks between unrelated scenes.

**Subrange nuance:** The five classD rooms share the same RGB bytes **208–255** as all 42 classB rooms, even though the rooms have a different **192–207** pattern. Hence 208–255 has one fewer distinct pattern class (10) than the combined upper-64 range (11). The two subranges can vary independently, consistent with but not proof of separate dynamic palette roles.

## Cross-reference to original scripted lighting

- [Global49 Room93 lighting](MI2_ROOM93_ACTOR_POSITION_PALETTE_LIGHTING_20261117.md) changes **192–207** based on Ego X via Var285..296.
- [Global54 Room9/13 lighting](MI2_ACTOR_LIGHT_SOURCE_GLOBAL54_ROOMS9_13_20261118.md) is a fully aligned 224-byte actor-parametric script changing **208–255**; Rooms9 and13 have their own seeded X/brightness interpolation arrays, and their sources also start global49. Both rooms have empty 10-byte CYCL resources, so effects are not ordinary stored palette rotation.
- [Room72 palette coverage](MI2_ROOM72_SCRIPT204_PALETTE_COVERAGE_20261118.md) investigates another script-derived intensity pair, **65–157 and169–187**; it overlaps the room-specific **16–191** range rather than the widely repeated upper palette bank. Its direct caller remains unverified.

## Engineering implications / actual gate

1. P1 should preserve **the exact full original 768-byte CLUT** and SHA-256 per physical room as immutable provenance. A hash/group for subrange0–15, 16–191,192–207,208–255 is a derived annotation only; do not silently deduplicate/rewrite original game archives.
2. P2 native image export should preserve palette-index maps separately from decoded RGB, and associate every index map with **its physical room palette and currently active runtime palette phase**. A generic 256-entry palette or assuming upper colors never change would lose fidelity.
3. P4 scene state needs **independent palette effects per range**. A shared original template does not mean a shared runtime mutable palette; global49 and54 can update different slices on the same scene depending on different actors.
4. Validation: compare the raw 256×RGB palette from original resource with ScummVM initial palette, then capture per-update RGB mutations and indexed pixels separately. Validate room9/13 dual-controller scenarios and room72 script204 activation before making fidelity claims.
5. Original resources and future private captures belong in FIXTURE, external tools in TOOLS, research/implementation in SOURCE. No new top-level project directories.

**Status:** a complete archive-wide exact-byte palette-template inventory; source-relative dynamic lighting implications; **not** live gameplay, an engine renderer, or completed palette animation support.
