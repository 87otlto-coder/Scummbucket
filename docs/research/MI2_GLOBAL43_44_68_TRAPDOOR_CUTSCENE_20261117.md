# MI2 Room39→40→37: full source-aligned brick outcome cutscenes (17 November 2026)

**Scope:** read-only source inspection of original DOS VGA `MONKEY2.000/.001`, bytecode XOR `0x69`, `MONKEY2.001` SHA-256 `ad045372e0d49626503bb50fca29a687ec8e01ef75d9b8bca702a366d143819e`; independent narrow Scumm v5 instruction walker, operands/handlers checked against the primary [ScummVM v2026.4.0 script_v5.cpp](https://github.com/scummvm/scummvm/blob/v2026.4.0/engines/scumm/script_v5.cpp) and [script.cpp](https://github.com/scummvm/scummvm/blob/v2026.4.0/engines/scumm/script.cpp). This is **static, branch-consistent original archive code**, not an original-interpreter, ScummVM runtime or framebuffer fidelity test. Game bytes, images and sounds remain private and unchanged.

## Proven script surface

These three global `SCRP` resources are stored in the Room39 LFLF bundle, but **execute in additional rooms** as their code calls `loadRoom`.

| Global script id | Body bytes | Complete narrow walk | Valid relative jumps | Main purpose |
| ---: | ---: | ---: | ---: | --- |
| **68** | 128 | **49 instructions, 128/128 bytes** | 0 (linear bytecode) | Common trapdoor/fall scene; loads Room40 |
| **43** | 253 | **82 instructions, 253/253 bytes** | 4/4 | Alternate outcome; loads Room37 after Room40 |
| **44** | 132 | **33 instructions, 132/132 bytes** | 4/4 | Other outcome; stays in Room40 on the ordinary source path |

These findings expand fully aligned Room39 LSCR203 ([brick puzzle analysis](MI2_ROOM39_BRICK_DIFFICULTY_REVEAL_20261117.md)), which tests whether `Local0 == Var251` and `Bit755`, then dispatches script44 for the match+prerequisite versus script43 for the alternative. **Natural-gameplay branches have not been run.**

Original room data: Room39 paired object388 is named **“trap door”**, and five object IDs392..396 are named **“brick”**. Room40 paired object423 is named **“butt slide”**, with two stored `IMxx` images; objects427 “trap door”, 425 “hole”, 426 “skeleton in bathtub” also occur in the Room40 original OBCD inventory.

## Global68: shared transition into Room40 (128 bytes)

Control flow is linear, and the source confirms all of these operations in order:

1. **`walkActorToObject(Ego, object388)`**, then `wait(actor Ego)` (this wait can repeatedly yield until walking stops); actor action244, change costume to **54**, set Room39 object388 (“trap door”) state1.
2. Issue sound-control `soundKludge` calls, start sound156, actor actions2 then6 with **4 + 19 explicit `breakHere` yields**.
3. Temporarily put Ego in room0; `loadRoom(40)` at **PC 0x004B**, then sound157, actor action250, configure ignore boxes / force clip, put Ego into Room40 at **(128,65)**, animate10 and yield.
4. Move Ego inside Room40 to **(128,85)**, animate10 and yield; restore actor box-following, then stop.

This is not simply a fade between rooms: it explicitly commands fall/transition poses, custom actor costume, sound events, two room-specific positions and a timed wait.

## Global43: alternative result and return to Room37 (253 bytes)

- Starts cutscene, sets Room40 **object423 “butt slide” state 0**, registers a cutscene skip/override target at PC **0x00B9**, then **starts shared script68** and waits for its completion (after one initial `breakHere`, uses `isScriptRunning(68)` + `equalZero` loop).
- Then places Ego in Room40 at **(128,105)**, changes costume animation speed, action9 with **9 explicit yields**, puts Ego in room0 and **`delay(60)`**.
- Executes **`loadRoom(37)` at PC 0x0041**, starts sound128, puts Ego in Room37 at **(187,112)**, uses actor costume **87**, action6, **29 explicit yields**, delay60, action7 and **5 yields**, then restores costume1/actor name and idle action3.
- Cutscene skip/cleanup branch at PC0x00B9 calls `stopScript(68)` under source `VAR_OVERRIDE` state, restores Ego in Room37 and retrieves/refreshes his position through `getActorX/Y`. End cutscene, stop.

**Boundary:** Object423 may be stored in Room40 even when the script issues its state command before loading it. `putState` is persistent logical object state independent of which LFLF currently provides the visible image; the visual outcome needs engine execution to confirm. Calls to `soundKludge` are source-verified operands but detailed music semantics have not been separately reconstructed.

## Global44: other result and remain in Room40 (132 bytes)

- Starts cutscene, sets Room40 **object423 state 2** (the second stored image), registers override target **PC0x003F**, **starts script68**, and waits while it remains running.
- Places Ego in Room40 at **(128,105)**, actor action7 with **5 explicit yields**, **`delay(40)`**, then action8 and **2 yields**.
- Post-override guard on ScummVM v5 **`Var[5]=VAR_OVERRIDE`** handles skipping versus natural completion; the cleanup path may stop the still-running script68, adjust actor box tracking and force clip, then sets Ego position to **(160,105)**.
- Ends override and cutscene, returns costume1 and actor properties, puts Ego at **(160,105)**, idle action3 and stops. **No `loadRoom(37)` in this script**; normal source path stays in Room40 until something else moves the player.

## Important notes for reconstructing assets

1. **Different scene endings:** Room39's selected brick and Bit755 condition choose between *a state0 butt-slide / Room37-return sequence* and *a state2 butt-slide / Room40-standing sequence*. Both share the same scripted transition into Room40 via global68. This is a source-level environmental state transition and actor cutscene, **not** an infinitely repeating background loop.
2. **Script storage room is NOT current room:** global43/44/68 are physically indexed under Room39, but at runtime manipulate Room40/37 objects and actors. A decoder that assigns every image event to the resource's storage room will render the wrong asset.
3. **Source skip path:** both outcomes register `beginOverride` with a target after a long visual/action sequence; they preserve a cleanup route. Treat skip-path state mutations separately from rendered animation frames.
4. **Actor placement and mask state:** room40 actor coordinates and clip/box flags are actively changed. To reconstruct the scene faithfully, retain actor costume, pose, clip plane, path flags, current room, object states and sound state.
5. **Potential loaded-room object-state nuance:** the scripted setState of Room40 object423 occurs before `loadRoom(40)` on the ordinary path; that state must survive room resource loading to be visually relevant. This follows ScummVM's logical global object state scheme but **has not been inspected in gameplay**.

## Reproducible future gates

- Compare official `descumm -5 -o` for each original tagged `SCRP[43/44/68]`, plus Room39 LSCR203; log exact PC boundaries and operands.
- Capture both puzzle outcomes and cutscene skip path with pinned ScummVM. Log script execution PC, current room, object423 state, Ego world pos, actor costume54/87/1, Z-clip, sounds156/157/128, palette hashes and indexed framebuffer changes.
- Test Room40 object423 two states and actor occlusion against independent decoded `IM01`/`IM02`.
- Never commit original game resource bytes or screenshots to Git; store future private recordings under `FIXTURE\CAPTURES`, assets under `FIXTURE\OUTPUT`, source/tests in `SOURCE\ScummBucket`.

**Done boundary:** Three fully opcode-aligned global scripts and source-backed control flow; no verification of natural invocation, branch coverage, pixel-perfect animation or original DOS semantics beyond published pinned ScummVM implementation.
