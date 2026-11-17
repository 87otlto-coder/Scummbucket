# MI2 Room55 — complete script213 seven-pair state synchronizer (17 November 2026)

**Evidence category:** exhaustive **read-only original DOS VGA archive bytecode decode**, not gameplay observation. Input `MONKEY2.001` SHA-256 `ad045372e0d49626503bb50fca29a687ec8e01ef75d9b8bca702a366d143819e`, XOR 0x69 decoded without length/offset changes. `LSCR[213]` tagged chunk at `0x4980FD`, bytecode begins at `0x498106`; **415/415 decoded bytes**, **77 aligned instructions**, **31 relative jump destinations**, **0 off-boundary jumps**. Independent narrow decoder implemented only the actually used handlers (`notEqualZero`, `getObjectState`, `isNotEqual`, `drawObject`, `jumpRelative`, `equalZero`, `breakHere`, `stopObjectCode`); semantics cross-checked with pinned [ScummVM v2026.4.0 script_v5.cpp](https://github.com/scummvm/scummvm/blob/v2026.4.0/engines/scumm/script_v5.cpp). **No official descumm run, no ScummVM or original DOS execution, no native indexed framebuffer comparison.** No game bytes or images committed.

## Main finding: 7 independent source-encoded boolean state groups in one continuous update script

The script contains **seven near-isomorphic conditional blocks**. Each reads a persistent variable. If nonzero, it ensures one probe object has state2, and if not already in state2, draws *two paired objects* in state2. If zero, it ensures that probe object has state1, and if needed draws both objects in state1.

| Group | Persistent source flag | Probe object | Paired object | Group entry PC | When nonzero | When zero |
| ---: | ---: | ---: | ---: | ---: | --- | --- |
| 1 | Var163 | 621 | 620 | `0x000` | draw both state2 unless probe already state2 | draw both state1 unless probe already state1 |
| 2 | Var165 | 624 | 623 | `0x038` | same rule | same rule |
| 3 | Var166 | 618 | 617 | `0x070` | same rule | same rule |
| 4 | Var167 | 628 | 627 | `0x0A8` | same rule | same rule |
| 5 | Var168 | 631 | 630 | `0x0E0` | same rule | same rule |
| 6 | Var169 | 633 | 634 | `0x118` | same rule | same rule |
| 7 | Var170 | 637 | 636 | `0x150` | same rule | same rule |

**Actual script endpoint:** after group 7, `PC 0x19A` executes **one `breakHere`** and `PC 0x19B` jumps to **PC0x000**; the trailing `stopObjectCode` at PC0x19E is unreachable on the uninterrupted ordinary loop. This does **not** prove a physical 60 FPS schedule, only one source script yield per seven-group synchronization pass.

### Exact conditional overlay nuance: Bit210 / object638

The seventh group additionally tests **variable reference `0x80D2 = Bit[210]`** after changing its paired objects:

- For Var170 **nonzero**, if probe637 is not already in state2, draw 637 and636 in state2, then if Bit210 is zero, **draw object638** with bare/default draw subopcode `0xFF`.
- For Var170 **zero**, if probe637 is not already in state1, draw 637 and636 in state1, then if Bit210 is zero, **draw object638**.
- If the probe already has the requested state, the branch skips these draw operations **including** the object638 overlay. It is not valid to claim object638 is redrawn on every update when Bit210=0.

`drawObject(638)` is a source instruction and object638 has a paired OBIM in this original room; actual appearance and masking are not independently verified.

## Why this links to TALK_ACTOR dispatch

The newly decoded [Room55 talk actor dispatcher](MI2_ROOM55_TALK_ACTOR_DISPATCH_20261117.md) shows LSCR212 snapshots `VAR_TALK_ACTOR = Var25`, and selects animation loops201/202/203–207 based on speaker ID (including mode arguments for actor8). Earlier independently aligned child loops initialize/reset **Var163, Var165, Var166, Var167, Var168, Var169, Var170** at their own start. Script213 therefore has **direct source-data dependency on exactly those same seven global variables**, synchronizing the paired object state as speaker animation scripts modify their flags.

The source makes **a plausible dialogue-reactive image architecture**, but the visual classification as speaking characters or room decorations is still tentative without inspecting indexed native images and actual gameplay. It is source-proven that the scripts coordinate: the exact semantic label needs observation.

**Critical implementation distinction:** LSCR213 is **not itself a 7-frame animation**. It is a continuous **state propagation process** with redraw suppression. Loops201/202/203–207 produce state changes; script213 observes flags and makes paired source-image states consistent. Source code should be modeled as stateful **speaker → child-script → shared flag → paired object state** graph, not seven independent GIFs.

## Related research / status

- [Room55 entry-to-helpers research](MI2_ROOM55_ENTRY_CALL_GRAPH_20261116.md): room ENCD calls scripts224 and200; script200 calls212/213/211 are **candidates until 200 fully aligned**.
- [Eight selected Room55 loops](MI2_ROOM55_STATIC_EVENT_LOOPS_20261116.md): 201/202/203–207/209 fully independently walked.
- [Room55 speaker dispatcher source substantiation](MI2_ROOM55_TALK_ACTOR_DISPATCH_20261117.md): direct `Var25` and child script branch map.
- **Next source-only:** finish LSCR200 (302 bytes) and LSCR212 (590 bytes) full walks; inspect LSCR211's persistent ambient or actor-dependent effects; locate flag writers beyond the known child scripts.
- **Future runtime:** capture actor talk start/stop and per-phase source Var25/163/165/166/167/168/169/170 + Bit210, paired probe states and object638, scheduler updates, front-buffer indexed hashes.

**Verification boundary:** all 415 original bytecode bytes and branch destinations are independently structurally aligned. The script's dynamic execution and pixel results have not been observed.
