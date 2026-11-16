# P4 — local opcode-pattern leads for MI2 same-rectangle objects

16 November 2026. **Unaligned source-byte candidates only.** This scan
does NOT establish valid instructions or observable scene animation.

## Method

The original MI2 DOS VGA `MONKEY2.001` matched SHA-256
`ad045372e0d49626503bb50fca29a687ec8e01ef75d9b8bca702a366d143819e`.
A read-only metadata scanner cross-referenced the 19 exact-rectangle groups
in [the structural inventory](P4_MI2_EXACT_RECTANGLE_CANDIDATES_20261116.md)
against local `LSCR`, `ENCD`, and `EXCD` bytes in the same room.

The pattern rules replicate the existing
`scummbucket/script_candidates.py` direct-object byte-pattern families:
`0x05/0x45` with subopcode 2 for `drawObject` state selection, and
`0x07/0x47` for `setState`. We scanned *every byte position*, without
using a disassembler. Object ID and state are decoded from the apparent
operands, but **none of these 42 matches is instruction-aligned,
branch-reachable, or runtime-executed evidence yet**. We did not scan
global `SCRP` or variable-object-ID forms.

## Results

| Room | Shared-rectangle group | Raw pattern matches | Kind | Initial interpretation to investigate |
|---|---|---:|---|---|
| 88 | objects 813, 818, 819 | **21** | setState | Several literal states for object 813 plus mutual resets for 818/819 |
| 72 | objects 741–748 | **8** | setState | Eight consecutive candidates to set state zero in LSCR 200; possibly a clearing sequence, not playback |
| 48 | objects 515, 517 | **6** | setState | ENCD and LSCR 201/202/211 candidates; object 517 has a raw parent-local-slot gate |
| 44 | objects 451, 461 | **4** | drawObject | Four candidate literal states **1, 2, 3, 1** on object 461, LSCR 201 |
| 29 | objects 276, 290 | **3** | setState | ENCD plus LSCR 200 candidates for object 276 |
| **Total** | **5 of 19 groups** | **42** | 38 setState / 4 drawObject | No instruction alignment checked |

No matching local direct-object pattern was found for Room 94's 136-object
group or Room 105's three-object multistate group. **This does not make
them unused or unreachable**: global scripts, variable object operands
and other instruction forms are outside this scan.

## Targeted static next steps — still no game run needed

**Room 44, LSCR 201:** candidate `drawObject(461,state)` starts at
decoded resource offsets **3,622,866; 3,622,882; 3,622,916; 3,622,969**.
Apparent state values are **1, 2, 3, 1**. Confirm these exact
instruction boundaries, subopcodes and operands with an independent
pinned `descumm -5 -o -h` invocation. Then identify branch triggers
before selecting a runtime capture. Avoid presuming automatic animation.

**Room 72, LSCR 200:** candidate `setState(...,0)` operations
at offsets **6,208,350–6,208,378** at four-byte intervals, targeting
the eight group object IDs 741–748. If disassembly corroborates them,
investigate this as a possible group reset. Do **not** reinterpret
`setState` as `drawObject`; their redraw semantics differ.

**Room 48:** candidates for objects 515 and 517 appear in ENCD and local
scripts; check that the raw parent slot of object 517 is bound to the
intended local object at runtime. A script may change global object
states without automatically making the child visible.

**Room 88:** 21 candidates across group objects 813, 818 and 819.
Resolve valid instruction starts before inferring animations or timing.

Exact offsets and selected operand metadata (not original script bytes)
are preserved in
[the candidate register](../validation/P4_MI2_EXACT_RECT_SCRIPT_PATTERNS_20261116.json).

## Mandatory evidence gates

1. Disassembler confirms start offset, opcode, operand width and values.
2. Branch/caller evidence identifies whether and when the instruction
   can execute. Global scripts remain a separate investigation.
3. Original engine observes state changes and actual draw operations in
   a known scene; original frontbuffer indices establish final fidelity.
4. No guessed frame duration or automatically looping object animation
   is promoted from a raw byte-pattern result.

This is a static investigation, not a new verification run. No
copyrighted game bytes, disassembly listings, compiled tools or
private captures were committed. Work remains draft P4 research.
