# MI2 Room40 — state-sensitive butt-slide and map-piece pickup handlers (17 November 2026)

**Input and evidence:** read-only original DOS VGA `MONKEY2.001` (SHA-256 `ad045372e0d49626503bb50fca29a687ec8e01ef75d9b8bca702a366d143819e`), independently bounded opcode walk of Room40 local scripts **200/201** and several OBCD/VERB handlers, with all relative branch targets aligned. Bytecode meanings checked against [ScummVM v2026.4.0 script_v5.cpp](https://github.com/scummvm/scummvm/blob/v2026.4.0/engines/scumm/script_v5.cpp) and [object.cpp](https://github.com/scummvm/scummvm/blob/v2026.4.0/engines/scumm/object.cpp). **Static research only.** No real SCUMM or original-DOS game execution, no full official descumm comparison, no verified native pixels. All copyrighted inputs/captures are excluded from Git.

## Room40 source structure / physical visual resources

Room40 has an empty one-byte ENCD and EXCD; **its interesting effects live in object verb handlers, room-local scripts and globally stored scripts**. Source OBCD names include:

| Object ID | Original OBCD name | Notes |
| ---: | --- | --- |
| 423 | `butt slide` | Two stored OBIM image states; source states 0,1,2 are used |
| 424 | `map piece` | Object with pickup/rename handling |
| 425 | `hole` | Interactive scenery |
| 426 | `skeleton in bathtub` | Interactive scenery |
| 427 | `trap door` | Interactive scenery |

This environment should not be mistaken for a simple static Room40 background, even though its ENCD/EXCD bodies contain no active logic.

## Confirmed caller: object423 butt slide verb5 / verb6

The Room40 paired OBCD `VERB` table maps both **verb5 and verb6** to the same handler at source offset **`0x31598E`**. Its **4/4 bytes, two source-aligned instructions** are simply `startScript(200)`, `stopObjectCode`. This directly ties the object interaction to the animation.

Room40 **LSCR200** begins at source **`0x315C57`**, body **40/40 bytes, 12 instructions, two valid branch destinations**:

| Initial `getState(423)` | Ordered source actions | Terminal state |
| --- | --- | ---: |
| equals **2** | `setState(423,1)`, `breakHere()`, `setState(423,0)` | **0** |
| anything else | `setState(423,1)`, `breakHere()`, `setState(423,2)` | **2** |

**Correction of an earlier shorthand:** This is not a `2→1→2` vs `0→1→0` return-to-initial state. It is an **inverting/toggling interaction** between final states **0 and 2**, with an intermediate state1 on both paths. The two alternative original global scripts set 423 to **state0** or **state2** before the Room39→40 cutscene; local200 subsequently reverses that state when invoked through butt-slide verbs 5/6. The final state of this handler is source-proved; when and how the user invokes it remains unobserved.

The script brackets the transition with `beginCutscene([2])` and `endCutscene`. The actual displayed duration for state1 depends on script scheduling and rendering phase and must not be assumed to be one video frame.

## Map-piece handler and 109-byte script201

The original Room40 object424 `VERB` table includes:

| Verb | Source handler | Full narrow-aligned interpretation |
| ---: | ---: | --- |
| **9** | `0x315AD6` (16 bytes; four instructions) | `getOwner(Var7)`, and **if owner==15** start local201, then stop |
| **7** | `0x315AE6` (43 bytes; six instructions) | `getOwner(Var7)`; branch to a message or global script157 depending on ownership condition |
| **8** | `0x315A93` (67 bytes; six instructions) | `getOwner(Var7)`; conditional reply or global script24 with arguments `[95,1]` |

The `Var7` owner query is exactly what the script contains; a higher-level object dispatch relationship is not asserted here. Ownership marker **15** corresponds to `OF_OWNER_ROOM` in ScummVM object state.

Room40 **LSCR201** begins at source **`0x315C88`**, body **109/109 bytes, 15 instructions, two valid branch destinations**. The source proceeds:

1. Set **`Bit[69]=1`**.
2. Invoke sound-control commands, then `startScript(109,[424])`.
3. **Rename object424** via `setObjectName` (the original embedded string spells “hand and map”).
4. **`pickupObject(424,room=0)`**, which ScummVM v5 resolves to current room and makes owned by Ego (per `o5_pickupObject`), with script-based inventory updates.
5. Change sound-control settings, copy `Var[56]` into `Local[0]`, then yield and recheck `Var[56]` until it becomes 0. Finish with further sound-control commands and terminate.

This is an example of **a source-defined persistent state change involving an animated environment and inventory item**. It cannot be reproduced accurately by merely exporting Room40 background and two images of object423; it depends on the dispatch and the object's ownership/renaming lifecycle.

## Linked cross-room global cutscenes

[Global scripts 43/44/68](MI2_GLOBAL43_44_68_TRAPDOOR_CUTSCENE_20261117.md) are now fully aligned and show the puzzle's two outcome paths:
- Global68: Room39 object388 trapdoor animation/movement; `loadRoom(40)`, original costume54, sound effects, Ego positioning.
- Global43: set object423 state0, run global68, then `loadRoom(37)` with longer Room37 actor sequence.
- Global44: set object423 state2, run global68, then remain in Room40 on the source ordinary path.

All three scripts are stored with Room39 but execute Room40 and sometimes Room37 actions. The “success” / “failure” semantics derive from Room39 script203's state-matched dispatch, **not from runtime observation**.

## Future acceptance gates

- Official `descumm -5 -o` comparison for Room40 LSCR200/201, object423 verb5/6, object424 verb7/8/9, global43/44/68; verify the attached original edition hash and source offsets.
- Capture natural Room40 entry via both global outcomes, including object423 initial state, verb5/6 activation, one-yield intermediate state1, and end state.
- Capture map-piece pickup with owner query, Bit69, current name, inventory, sound controls, parent script109 and both possible branches based on ownership.
- Compare indexed native pixels of both object423 `IMxx` states, relevant background, costume overlays, and masking. Captures/exports under `FIXTURE`; original archives unchanged.

This report is independent source-walk evidence only; P4/P6 features do not become complete without runtime, source-image and pixel parity verification.
