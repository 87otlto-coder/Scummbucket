# MI2 Room9: global70 Largo cutscene, actor-light handoff and explicit RGB cleanup (18 November 2026)

**Evidence class:** read-only original DOS VGA `MONKEY2.000/.001`; original `.001` SHA-256 `ad045372e0d49626503bb50fca29a687ec8e01ef75d9b8bca702a366d143819e`. Source decoded with an independently implemented *narrow SCUMM v5 opcode/operand walker*, checked against pinned ScummVM [v2026.4.0 script_v5.cpp](https://github.com/scummvm/scummvm/blob/v2026.4.0/engines/scumm/script_v5.cpp), [script.cpp](https://github.com/scummvm/scummvm/blob/v2026.4.0/engines/scumm/script.cpp), [room.cpp](https://github.com/scummvm/scummvm/blob/v2026.4.0/engines/scumm/room.cpp), [palette.cpp](https://github.com/scummvm/scummvm/blob/v2026.4.0/engines/scumm/palette.cpp). **No official descumm crosscheck, instrumented gameplay, original DOS test or native indexed/RGB parity.** Original game bytes, dialogue and art remain private/out of Git.

## Full source-boundary census

| Original resource | Source body absolute .001 offset | Body bytes independently consumed | Instructions | Valid PC-relative targets |
| --- | ---: | ---: | ---: | ---: |
| **Global SCRP70** (stored with Room9) | `0x0ABD96` | **1281/1281** | **215** | **4/4** |
| **Room9 ENCD** | `0x0A8AC0` | **259/259** | **54** | **15/15** |
| **Room9 LSCR201** | `0x0A8BF7` | **30/30** | **6** | no branches |
| **Room9 EXCD** | `0x0A8AB5` | **3/3** | **2** | no branches |

All detected signed branch targets lie on original decoded opcode boundaries, including the skip/override path of global70. Bytecode alignment is a source research milestone, NOT proof of original interpreter behavior or framebuffer fidelity.

## Global70: the cutscene moves across Rooms9 and10 while controlling the actor light

The source defines a scripted bartender/Largo encounter, complete with actor6's source name `Largo` and a short Room10 scene insertion. No original dialogue transcript is reproduced here.

| Global70 body PC | Independently decoded event |
| ---: | --- |
| `0x000` | begin cutscene with argument1 |
| `0x005–0x007` | register an override/skip handler and branch directly to a common cleanup section around PC0x487 if triggered |
| `0x0BF–0x0D4` | initialize actor6 costume16/name; start global108; place actor6 in **Room9** and near source object72 |
| **`0x0D8`** | **`startScript(global54,[actor6])`** |
| `0x0DE–0x217` | actor6/7 movements, original image-state changes object77/84, sounds, waits, and actor-related actions |
| **`0x21A`** | `loadRoom(10)` (not a `loadRoomWithEgo`) |
| `0x21C–0x23F` | create/place actor8 in Room10, move and wait for motion |
| **`0x242`** | `loadRoom(9)` |
| `0x244–0x247` | start Room9 local221 and move actor8 out of room |
| **`0x24A`** | **`startScript(global54,[actor6])` again**, reinitializing actor-light state on reentry |
| `0x250–0x485` | additional actor, object, sound and dialogue actions; actor6 eventually placed in room0 |
| `0x487–0x4E2` | two conditional source cleanup branches, distinguished by VAR_OVERRIDE and the registered cutscene skip |
| **`0x4F1`** | **`stopScript(global54)`** |
| `0x4F3` | check **`Var49=VAR_VIDEOMODE == 19`** |
| **`0x4FA`** | when VGA, `roomOps(SO_ROOM_INTENSITY,255,208,255)`: reapply **full intensity** to original base RGB palette slots **208–255** |
| `0x4FF–0x500` | endCutscene, stopObjectCode |

**Nuance:** `roomOps(...,255,208,255)` re-derives RGB from the base palette via pinned `darkenPalette`; for original v5 the renderer caps channels at252. It is *not* a guarantee that arbitrary runtime palette values are restored byte-for-byte if another script modified the same slots. It does encode an explicit intended full-intensity clean-up of the second actor-lighting range.

**In Room10**, while global54 is running, its actor-room guard can prevent palette updates because actor6 is associated with Room9 rather than current Room10. Returning to Room9 and starting global54 again resets its cached scale/actor-local state. Exact per-frame scheduler visibility and interaction with loading the new room palette remain unobserved.

## Important engine-source finding: global54 is a singleton, not one concurrent script per actor

Pinned `o5_startScript` calls `runScript(script,(opcode&0x20)!=0,(opcode&0x40)!=0,data)`. The original commands above use immediate non-recursive `0x2A`, so `recursive=false`. In pinned `ScummEngine::runScript`, non-recursive calls first **`stopScript(script)`**, then initialize a new slot and its locals before executing nested. Therefore:

- `startScript(54,[actor6])` **replaces an existing global54 instance**, if one was running, including any existing instance with actor9 as its argument.
- `startScript(54,[actor6])` later in the same global70 is also a **replacement/restart**, NOT an additional actor light.
- global49 and global54 remain separate IDs, so they **can** coexist and shade separate palette ranges (192–207 for Ego, 208–255 for selected actor). Multiple independent global54 actor trackers **do not** coexist under these non-recursive calls.

This corrects any overly broad impression from prior dual-lighting research that Room9 could have two simultaneous instances of script54. Source permits at most one ordinary non-recursive instance while the other global49 may remain active.

### Room9's own entry and actor9 initializer

- **ENCD PC0x000** sets six X breakpoints in Var285..290; **PC0x010** seeds six brightness values Var291..296; **PC0x01A** starts **global49** for Ego palette range192–207.
- **ENCD PC0x02D–0x046** explicitly checks `isScriptRunning(global70)`. If it is running, it **yields at PC0x03C** and polls until it stops before continuing to **local206**. If not running, it starts local200 and skips the wait. Room9 thus has an *entry synchronization barrier* against the active global70 cutscene; it does not blindly start all animations at once.
- **LSCR201** has six instructions, including **PC0x00E `startScript(54,[actor9])`**; actor9 is also placed in Room9 at native (33,108). The natural caller of LSCR201 is not established by ENCD (it does **not** directly call201), so actor9 light activation is *source-possible*, not proven on ordinary entry.
- **EXCD** contains only `stopSound(47)` and stop, and **does not directly stop either global light script**.

## Why room-change cleanup must be modeled explicitly

Pinned `room.cpp::startScene` invokes `killScriptsAndResources()` at transitions, and pinned `script.cpp::killScriptsAndResources` kills **WIO_ROOM/WIO_FLOBJECT/WIO_LOCAL** scripts but **not WIO_GLOBAL scripts**. Global49 and54 are **not automatically canceled merely for being started in a physical room**. Source-authored **stopScript**, self-stop or replacement calls are important. The scripts themselves check whether the target actor is in the logical current room, which can suppress modifications but does **not** itself stop them.

**Risk to validate:** A running global49 or54 can survive a room transition until stopped or replaced. Do not assert accidental leakage into a different scene without tracing the exact game call path, active room, actor room, Var49 mode and current palette; initial palette loading also resets RGB.

## Validation gates and implementation consequence

- Official descumm -5 -o on SCRP70 and Room9 ENCD/LSCR201/EXCD; crosscheck 215 instructions and 4 branch targets; verify 54 call PCs 0x0D8/0x24A and stop at0x4F1.
- Capture both the full and override-skip global70 branches with script slots, actor6/9 X and room, current physical/logical room, global49/54 state and palette banks192–207/208–255 before/during/after Room10 transition.
- Compare both **original indexed pixels and active RGB palette**. Frame hashes alone are insufficient: RGB lighting changes while indexed graphics may stay identical.
- Preserve script start flags (recursive/freeze-resistant), source room, calling script PC, tracked actor, Y/box constraints, palette base and actual scheduler phase in P4 event IR. Do not synthesize two active script54 trackers.
- Keep original resource archive, outputs and captures in FIXTURE; source code and research in SOURCE; external ScummVM in TOOLS. No additional workspace root folders.

**Source-complete on the named scripts; runtime behavior and native pixel fidelity remain unverified.**
