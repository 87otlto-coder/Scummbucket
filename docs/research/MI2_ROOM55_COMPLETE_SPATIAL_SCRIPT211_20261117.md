# MI2 Room55 — COMPLETE script211 spatial actor/animation scheduler (17 November 2026)

**Evidence:** read-only original DOS VGA `MONKEY2.001` source, SHA-256 `ad045372e0d49626503bb50fca29a687ec8e01ef75d9b8bca702a366d143819e`, XOR0x69 decoded at unchanged offsets. Room55 LSCR211 tagged chunk `0x497D20`, script body begins `0x497D29` and has **381 bytes**. Private independent *narrow, encounter-based v5 bytecode decoder* consumed **381/381 original source bytes, 80 instructions, 30 signed relative jump destinations, all targets valid opcode boundaries**; used only the actual encountered opcode handlers for move, getDist, getActorY, comparisons, start/stopScript, getScriptRunning, yield, unconditional branches, stop. Semantics checked against primary [ScummVM v2026.4.0 script_v5.cpp](https://github.com/scummvm/scummvm/blob/v2026.4.0/engines/scumm/script_v5.cpp) (`o5_getDist`, `o5_getActorY`, `o5_isLess`, `o5_isGreater`, `o5_isGreaterEqual`, `o5_isNotEqual`, `o5_isScriptRunning`, `o5_equalZero`, `jumpRelative`). **No external descumm run, gameplay, frame timing or graphics parity test**. No original copyright game resource bytes committed.

## Main mechanism: actor position selects 4 conditional controllers

Script211 uses a private `Local[1]` **last chosen category**, initialized to sentinel **-999** at `PC0x000`. Each update resets `Local[0]=0` at PC0x005, then tests Guybrush/actor1 distance from specific other actors. Some branches also read **actor1's Y**. A matched predicate overwrites Local0; later predicates execute after earlier ones, so **source order confers priority**.

| Test order / source PCs | Original source predicate | Set group `Local0` | Notes |
| --- | --- | ---: | --- |
| `0x00A–0x01C` | `getDist(actor1,actor8) < 20` | **8** | No actor-Y guard |
| `0x01D–0x02F` | `getDist(actor1,actor11) < 20` | **8** | Can keep/set same group |
| `0x030–0x04E` | `getDist(actor1,actor9) < 25` **and** `getActorY(actor1)>119` | **9** | Lower screen segment |
| `0x04F–0x06D` | `getDist(actor1,actor10) < 15` **and** `getActorY(actor1)>119` | **9** | Same group |
| `0x06E–0x08C` | `getDist(actor1,actor7) < 15` **and** `getActorY(actor1)<=119` | **7** | Upper screen segment |
| `0x08D–0x0AB` | `getDist(actor1,actor5) < 20` **and** `getActorY(actor1)<=119` | **7** | Same group |
| `0x0AC–0x0BE` | `getDist(actor1,actor12) < 31` | **12** | No Y guard; overrides older matches |
| `0x0BF–0x0D1` | `getDist(actor1,actor6) < 20` | **12** | Last/highest priority |
| No predicate matches | retain reset value | **0** | Fallback/default category |

In all of these, distance comes from pinned `getObjActToObjActDist` via `o5_getDist`. Do **not** treat the numeric thresholds automatically as Euclidean native pixels or physical screen distance until engine coordinate and scaling calculations are independently checked. The source comparisons are strict for distance; Y split is **>119 vs ≤119**.

**Order matters:** because all eight tests are sequential (not an `else-if` chain), an actor6/12 proximity match can override a previous 7/9/8 group choice. A future static state machine must replicate this ordering exactly rather than taking the first match.

## Change detection drives child script lifecycle

At `PC0x0D2` the code compares `Local0` with previous `Local1`. If equal, v5 reverse `isNotEqual` branch jumps directly to `PC0x178` and yields. If different, it enters the reconfiguration code:

- **PC0x0D9–0x0E2** stops local scripts **214, 215, 216, 217, 218**.
- **PC0x0E3–0x11E** checks category and replaces the corresponding default helper with a group animation:
  - group7: stop **220**, start **214**;
  - group8: stop **221**, start **215**;
  - group9: stop **222**, start **216**;
  - group12: stop **223**, start **217**.
- **PC0x11F–0x173** checks `isScriptRunning` for each of 214–217 and 220–223; if neither the corresponding group animation nor fallback is running, it starts fallback **220/221/222/223**. This is a **source-coded ensure-running fallback**, not evidence that eight helpers execute simultaneously.
- `PC0x173` writes `Local1 = Local0`, then `PC0x178` **breakHere**, and `PC0x179` jumps to `PC0x005` to evaluate again. Terminal stop at PC0x17C is unreachable under uninterrupted normal loop.

**Important nuance:** fallback ensure-running checks appear only on the **category-changed** path in the decoded control flow; when Local0 remains unchanged the script yields at PC0x178 directly. Do not synthesize unconditional per-frame restarts of missing helpers.

## Links to earlier Room55 reconstruction

Room55 entry ENCD starts local200. [Local200 has now been fully aligned](MI2_ROOM55_COMPLETE_ENTRY_SCRIPT200_20261117.md): 302/302 bytes, 62 instructions, and **unconditionally starts both script211 and script213** from the fully aligned entry path, while starting script212 only if `Var6=VAR_MACHINE_SPEED` nonzero.

Thus this room has **at least two separately triggered control channels**:
- [Local212, TALK_ACTOR controller](MI2_ROOM55_COMPLETE_SPEAKER_CONTROLLER_20261117.md): chooses scripts201/202/203–207 according to who speaks; actor8 modes depend on actor1-to-8 distance.
- **Local211, spatial controller:** chooses scripts214–217 or defaults220–223 according to actor1 proximity and Y, independent of which actor is the speaker.
- [Local213, seven-pair redraw synchronizer](MI2_ROOM55_SEVEN_PAIR_SPEECH_SYNC_20261117.md): source Vars163,165–170 keep paired objects in state1/2 with redraw suppression.

**Still unknown:** the detailed effects of children 214–218 and 220–223; they may manipulate actors/costumes/image states/sound, and the present script211 alone does not determine which. Their full original bytecode and original image resources need subsequent narrow walks.

## Why this changes P4

A room with many frames can have several **orthogonal state machines**: one driven by dialogue, one driven by **proximity and vertical position**, and one continuously synchronizing flags to graphics. Correctly reconstructing observed output will require tracking dynamic actor positions, talk actor, nested script start/stop, image states, clock, and possibly costume/occlusion; neither a background GIF nor a single linear animation timeline is adequate.

Suggested eventual regression matrix: category0/7/8/9/12, near/far boundaries at **15,20,25,31**, actorY **119/120** threshold, simultaneous-nearby priority, talk-actor off/on, script-start/stop events, source image/costume state, and native indexed framebuffer hashes. Preserve engine source tag, game edition/hash, and script PCs.

**Completion boundary:** independently source-aligned control flow, **not actual runtime state/path or graphics fidelity**.
