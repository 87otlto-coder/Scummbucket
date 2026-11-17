# MI2 Room55 — COMPLETE LSCR212 TALK_ACTOR controller, distance-dependent modes and cleanup (17 November 2026)

**Evidence:** read-only original DOS VGA `MONKEY2.001` (SHA-256 `ad045372e0d49626503bb50fca29a687ec8e01ef75d9b8bca702a366d143819e`). LSCR212 chunk `0x497EA6`, body starts `0x497EAF`, length **590 bytes**. A narrowly implemented independent v5 decoder consumed **590/590 bytes, 116 instructions, and 56 relative branches whose target PCs ALL lie at valid instruction boundaries**. Implemented instruction families were actual source-encountered only: comparisons, move, stop/start scripts with vararg and variable operands, draw/setState, getState, getDist, random, expressions (including nested getRandomNr), script-running probe, sounds, yield/stop. Opcode, parameter bitmasks, backwards jump logic and `VAR_TALK_ACTOR` binding checked against pinned [ScummVM v2026.4.0 script_v5.cpp](https://github.com/scummvm/scummvm/blob/v2026.4.0/engines/scumm/script_v5.cpp), [vars.cpp](https://github.com/scummvm/scummvm/blob/v2026.4.0/engines/scumm/vars.cpp), and [script.cpp](https://github.com/scummvm/scummvm/blob/v2026.4.0/engines/scumm/script.cpp). **No descumm comparison, runtime execution, original interpreter testing, native-rendered image or audio comparison.** Original resources remain read-only and outside Git.

This upgrades the earlier partial [Room55 speaker-dispatch candidate](MI2_ROOM55_TALK_ACTOR_DISPATCH_20261117.md) to a **complete source-aligned controller**, not an observed gameplay trace.

## Full source algorithm

1. At PC `0x000`, if `VAR_MACHINE_SPEED (Var6)` is 0, execute `stopScript(0)`; otherwise continue.
2. At **PC0x009**, `0x9A 00 40 19 00` → **`Local0 = Var25 = VAR_TALK_ACTOR`**, a snapshot of current speaker.
3. Branch on `Local0` and start the relevant local animation script.
4. At **PC0x107** execute `breakHere()` and at **PC0x108** `isNotEqual(Var25,Local0)`, reverse-branch -8. This **continues yielding while the SAME actor remains the talk actor**. Once the actor number changes, progress into the cleanup dispatch at `0x10F`.
5. Reset the corresponding flag Var163–170 to zero, redraw/restore paired images, stop the child script, and in certain branches explicitly set a final image state. At **PC0x24A** jump back to the top-level actor snapshot PC0x009, so it keeps reacting to future speakers.
6. When no recognized actor is speaking, reach **PC0x103** breakHere and jump back to PC0x009; this prevents a tight spin. The last `stopObjectCode` at PC0x24D is unreachable during ordinary uninterrupted looping.

### Speaker-to-child and speaker-to-cleanup map

| Talk actor | Source dispatch PC | Child action | Cleanup begins | Cleanup essential effects |
| ---: | ---: | --- | ---: | --- |
| 7 | `0x00E` | start **201** | `0x10F` | Var163=0; pair621/620 state1; stop201 |
| 5 | `0x01B` | none in this branch | `0x132` | immediate return (special no-child case) |
| 11 | `0x025` | start **203** | `0x13C` | Var165=0; pair624/623 state1; stop203; object623 state3 |
| 8 | `0x032` | start **202** with arg **4/5/8** based on distance and randomness | `0x15F` | Var166=0; pair618/617 state1; stop202; object617 finishing state depends on **Var160** |
| 9 | `0x0CF` | start **204** | `0x1AC` | Var167=0; pair628/627 state1; stop204; obj627 state4 |
| 10 | `0x0DC` | start **205** | `0x1CF` | Var168=0; pair631/630 state1; stop205 |
| 12 | `0x0E9` | start **206** | `0x1F2` | Var169=0; pair633/634 state1; stop206 |
| 6 | `0x0F6` | start **207** | `0x215` | Var170=0; pair637/636 state1; optional draw638 if Bit210==0; stop207 |

**Note:** In the actor8 cleanup at `0x179–0x1A9`, script explicitly reads **Var160** (not the original caller `Local0`) and draws object617 state6 if Var160==4, state1 if Var160==5, or state10 if Var160==8. Var160 is already used in other room scripts for transition gating; its full global writers and value semantics need further analysis. It is **not automatically guaranteed to contain the child caller argument**. Do not silently replace that variable with a guessed saved mode.

### Original actor-8 distance/random branch, fully opcode-aligned

Source **PC0x039** contains `B4 00 00 01 00 08 00`:
`Var0 = getDist(Actor1, Actor8)`. Pinned `o5_getDist` computes object/actor distance; do **not** confuse the units with pixels or a room camera coordinate without testing the engine function.

At **PC0x040**, `isGreater(Var0,20)` takes the relative branch to `0x083` when **distance ≥20** (v5 `jumpRelative` jumps when comparison condition is false).

**If distance is below 20:**
- Source expression at `0x047` writes `Var100 = 2-1 = 1`.
- The next expression at `0x052` executes `getRandomNr(Var100)+1`. ScummVM random is inclusive so the choice is uniformly **1 or 2** (subject to the engine's random implementation).
- Choice1 calls `startScript(202,[8])` at `0x067`.
- Choice2 calls `startScript(202,[5])` at `0x077`.

**If distance is 20 or greater:**
- Source expression at `0x083` writes `Var100=3-1=2`.
- Expression at `0x08E` computes `getRandomNr(Var100)+1` → choices **1..3**.
- Choice1 calls `startScript(202,[4])` at `0x0A3`.
- Choice2 calls `startScript(202,[5])` at `0x0B3`.
- Choice3 calls `startScript(202,[8])` at `0x0C3`.

The earlier fully aligned LSCR202 modes therefore have actual source callers:
- arg8 → nonrepeating states8–11 for object617;
- arg4 → nonrepeating states4–7;
- arg5 → fallback alternating states1 and3.

This is source-proven **spatially conditioned variation in dialogue-related image animation**. It is **not** an unconditional animation based solely on the current room.

## Link with script213 and source-image synchronized flags

[Room55 complete LSCR213](MI2_ROOM55_SEVEN_PAIR_SPEECH_SYNC_20261117.md) independently consumes **415/415 bytes, 77 instructions, 31 aligned branches**. It reads the same source flag vars163,165,166,167,168,169,170, and changes seven pairs of object states1/2 with redraw suppression. Source script212's cleanup writes these flags to zero and stops corresponding child image-state loops. Together they imply a central speaking-actor/animation/synchronization lifecycle, whose final visuals remain to be tested.

## Engineering implications and verification gates

1. **Do not export six simultaneous idle background GIFs:** only one relevant speaking-actor branch may launch at a time, actor8 varies by proximity to actor1 and the live RNG, and child lifetime is tied to `VAR_TALK_ACTOR`.
2. **Do not substitute fixed animation FPS:** accepted state choices call `breakHere`; script212 polls the current speaker each scheduler update. The exact render phase remains unknown.
3. **Preserve actor geometry and RNG:** record `getDist(1,8)`, Var100, selected script202 caller mode, current Var160, actor IDs, parent/child PC, flag writes, object state redraws.
4. **Re-check source code with official descumm:** independent narrow walk is full but not an official tool comparison, nor an original-interpreter test.
5. **Runtime:** stimulate different room speakers, including near/far actor8 cases, capture source vars, exact child starts/stops, shared flag sync and native front buffer. Compares the indexed output to decoded original assets before assigning fidelity acceptance.

**Completion boundary:** 590/590 static bytecode and 56 jump targets verified under pinned ScummVM syntax, not natural gameplay or pixel-exact animation.
