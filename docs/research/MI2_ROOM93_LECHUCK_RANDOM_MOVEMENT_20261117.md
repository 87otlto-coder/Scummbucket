# MI2 Room93 randomized LeChuck actor appearance — LSCR204 → global154 (2026-11-17)

**Evidence:** read-only original DOS VGA `MONKEY2.001`, SHA-256 `ad045372e0d49626503bb50fca29a687ec8e01ef75d9b8bca702a366d143819e`. Decoded v5 original script bytecode with private narrow instruction parser, then checked named instructions against ScummVM v2026.4.0 [script_v5.cpp](https://github.com/scummvm/scummvm/blob/v2026.4.0/engines/scumm/script_v5.cpp), [script.cpp](https://github.com/scummvm/scummvm/blob/v2026.4.0/engines/scumm/script.cpp). No runtime, official descumm, original DOS stepping or image parity. All copyrighted original bytes are excluded.

## Full original script evidence

| Script | Stored physical LFLF | Source body offset | Length / parsed | Instructions | Relative branches |
| --- | ---: | ---: | --- | ---: | --- |
| **Room93 LSCR204** | 93 | `0x767BD9` | **179/179** | **37** | 16/16 valid |
| **Global SCRP[154]** | 93 | `0x769A97` | **180/180** | **38** | 10/10 valid |

The Room93 ENCD (fully decoded in [pseudo-room scene report](MI2_PSEUDOROOMS_ROOM93_SCENE_INSTANCES_20261117.md)) runs local204 **conditionally on Bit731**, after initializing the shared physical Room93 resource for one of its eight logical room IDs160–167.

### Local204: source-directed randomized doorway selection

- At script PC0x0000: **`delay(60)`** script-time units.
- At PC0x0004: condition on Bit731; if absent, `stopScript(0)` in source (exact stopScript(0) behavior confirmed via ScummVM script handler when runtime tests are eventually prepared).
- Random `getRandomNr(Var587)` (inclusive max) into Var100; continue the event branch **only if selected value is zero**. Otherwise issue `delayVariable(Var588)` and repeat.
- When a candidate event occurs, choose one of the two *logical door objects*: **872 at native x46**, **873 at native x263**, using an independent random0/1 result, then adjust the chosen door for logical-room boundary conditions `Var4==160` and `Var4==164`.
- The code tests Ego actor X through `o5_getActorX` and branches based on **100 and220 pixel thresholds**, with special handling at the logical-room edges so the selected appearance side is not purely random.
- At PC0x009D: **`chainScript(154,[Local0 door, Local1 X, 120])`**. This is not an ordinary start-and-return or an animation-frame yield.

**Critical source-semantic distinction:** ScummVM `o5_chainScript` kills the current script slot and immediately calls `runScript` for the replacement. Thus once event selection reaches global154, **LSCR204's polling loop no longer resumes by itself**. It is a randomized *trigger until first selected event* unless some other external script starts 204 again. Do not label it an unconditional perpetual ambient NPC-loop. This corrects the looser descriptive wording in the earlier short source notebook.

### Global154: real actor costume animation rather than OBIM states

- PC0x0000: `startScript(164)`; the separate effects of global164 are not yet decoded.
- PC0x0003: initialize **actor3** defaults, talk colour, walk speed (4,1), then set original **actor name string “LeChuck”** and costume **77**. This name is **stored explicitly as original `o5_actorOps::SO_ACTOR_NAME` bytes**, not inferred from graphics.
- PC0x0017: place actor3 into **current logical room Var4**, then `putActorAtObject(3, Local0 door)`.
- PC0x001F: set actor class flags and animate actor3 action1.
- PC0x0039: if `Var583` nonzero, start script number from Var583, and **wait while that script is running**.
- Otherwise if Local1 nonzero, enter a cutscene: `walkActorTo(3,Local1,Local2=120)`; register override; **`wait(actor3)`** until movement ends; capture actor3 X/Y, and proceed through override/cleanup.
- Later code conditionally changes Ego costume to **126**, starts other global scripts **143/153**, waits until script153 stops, invokes a sentence action, and either runs global144 or puts actor3 into room0.
- Source terminal state **stops the script** after the actor cleanup.

**Evidence boundary:** The exact rendered costume77 cel sequence and actor Z-clip, movement speed/turning, any dialogue sound, and the behavior of global143/153/164 must be independently captured or decoded before we can reconstruct the full event. Merely knowing costume ID77 and scripted waypoints does not establish all animation cels or pixel-perfect positioning.

## Why this is central to P4

The visual presentation of one pseudo-room scene can contain:
1. Physical shared **Room93 background**;
2. Current logical-room-specific object images/positions and walkbox flags;
3. An actor-X-dependent palette brightness controller (**global49**);
4. A random chance to start an actor costume sequence (**local204**) and then replace its own script slot with a **global actor-motion script154**;
5. Room93's interactive elevator-door image-state animations (**local205/206**), and other state-dependent objects;
6. Persistent exit effects `Bit93` at virtual corridor endpoints.

This is a genuine **scripted environmental actor plus dynamic lighting** class, substantially beyond concatenating stored object states. It requires an event timeline with room aliases, actor movement, costume cels, palette transforms and nested/chained scripts.

## Next checks

- Official `descumm` on both source bodies and accompanying Room93 ENCD.
- Source-align global164,143,153,144 and inspect actor3 costume77 format + Z plane and dynamically clipped visible positions; avoid claiming all runtime effects before following the remaining global scripts.
- Use pinned ScummVM debug tracing: with `Var49=19`, document `Bit731,Var587,Var588,Var583,Var4,EgoX`, source PCs and random decisions. Capture actual costume and indexed native frame stream and compare to independently reconstructed output.
- Do not infer that a low numeric script ID is local without room qualifier; global154 and local204 have distinct identities.
- Record natural entry/difficulty/skip branches and separate original DOS interpreter oracle only if discrepancies appear.

**Status:** original archive script boundaries align completely; behavior is source-projected, not gameplay-observed.
