# MI2 bone-puzzle continuation: Room72 → Room73 door animation → Room74 source route (17 November 2026)

**Evidence:** read-only original DOS VGA `MONKEY2.000/.001`; original `MONKEY2.001` SHA-256 `ad045372e0d49626503bb50fca29a687ec8e01ef75d9b8bca702a366d143819e`. Recovered original `OBCD/OBNA` names and decoded specific short `VERB`, `LSCR` and global script opcode spans using pinned [ScummVM v2026.4.0 script_v5.cpp](https://github.com/scummvm/scummvm/blob/v2026.4.0/engines/scumm/script_v5.cpp). **Source path only, not original gameplay observation, complete independent descumm, natural caller/branch reachability, sound semantics, or native pixel fidelity.** No original game resource chunks or imagery committed.

## Why adjacent rooms matter

- **Room71** includes tunnel and sign objects; its ENCD resets **Var457 and Var459 in Regular Mode**. [Eight bone-statue sequences](MI2_ROOM72_BONE_STATUE_EIGHT_PATHS_20261117.md) and [conditional next-object injection](MI2_ROOM72_GUARANTEED_NEXT_STATUE_LAYOUT_20261117.md) show how Room72 compares four three-letter statue tokens from String46.
- **Room72 LSCR205** sets `Bit365=1` when a successful three-symbol match advances Var459 to12, and has a state-conditional `loadRoomWithEgo(object749,room73, x145,y120)` source call. Object749 is original Room73 source OBCD name **`exit to passage`**. Whether room-change script cancellation makes this the final visible transition must be observed; subsequent bytes in the same routine also contain an alternate logical-room132 load path.
- **Room73** original source objects **750 `huge door`**, **751 `massive locks`**, **752 `doggie door`**, and **749 `exit to passage`**. Source has an empty ENCD and EXCD; its interactive scripts create the visible change.
- **Room74** source OBCD names include **753 `massive door`**, **754 `LeChuck's voodoo throne`**, and **755 `voodoo key to jail`**. This anchors what kind of downstream asset location the short room73 interaction can reach, without relying on inferred artwork.

## Fully source-readable Room73 small animation

The Room73 `LSCR200` tagged chunk begins `0x5F5CCA`, with **36-byte script body**. Source opcode sequence:

1. `beginCutscene([2])`.
2. `animateActor(Ego,action10)`, `delay(20)` (script units, not 20 display frames).
3. `startScript(global25,[object752])`. This is an **explicit call with object752 argument**, not a numeric local script slot.
4. `delay(20)`, `animateActor(Ego,action3)`.
5. `setClass(object752,32)` (clear class32, per pinned v5 class-bit convention); `endCutscene`; stop.

The indexed **global script25** resides with original physical Room4, not Room73. Its source contains a `getObjectState(Local0)` test and `setState(Local0,1)` plus character/sound operations on the eligible branch. Thus this Room73 short scene delegates an object state transition for the **doggie door** while Guybrush performs a timed costume action. Global25's full code branches and original game visuals still require full independent descumm/engine tracing.

## Original interaction callers and room74 traversal

- Room73 original `huge door` object750 has a **shared VERB handler for verbs2,5,7** at decoded source **`0x5F5C8C`**. It reads `getState(object752)`, compares with **0** and, if the state is zero, **starts Room73 local script200**. This is a directly source-coded *door state→animated cutscene* event route.
- Room73 original `doggie door` object752 has a **verb11 handler** at **`0x5F5AC7`**: when its own state is **1**, it invokes `loadRoomWithEgo(object753,room74,-1,-1)`. Object753 is original Room74 **massive door**.
- Room73 doggie-door verbs2/3/7 invoke global script25 or26 with a variable object argument depending on its state. These are additional state-aware interactions and **not** proof the same cutscene occurs for all verbs.

This supplies an exact source-driven chain:

`four matching Room72 bone tokens → Bit365 progression → authored Room73 transition request → Room73 huge-door handler (if doggie-door state0) → local200 Guybrush/door state animation → doggie-door state1 permits authored Room74 transition`.

**Scope guard:** The chain is a **composition of independent source-coded conditions**, not observed natural gameplay. Do not claim it always executes contiguously or call it fully reconstructed.

## P4/P6 implications

A future scene preview should support a short **conditional door animation** triggered through a logical object handler, with Guybrush pose changes, a delegated global script changing a physical room object, 20-unit script delays, and an interaction-dependent subsequent room transition. The global script's *storage room (4)* is different from its *execution room (73)*, as elsewhere in MI2; asset ownership and script resource origin must remain separate fields.

**Future verification:** official `descumm -5 -o` on Room73 LSCR200, object750/752 handlers and global25/26; instrument real Room72->73 and 73->74 source-call progression, status of Room73 doggie-door object752, actor/costume timing, Z-masking, RGB/indexed front-buffer hashes and exact active script states; capture actual room-change script cancellation vs continued source execution. Original game archives read-only; captures stay under `FIXTURE`.
