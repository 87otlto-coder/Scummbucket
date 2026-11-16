# P4 — source-to-runtime object mechanism investigation packet

Prepared 16 November 2026 for the next Windows execution window.
**Preparation only — no new original-engine capture or native validation
performed to produce this packet.** Existing verified Room 7 data and
open COST 129 failures are unchanged.

## Priority and reason

| Priority | Target | Evidence already available | One discriminating next step |
|---|---|---|---|
| **A — low-scope** | Room 44 objects 461/451 | Two exact source rectangles; four unaligned LSCR 201 `drawObject(461,...)` candidates, apparent literal states 1,2,3,1 | Check disassembler alignment and then record original peer resets + queued draws |
| **B — visibility** | Room 48 objects 517/515 | Same rectangle; six unaligned `setState` candidates; object 517 has raw parent slot 20, parentstate 1 | Resolve actual local slot-20 owner and parent gate against native object snapshots |
| **C — clearing** | Room 72 objects 741–748 | Eight two-state resources, same rectangle, eight contiguous unaligned `setState(...,0)` candidate patterns | Check if actual script executes a group-clearing sequence rather than frame cycling |
| **D — state mixing** | Room 88 objects 813/818/819 | One group with 4/1/1 image states, 21 unaligned `setState` patterns | Differentiate script state mutations from visible image changes |
| **E — structural stress** | Room 94, 136-object rectangle | Identical 40×24 original CDHD bounds for 136 objects; no matching *local direct-object* byte pattern in bounded scan | Identify an aligned caller before scheduling any costly native capture |
| **Later holdout** | Room 105 objects 1137/1139/1142 | Same 56×48 source rectangle, 5/15/3 states; no matching local direct-object pattern | Search global or indirect script references before asserting actual use |

Room 34 object 358 (stored 16 IMxx states) remains deferred as a
live-runtime target. The state=16 low-nibble visibility ambiguity is a
specific **future** experiment, not license to inject a value into an
ordinary accepted capture. Room 12 old residuals stay deferred.

## Static-only gate S0 — before starting ScummVM

1. In a clean Windows checkout of the real upstream ancestry,
   inspect [source phase map](P4_SCENE_STATE_ENGINE_PHASE_MAP_20261116.md),
   [object rectangle candidates](P4_MI2_EXACT_RECTANGLE_CANDIDATES_20261116.md),
   [local script leads](P4_MI2_EXACT_RECT_SCRIPT_LEADS_20261116.md)
   and the exact GitHub commit SHA. Never cherry-pick synthetic local
   snapshot history over the remote research branch.
2. Reopen original MONKEY2 pair **read-only** and verify known SHA-256s:
   MONKEY2.000 `cde7aa8980317e3a750fbb3b49884cdddaf1ff3d4231a0c840b22cceed9033f1`;
   MONKEY2.001 `ad045372e0d49626503bb50fca29a687ec8e01ef75d9b8bca702a366d143819e`.
3. Use the separately installed ScummVM Tools `descumm -5 -o -h`
   to confirm *actual instruction starts and operands* in
   Room 44 LSCR 201 at decoded MONKEY2.001 offsets
   **3,622,866, 3,622,882, 3,622,916, 3,622,969**.
   Do the same for Room 72 LSCR 200 offset range
   **6,208,350–6,208,378**; Room 48 ENCD/LSCRs;
   Room 88 ENCD/LSCR 200. Save private per-script disassembly hashes
   and result metadata, **not script bytes or the listing**, to Git.
4. Trace script callers and branch gates; a global `SCRP` may
   trigger a room action, and a local raw byte pattern may be dead
   data. If none is reachable on the chosen save, do not fabricate
   a native capture scenario or mark the mechanism verified.
5. The original object rectangle is an archive *default*. Confirm
   live bounds and local slots once a genuine scene is reached.

## Native gate N1 — exact state mutation channel

Use pinned ScummVM 2026.4.0 source; preserve existing original build and
create an isolated, non-overwriting instrumented build under TOOLS.
The instrumentation must be observation-only and preserve normal script,
actor, palette and drawing behavior.

Capture at every *executed* relevant opcode:

- `engine_tick`, `script_slot`, `script_number`, source location/PC,
  opcode and subopcode; distinguish `o5_drawObject` and `o5_setState`.
- Requested global `object_id`, state and optional placement. Record
  old/new state of **all affected same-rectangle peers**, not just target.
- Every live room-local object slot, object ID, current x/y/w/h,
  parent index/parentstate, state and visibility eligibility.
- Queue insertion, clearing, dirty background flag, dirty strips and
  whether an object was drawn from a background pass versus a queue.
- Per-draw actual `IMxx` lookup result, local slot, clip, mask source
  and recorded draw order. Do not infer image selection from state alone.

The existing actor-state/palette/frontbuffer channels may be reused
only after checking the instrumented binary/source and matching capture
phase against the current code. Avoid high-volume logging unrelated
rooms. Hash every raw record and capture output.

## Native gate N2 — original indexed frame correspondence

For each accepted engine tick, preserve:

- actual capture-phase camera rectangle and indexed frontbuffer,
  original room background/ZP masks and source-drawn object indices;
- ordered actual object paints, pre-redraw actor states, actor drawing
  operations, palette snapshots before/after cycle/manipulation;
- mismatch count and first differing pixel, indexed palette values,
  current layer/mask/occlusion provenance and event timing fields.

Compare **all** observed indexed frames from the capture, not only
chosen passing moments. Do not use engine reference pixels to fill
candidate frames. Do not infer engine tick duration or GIF FPS.

## Source-backed traps to preserve

- `drawObject` can reset all exact-coordinate-and-size peers, but
  `setState` uses dirty-strip invalidation instead. Neither guarantees
  immediate presented images.
- Normal v5 room-object drawing checks the low four state bits;
  the queued path is separate. `IM10` exists in the source lookup but
  is not automatic permission to display state 16 during regular draw.
- Full-room object iteration uses reverse local slots; queued draws
  are in queued order; actors draw later, then advance costumes.
- `VAR_MAIN_SCRIPT` runs after object/actor drawing and palette effects,
  but before palette/frontbuffer presentation. This can place mutations
  in a different phase than actual painting.
- Original `CDHD` parent bytes are local-object slots, not global IDs.
- Static raw script matches have **not** been authenticated by descumm,
  and absence of local direct-object patterns does not rule out global
  or variable-operand control.

## Acceptance labels

| Label | Evidence |
|---|---|
| `ARCHIVE_RELATIONSHIP_ONLY` | Original source hashes, CDHD/IMHD pairs and exact grouped rectangles |
| `RAW_OPCODE_PATTERN_ONLY` | Byte-pattern source offset without independently aligned instruction |
| `DISASSEMBLED_INSTRUCTION` | External descumm agrees on instruction start, opcode and operand |
| `ENGINE_MUTATION_OBSERVED` | Original engine executes opcode, old/new peer state and queue channel captured |
| `DRAW_ORDER_OBSERVED` | Actual background/queue paint operations and masks captured |
| `INDEXED_SCENE_MATCHED` | Complete original indexed-frontbuffer comparison across every sampled frame |

These statuses are *not interchangeable*. No completeness claim follows
from a disassembler match or synthetic test alone.

## Windows directory and safety contract

Always begin PowerShell commands with:

```powershell
Set-Location -LiteralPath 'F:\Dev\SCUMMBUCKET\SOURCE\ScummBucket'
git status --short --branch
git fetch origin
git rev-parse HEAD
# Inspect first; do not reset, merge or overwrite a dirty worktree.
```

Use exactly the canonical SOURCE / TOOLS / FIXTURE top-level folders.
Original files and captures remain under FIXTURE; external build overlays
under TOOLS; ScummBucket-owned scripts, test code and research docs under
SOURCE. Use exclusive new run IDs/paths. Never commit copyrighted assets,
runtime captures, executables, game archives or third-party code.
Windows-only CI with no automatic workflow-artifact uploads.

No ScummVM runtime or test verification was performed in the static
research session that prepared this handoff.
