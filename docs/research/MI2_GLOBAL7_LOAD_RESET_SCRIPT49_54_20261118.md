# MI2 global7 — load-state cleanup for actor-dependent palette scripts (18 November 2026)

**Evidence:** original DOS VGA MONKEY2.001 read-only, SHA-256 ad045372e0d49626503bb50fca29a687ec8e01ef75d9b8bca702a366d143819e. Original indexed global SCRP7 source body at decoded .001 offset **0x37B2B**, **166/166 bytes fully walked**, **17 instructions**, **5/5 signed branch targets aligned**. Opcode interpretation from pinned [ScummVM v2026.4.0 script_v5.cpp](https://github.com/scummvm/scummvm/blob/v2026.4.0/engines/scumm/script_v5.cpp), [script.cpp](https://github.com/scummvm/scummvm/blob/v2026.4.0/engines/scumm/script.cpp), [vars.cpp](https://github.com/scummvm/scummvm/blob/v2026.4.0/engines/scumm/vars.cpp). **No official descumm, runtime, verified load invocation, original interpreter or native indexed/RGB comparison.** No copyrighted game data committed.

## Exact aligned reset actions

| Source PC | Original v5 operation |
| ---: | --- |
| 0x000 | move Var102=Var4 (current logical room) |
| 0x005 | move Var54=-80 |
| 0x00A | Configure actor255/on-screen text properties |
| 0x016–0x025 | If Var157 nonzero, modify its verb color then clear Var157 |
| **0x026** | **stopScript(global49)** — Ego-X-controller, RGB palette192–207 |
| **0x028** | **stopScript(global167)** — additional global whose mechanism still needs discovery |
| **0x02A** | **stopScript(global54)** — actor-specific controller, RGB palette208–255 |
| 0x02C–0x0A4 | Compare Bit567 (source Regular/Easy difficulty) with Var98; conditional original on-screen diagnostic refers to the selected mode changing when a game is loaded; update Var98 |
| 0x0A5 | stop |

Those source messages support labeling this **load/reinitialization-associated code**, but they do NOT establish automatic invocation on every save/load or restart. No complete caller trace for global7 yet exists; an indirect/engine-origin caller remains a possibility.

## Architectural consequence

Pinned ScummVM startScene invokes killScriptsAndResources on a room change, which terminates room-object/local scripts but **does not terminate global script slots**. Global49 and54 can survive room transitions, be stopped by explicit source calls or be replaced by nonrecursive new starts. Script7 is one original authored path stopping **both** controllers together. Do not model the palette lifecycle using room ID changes alone.

Cross-reference [12-room lighting atlas](MI2_GLOBAL49_EGO_LIGHTING_ATLAS_20261118.md), [Room9 cross-room light cutscene](MI2_ROOM9_GLOBAL70_DUAL_LIGHTING_CUTSCENE_20261118.md), [Room13 cutscene exits](MI2_ROOM13_LARGO_LIGHT_EXIT_CUTSCENE_CORPUS_20261118.md) and [Room21 camera-coupled lighting](MI2_ROOM21_CAMERA_COUPLED_THREE_BANK_LIGHTING_20261118.md).

**Next tests:** identify actual global7 caller, decode global167 and observe scripted save-load around active 49/54 with native RGB palette hashes, source script slot/PC, logical/physical rooms and current actor X. No genuine runtime or pixel fidelity established.
