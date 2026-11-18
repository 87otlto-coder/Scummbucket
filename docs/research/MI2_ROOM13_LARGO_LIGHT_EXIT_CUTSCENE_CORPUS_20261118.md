# MI2 Room13: multiple Largo cutscenes, lighting lifecycle, and cross-room exits (18 November 2026)

**Evidence category:** original DOS VGA archive `MONKEY2.000/.001` read-only, original .001 SHA-256 `ad045372e0d49626503bb50fca29a687ec8e01ef75d9b8bca702a366d143819e`. Complete narrow v5 bytecode/operand walks of original ENCD and five selected LSCR bodies with signed branch destination consistency, crosschecked with pinned [ScummVM v2026.4.0 script_v5.cpp](https://github.com/scummvm/scummvm/blob/v2026.4.0/engines/scumm/script_v5.cpp), [script.cpp](https://github.com/scummvm/scummvm/blob/v2026.4.0/engines/scumm/script.cpp), [room.cpp](https://github.com/scummvm/scummvm/blob/v2026.4.0/engines/scumm/room.cpp), and [palette.cpp](https://github.com/scummvm/scummvm/blob/v2026.4.0/engines/scumm/palette.cpp). These are research source-aligned walks, **not official descumm corroboration, actual runtime paths, indexed framebuffer or RGB palette acceptance**. Copyrighted original dialogue, art and script data remain private/outside Git.

## Exhaustive narrow source-bytecode results

| Original physical Room13 source | .001 bytecode body offset | Body consumed | Instructions | Aligned PC-relative branch targets |
| --- | --- | ---: | ---: | ---: |
| ENCD | `0x0F8FB1` | **270/270** | **54** | **18/18** |
| LSCR200 | `0x0F90D2` | **2346/2346** | **421** | **15/15** |
| LSCR201 | `0x0F9A05` | **83/83** | **14** | **1/1** |
| LSCR209 | `0x0FA118` | **576/576** | **78** | **4/4** |
| LSCR211 | `0x0FA3DA` | **637/637** | **110** | **15/15** |
| LSCR212 | `0x0FA660` | **301/301** | **44** | **11/11** |
| **Total** | | **4,213 bytes** | **721** | **64/64** |

Room13 EXCD is a one-byte `stopObjectCode`, with **no explicit stopScript(49/54) in EXCD itself**. Other Room13 locals and object verb handlers are NOT included in this complete-walk census. Thus do not call the **entire room** source-decoded.

## Entry-driven branching: one light curve, alternative Largo scenarios

The ENCD itself initializes **Var285..290** to `[0,0,225,320,320,320]` (X knots), **Var291..296** to `[0,100,235,200,200,200]` (lighting scales), and **starts global49 at PC0x01A**, affecting RGB indices **192–207** based on Ego X. It flags two walkboxes and reads source puzzle state/difficulty and object ownership.

A later branch at ENCD **PC0x0BD** reads `getOwner(object117)` and compares to `Var1=VAR_EGO`, then tests source Bit56 and Bit513; depending on values the original code:
- starts **local201**, local203, local202, local204 at PCs **0x0D5/0D8/0DB/0DE**, or
- starts **local211** at PC**0x0FF**, or
- starts **local212** at PC**0x10A**, or
- bypasses these branches.

These are **mutually conditional source paths**, not simultaneous runtime events. The semantic identity of original object117 and all puzzle bits should be independently corroborated by its OBCD/OBNA and full story triggers before labeling the alternative states.

## Local201: short actor6 light setup

The **83-byte, 14-instruction** script performs sound calls, initializes actor6 as **Largo** (original actorOps name text), positions him in physical Room13 at **(135,109)**, and at **PC0x04C** executes `startScript(global54,[actor6])`. Since this uses original immediate **opcode0x2A (non-recursive)**, pinned `ScummEngine::runScript` first stops any previous global54 instance before initializing a new one. The actor6 controller shades **208–255**, separate from Ego script49's **192–207** range.

## Three self-contained exits with explicit global54 stop

**LSCR209 (576 bytes, 78 instructions, 4 branch targets):** starts a cutscene, manipulates walkbox flags 5/6, waits on global213, positions Largo in Room13, starts global54 for actor6 at **PC0x07F** and sequences actor movement and dialogue. On convergence near **PC0x22E**, it executes **`stopScript(54)`**, restores boxes and ends. Does **not** issue an explicit full-intensity `SO_ROOM_INTENSITY(...,208,255)` in this script; this is a source distinction versus Room9 global70, not proof of a visible palette error.

**LSCR211 (637 bytes, 110 instructions, 15 branch targets):** starts its own cutscene; places actor6, starts global54 at **PC0x04A**, uses walking, yields and dialogue; includes a small randomized dialogue-selection branch. At **PC0x25B**, **stopScript(54)**, restores walkboxes, ends cutscene, starts global151 with args `[13,12]`, then requests **`loadRoomWithEgo(object100, Room12, -1,-1)`** at PC0x274. This is source-authorized cutscene-to-new-room traversal, not a verified visible actor path.

**LSCR212 (301 bytes, 44 instructions, 11 branch targets):** begins cutscene then **calls local201** at PC0x005 (which starts global54 for actor6). At PC0x008/0x009/0x00D it yields and tests `isScriptRunning(201)` until complete; then randomly selects one of five authored dialogue variants, animates actors, moves Guybrush, removes actor6, and **stops global54 at PC0x110**. It then restores walkbox flags, ends cutscene, starts global151 `[13,12]`, and requests **Room12** at PC0x124.

This reveals a **reuse pattern**: short scene setup (201) starts actor light54; two alternative rejection/exit cutscenes (211/212) both converge on the same cross-room endpoint and explicitly terminate the light before leaving.

## Long LSCR200: lighting teardown before scene transition to Room21

The longest script is **2346 bytes, 421 instructions**, with **156 source `breakHere` yields**, 60 `animateActor` operations, 36 `wait` operations, 33 `soundKludge` operations, and 15 valid signed branches. This is a multi-phase **actor/costume/sound and object-state cutscene**, not a single OBIM animation or a promise of 156 visible unique frames.

Key verified ending PCs:
- **PC0x090D**: `stopScript(global54)`.
- **PC0x090F**: endCutscene.
- **PC0x0910**: set source Bit535=1 (variable reference `0x8217`).
- **PC0x0915**: `roomOps(SO_ROOM_FADE,257)`. Pinned v5 sets `_switchRoomEffect=1`, `_switchRoomEffect2=1` based on word257; this is **an authored transition effect**, not a hard-coded palette animation.
- **PC0x0919**: place Ego actor in Room21.
- **PC0x091D**: Ego source position `(300,112)`.
- **PC0x0924**: `loadRoom(21)` (direct script room load, not `loadRoomWithEgo`).
- **PC0x0926**: pan camera to source X480.
- **PC0x0929**: terminate.

**Caution:** Under pinned ScummVM's `startScene`, room loads and script yields can interact with script slot cancellation; this is original *static instruction order*, not a guarantee all post-room-change instructions execute with specific rendering timing. The actual visual fade, actor animation and audio timing need an engine trace.

## Palette-lifecycle implications

- **Global49 and global54 are both global scripts.** Pinned `room.cpp::startScene` invokes `killScriptsAndResources` on room transitions, and pinned `script.cpp::killScriptsAndResources` cancels local/object scripts, **not global script slots**. Thus a global light does not automatically end when its invoking room-local script dies.
- **Most decoded Room13 cutscenes deliberately stop global54**, including local200/209/211/212, before a scene change or endpoint. This is consistent with explicitly managing the actor-light lifecycle.
- Room13's EXCD does not kill 49/54; other source paths and the engine's active actor-room guard may be involved. **Do not claim persistent palette leakage** without a genuine runtime case, target actor and live palette hashes.
- The prior [Room9 global70 lifecycle](MI2_ROOM9_GLOBAL70_DUAL_LIGHTING_CUTSCENE_20261118.md) **explicitly restores full intensity 208–255 after stopping54**. By contrast these Room13 endings have **no adjacent full-intensity roomOps**; they often leave or reload a room, which may reset colors through the normal scene-loading path.

## Future validation: strong reproducible targets

1. Verify ENCD branching across relevant ownership/difficulty/Bit56/Bit513 states without altering original archives; preserve selected branch and call stack.
2. Observe scripts201/209/211/212 and the large 200 cutscene at native indexed resolution with exact original game version, actor positions, palette banks192–207/208–255, sounds and cutscene skip modes.
3. For LSCR200 capture `stopScript54` → endCutscene → fade(257) → Room21/camera480; compare native RGB before/after, mask layers, actor cels and room transition timing.
4. Official pinned descumm -5 -o for all six selected scripts; the independent custom walker provides structural checks, NOT a replacement for descumm/original runtime acceptance.
5. Preserve `SCRIPT_START actorID`, `SCRIPT_STOP`, `PALETTE_INTENSITY range`, `ROOM_FADE`, `ACTOR_ACTION`, `ROOM_CHANGE`, `CAMERA_PAN` as separate event types, each with evidence provenance; a scene can mix all of them.
6. Keep game archives/captures in FIXTURE, third-party engines in TOOLS, research and tests under SOURCE; no copyrighted resources in Git.

**Status:** source-aligned cutscene/lighting interactions with explicit uncertainty. No runtime or pixel fidelity claims.
