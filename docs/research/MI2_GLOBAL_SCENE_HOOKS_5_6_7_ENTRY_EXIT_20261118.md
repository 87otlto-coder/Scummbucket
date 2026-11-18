# MI2 complete source entry/exit hook chain: global5/6/7 (18 November 2026)

**Evidence class:** original DOS VGA MONKEY2.000/.001 read-only, .001 SHA-256 `ad045372e0d49626503bb50fca29a687ec8e01ef75d9b8bca702a366d143819e`; original SCRP1 source-assignment span and all three indexed global script5/6/7 bodies independently consumed; pinned [ScummVM v2026.4.0 vars.cpp](https://github.com/scummvm/scummvm/blob/v2026.4.0/engines/scumm/vars.cpp), [script.cpp](https://github.com/scummvm/scummvm/blob/v2026.4.0/engines/scumm/script.cpp), [room.cpp](https://github.com/scummvm/scummvm/blob/v2026.4.0/engines/scumm/room.cpp), [script_v5.cpp](https://github.com/scummvm/scummvm/blob/v2026.4.0/engines/scumm/script_v5.cpp). **No official descumm, actual room-transition run, original DOS interpreter comparison or native pixel/RGB acceptance.** Original assets, archives and source-text transcripts remain private.

## Critical original source fact: global script1 explicitly assigns ALL three global scene hooks

The original indexed `SCRP[1]` bytecode body starts at decoded .001 file offset `0x35513`. It contains a contiguous, correctly aligned sequence of v5 `move` instructions:

| SCRP1 bytecode PC | Absolute original .001 byte offset | Source assignment | Pinned ScummVM variable meaning |
| ---: | ---: | --- | --- |
| **0x855** | **0x35D68** | Var[28]=5 | `VAR_ENTRY_SCRIPT = 28` |
| **0x85A** | **0x35D6D** | Var[29]=6 | `VAR_ENTRY_SCRIPT2 = 29` |
| **0x85F** | **0x35D72** | Var[30]=7 | `VAR_EXIT_SCRIPT = 30` |

The source script1 body is large and has NOT been fully independently disassembled; **this contiguous three-instruction span is operand-aligned** and the names/meaning of the variable indices come directly from pinned vars.cpp. It establishes the game's *authored hook assignment*, conditional on script1's setup path actually executing. The source has no aligned write to Var31=VAR_EXIT_SCRIPT2 in this span.

### Actual pinned ScummVM callback order

`startScene` in pinned room.cpp invokes `runExitScript()` **before** `killScriptsAndResources()`, unload/reload/room setup, and subsequently `runEntryScript()`. In pinned script.cpp the hook order is:

1. **Exit:** `runScript(VAR_EXIT_SCRIPT)` = **global7**, then execute physical ROOM's `EXCD`, then optionally `VAR_EXIT_SCRIPT2`.
2. **Room transition:** kill physical room-local and object scripts, stop color cycles, initialize new room, palettes, objects, actors/camera.
3. **Entry:** `runScript(VAR_ENTRY_SCRIPT)` = **global5**, then execute physical ROOM's `ENCD`, then `runScript(VAR_ENTRY_SCRIPT2)` = **global6**.

**The decisive correction:** generic `killScriptsAndResources` does NOT terminate global script IDs49/54/167 by itself, but the game's **installed global7 exit hook does**. Therefore under a normally initialized original game, source-defined room changes have a built-in centralized lighting cleanup path. Do not claim global palette script leakage from generic engine behavior while ignoring this original hook.

## All three global script bodies fully narrow-walked

| Original indexed SCRP | Source body absolute file offset | Bytes consumed | Instructions | Valid relative branches |
| ---: | ---: | ---: | ---: | ---: |
| **5** | **0x37A9C** | **23/23** | **5** | **1/1** |
| **6** | **0x37ABB** | **104/104** | **15** | **2/2** |
| **7** | **0x37B2B** | **166/166** | **17** | **5/5** |

These are syntax-aligned source facts, not a live scene trace.

### Entry hook 5: reset precisely Var160–173, before the physical ENCD

Script5 source:
- initialize **Var100=0**;
- assign **Var[160+Var100] =0** using SCUMM v5 indexed-variable flag `0x2000` and indirect index `Var100`;
- increment Var100;
- `isLess(Var100,13)` branches back while Var100 is **≤13** under pinned v5 reversed-branch polarity;
- stop when Var100 reaches **14**.

Therefore the source loop clears **14 consecutive globals: Var160,161,...,173 (inclusive)** on every path where entry hook5 runs. **Important connection:** Var160 is the additive RGB scale offset in [Room21 camera-responsive lighting](MI2_ROOM21_CAMERA_COUPLED_THREE_BANK_LIGHTING_20261118.md), and Vars163/165–170 help synchronize the source [Room55 party-animation flags](MI2_ROOM55_SEVEN_PAIR_SPEECH_SYNC_20261117.md). At the moment of ENCD invocation these values have just been reset to zero (unless some additional global reentrant code intervenes). This is a source-coded per-scene state reset, not a general property of the archive variable bank.

### Entry hook 6: VGA palette slots and sentence/UI reinitialization, AFTER physical ENCD

Global6 source starts with a VGA guard `isEqual(Var49=VAR_VIDEOMODE,19)`. On VGA path it calls **o5_roomOps::SO_ROOM_PALETTE**, setting individual active RGB palette indices:
- **index2** from source globals **Var469,470,471** (R,G,B);
- **index3** from **Var472,473,474**;
- **index1** from **Var475,476,477**;
- **index6** from **Var478,479,480**.

On non-VGA path it writes four explicit source RGB triplets to those same slots (two black, two purple-ish); the exact appearance and render mode are not tested. Later script6 starts global11 and global12, assigns Var114 from Var38 and clears the active queued sentence using the special `doSentence(254)` operation.

Both global11 and12 were independently narrow-walked in this session (36/36 bytes, eight instructions and 86/86 bytes, ten instructions respectively); script11 resets several conversation/verb tracking vars, while script12 constructs/displays a context-sensitive UI verb. Neither is classified as background animation.

**Order matters:** these four palette writes occur **after ENCD** and after any ENCD-triggered nested script writes. They target indices1/2/3/6, distinct from the main global49/54 dynamic ranges but can affect indexed art/UI pixels that use the low slots.

### Exit hook 7: centralized cancellation of three source animation mechanisms

Global7 source at PCs **0x026/0x028/0x02A** calls:
- `stopScript(49)` — actor1/Ego-X lighting for RGB range192–207;
- `stopScript(167)` — **all global167 script slots**, including two recursively started concurrent random-intensity effects in physical Room8;
- `stopScript(54)` — actor-targeted RGB range208–255.

Pinned `ScummEngine::stopScript(scriptID)` iterates all active slots of matching script ID. Thus one stop167 call cancels **all concurrently recursive instances**, not merely the last started slot. Global7 also stores current Var4 in Var102, resets Var54, and has a source diagnostic for difficulty mismatch on game load.

## Consequences for previously unresolved source interpretations

- **Room8 and Room15 EXCD** each merely unlocks a sound resource; they have **no direct stop167**. That is entirely compatible with the game's **global7 exit hook** stopping both Room8 random-RGB channels before local EXCD. See [global167 recursive palette mechanism](MI2_GLOBAL167_CONCURRENT_RANDOM_PALETTE_ROOMS8_15_20261118.md).
- **Room9 global70 crosses to Room10 and back.** Under the installed global7 hook, the first room change **stops global54**, and the original cutscene's second start54 after returning to Room9 is a deliberate and necessary **re-initialization** in the source sequence. Do not describe a global54 instance as guaranteed alive throughout Room10 merely because generic killScriptsAndResources ignores global slots.
- **Room13→Room21 cutscene** stops54 directly and then the source exit hook also stops49/167/54. Room21 then runs entry global5 (reset Var160=0), its ENCD (which starts local208/global49), and entry global6 (four low-index palette colors).
- **Room21 local208 initial scale:** previous counterfactual table with Var160=0 has a new source rationale: **global5 clears Var160 immediately before ENCD**. Future writes to Var160 while remaining in the room could still change later scale; no runtime observation.
- **Room55 speaking animation:** global5 resets its shared state vars before local ENCD200/211/212/213 initialize them; do not attribute all nonzero state flags to savegame persistence without accounting for the entry hook.

## Next acceptance and research gates

1. Verify authentic original startup reaches SCRP1's three assignments, then capture the **actual hook order** by instrumented ScummVM and original DOS if discrepant.
2. Trace a Room8 entry with **two recursive global167 script slots**, then a normal exit: original exit7 stop167 occurs before room-local EXCD; verify no residual room-to-room RGB writes.
3. Trace Room21 entry: Var160 reset in global5, local208 first RGB values, subsequent global6 low palette slots, and physical/global light changes.
4. Descumm global scripts1 (at least assignments)/5/6/7, and crosscheck nested script start/stop phase, scene resource palettes and native indexed+RGB hashes.

**Evidence status: original bytecode and pinned implementation source only; runtime and pixel fidelity still unverified.**
