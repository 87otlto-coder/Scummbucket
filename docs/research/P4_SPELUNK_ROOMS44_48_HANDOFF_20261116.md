# ScummBucket P4 — Spelunking handoff: Rooms 44 and 48

**16 November 2026. Static/source-only research; no new native captures,
debugger runs, replay verification, or fixed-timing animations.**
This document prepares later experiments without spending Work mode
on reconnaissance. Roadmap milestone stays P4.

## Source identity and research provenance

Original Monkey Island 2 DOS VGA archive read-only:
- `MONKEY2.000` SHA-256 `cde7aa8980317e3a750fbb3b49884cdddaf1ff3d4231a0c840b22cceed9033f1`
- `MONKEY2.001` SHA-256 `ad045372e0d49626503bb50fca29a687ec8e01ef75d9b8bca702a366d143819e`
- Source semantics are referenced from separately obtained ScummVM
  `v2026.4.0` C++ (do not copy source into ScummBucket).
- Game-resource positions refer to zero-based offsets in XOR-decoded
  `MONKEY2.001`. All original bytes, text, images and scripts stay
  outside Git; derived offsets/hashes/relationships alone are recorded.

Detailed evidence:
- [Room 44 investigation](P4_SPELUNK_ROOM44_20261116.md)
  + [source register](../validation/P4_SPELUNK_ROOM44_20261116.json).
- [Room 48 investigation](P4_SPELUNK_ROOM48_20261116.md)
  + [source register](../validation/P4_SPELUNK_ROOM48_20261116.json).
- [Engine object/draw phase](P4_SCENE_STATE_ENGINE_PHASE_MAP_20261116.md).
- [Earlier raw object lead survey](P4_MI2_EXACT_RECT_SCRIPT_LEADS_20261116.md).

## Highest-value finding — Room 44 intermittent animation candidate

**Archive facts:** 20 matched object graphics/code resources, six local
scripts, 20 empty object VERB tables, zero active CYCL room records.
Object 451 and three-image object 461 have identical original bounds
at (88,48), 112×96. Direct `drawObject(461)` can clear a same-rect
peer before queueing the selected object, *if their live geometry
remains equal*.

**Strong source-control hypothesis:** Room 44's ENCD contains a
plausible five-script launch sequence for 202/203/205/201/206.
LSCR 201 has a coherent Var[164] increment-and-test block selecting
object461 source images 1 → 2 → 3 → 1, with conditional effects
and reset. LSCR 205 conditionally gates and triggers that sequence
when global Var[164] and Var[3] are zero, after its **own script-slot
local[0]** counter reaches a threshold of 100 and an inclusive
`getRandomNr(60)` returns zero. Var[100] holds the RNG result.

**Critical correction:** raw operand `0x4000` is **local variable 0**
in the *currently executing script slot*, not global variable 16384.
ScummVM `runScript` initializes locals upon a new script start,
so a restart may reset the counter even if a prior invocation had
advanced it. The source back-jump with `breakHere` preserves control
within a running slot; no runtime cadence or branch execution was
measured. Do not export a uniform-FPS loop as verified.

Room 44 also contains other `drawObject` candidates for objects
452/453/454/459/460 and additional LSCR loops. A correct future
scene capture needs the whole ordered room object queue and real
actor/palette state, not only object 461.

## Second finding — Room 48 conditional layered scene

**Archive facts:** Antique dealer's shop; 41 object/code pairs, 18
local LSCR resources, numerous nonempty object VERB tables,
zero active CYCL entries.

- Source object 515 is the **sign**, original OBCD ordinal 20.
- Object 517 is **parrot chow**, OBCD ordinal 19, with parent *local
  object slot* 20, required parentstate 1, and exactly the same
  stored 24×32 bounds. Both have one stored image.
- ScummVM's clean sequential OBCD load maps the 20th source object
  to slot 20 **if** the local slot table starts empty, but this
  native slot and its actual state remain unobserved.
- Hook object 516's `VERB` event 0x07 includes two start-201
  instruction *candidates*. LSCR 201 has `setState(517,1)`,
  `setState(515,1)`, a `delay(20)` and start-202-shaped call.
  LSCR 202 contains an actor-8 wait candidate, another pair of
  state assignments and a start-214-shaped call.
- ENCD and LSCR 211 have candidate resets of 517 to state 0.
  LSCR 210/213/214 contain separate self-looping actor-animation
  structures. Do not conflate those actors with a two-frame
  parrot-chow/sign cycle.

This is a **parent-gated, interaction-driven overlay candidate**,
not proof of an autonomously cycling background image. It may become
visible conditionally after a verb interaction or entry script,
but actual branch execution and frame appearance are still open.

## Next execution-window order (smallest discriminating cost)

1. **Static S1, no ScummVM runtime:** run the *separate* external
   `descumm -5 -o -h` on original local script copies, preserving
   private original bytes outside Git. Room44 priority: ENCD,
   LSCR201, LSCR205 and nested 202/203/206; Room48 priority:
   hook516 VERB event0x07, ENCD, LSCR201/202/211, 210/213/214.
   Compare source offset, operand widths, jump targets and actual
   instruction starts. Bad/unreachable candidates must stay visible.
2. **Source reachability S2:** resolve Room44's script205 restart
   possibilities, Var[3], Var[164], local0 lifecycle, RNG gate,
   LSCR201 branch structure and all object draw candidates.
   For Room48 trace event0x07's verb conditions, script201→202→214,
   script211 resets and parent slot ownership. Search global callers
   only with aligned script evidence; absence of a local hit is
   not evidence of no caller.
3. **Native N1 — choose Room44 first if reachable:** capture a
   normal non-injected game execution with script slot/PC, local0,
   globals3/100/164, random return, exact `drawObject` params,
   live same-rectangle peer resets, full object queue, actor state
   before redraw, palette/CLUT, masks, tick and original indexed
   frontbuffer. Never consume extra RNG calls or force redraw.
4. **Native N2 — Room48 interaction:** verify hook dispatch,
   parent local slot20, object states 515/517, script wait, frame
   phase, actual object paint order and independent indexed front;
   distinguish ordinary room draw from queued object draw and from
   actor animation. Script state is not identical to image display.
5. **Fidelity N3:** compare every sampled indexed pixel without
   copying engine frontbuffer pixels into candidate outputs.
   Preserve mismatch coordinates and provenance; only measured
   native tick/palette data support real timing exports.

## Current acceptance

| Claim | Status |
|---|---|
| Source resource geometry, linked OBCD/OBIM, names, LSCR hashes | **Archive-decoded** |
| Control flow and variable scopes matching pinned ScummVM opcode definitions | **Source-backed hypothesis; external disassembly pending** |
| Descumm instruction alignment for Rooms 44/48 | **Not independently verified** |
| Actual script entry, branches, RNG outcomes, timer/state changes | **Not observed** |
| Live room-local object slots and exact rendering order | **Not observed** |
| Original native indexed frames for these mechanisms | **Not captured or compared** |
| Continuous animation timing or complete layer exports | **Not validated** |

Do not re-open Room12 residuals or Room34 runtime as a prerequisite.
These Rooms44/48 static findings do not alter earlier Room7 native
fidelity checkpoints.

## Operator and repository safety

Use Windows PowerShell and begin in
`F:\Dev\SCUMMBUCKET\SOURCE\ScummBucket`. Preserve exactly
the top-level SOURCE, TOOLS, FIXTURE layout. Game data and
native captures belong in FIXTURE, separate ScummVM and descumm
tools in TOOLS, project-owned source/reports in SOURCE. No
destructive copies, silent overwrite, copyrighted artifacts in Git,
Linux CI expansion, or routine Actions uploads. Draft PR #18 remains
unmerged pending real runtime evidence.
