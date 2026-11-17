# MI2 Room97: source-coded imported-object animation during multi-choice dialogue (17 November 2026)

**Evidence:** read-only original DOS VGA MONKEY2.000/.001 (MONKEY2.001 SHA-256 ad045372e0d49626503bb50fca29a687ec8e01ef75d9b8bca702a366d143819e), independently aligned source bytecode with a private narrow v5 walker, cross-checked against pinned ScummVM v2026.4.0 [script_v5.cpp](https://github.com/scummvm/scummvm/blob/v2026.4.0/engines/scumm/script_v5.cpp), including o5_verbOps, o5_cursorCommand, o5_getInventoryCount, o5_drawObject, o5_print, o5_startScript and o5_stopScript, and [object.cpp::loadFlObject](https://github.com/scummvm/scummvm/blob/v2026.4.0/engines/scumm/object.cpp). **Static code interpretation, not runtime or original-DOS verification, not official descumm crosscheck or indexed-pixel acceptance.** No game bytes committed.

## Completely aligned source

| Script | Bytecode body offset | Bytes | Instruction boundaries | Valid relative jumps |
| --- | --- | ---: | ---: | ---: |
| Room97 LSCR202 (main interactive script) | 0x7CA5CF | **2343/2343** | **211** | **34/34** |
| Room97 LSCR213 (background object animator) | 0x7CB3D2 | **98/98** | **19** | **8/8** |
| Room97 LSCR212 (another finite five-image loop) | 0x7CB36E | **91/91** | **26** | no conditional jumps |
| Room97 LSCR208 (caller of 212) | 0x7CB109 | **228/228** | **122** | 3/3 |

The prior source-bank report accurately identified LSCR213 as an aligned loop but had not established its caller. **That uncertainty is resolved here by the full LSCR202 decode.**

### Main LSCR202: original control timeline

- PC0x0000–0x0229: takes control of input/cursor, runs actor Ego animations, changes original Room97 object1048 and object1063 states, issues many timed prompts/delays, and begins actor9 setup. This is script-controlled dialogue, not independent ambient scenery.
- PC0x023F: draw imported **object1096** (source bank100) at 8-pixel grid **(7,2)**.
- PC0x0247: draw imported **object1098** (source bank100) at grid **(14,6)**.
- PC0x024F: draw imported **object1097** (source bank100) at grid **(11,6)**.
- PC0x025C–0x0266: animate **object1097** through state1..3 using one breakHere per chosen image step.
- **PC0x026D: startScript(213)**. This establishes the in-dialogue caller of the independently decoded six-image-state animator.
- PCs **0x02B5,0x0321,0x0378,0x03DE,0x043A,0x04A0,0x0506,0x0567** contain eight distinct dynamically configured **verbOps** options. They adjust x position Var176, selected key Var177, and option text, with gate conditions on Bits561–566 and Var304. This is an **interactive choice graph**, not eight simultaneously rendered buttons guaranteed by static asset count.
- PCs 0x05C2–0x08DE select responses based on **Var175 values 120..127**, plus random state, and produce dialogue/actor speech events. Stored text has not been reproduced in research docs.
- **PC0x08E3: stopScript(213)**. This explicitly ends the concurrent object1098 animator.
- PCs0x08E5–0x08FB draw object1097 states2→1, yield between them, then set **all three imported objects1097/1098/1096 to state0**.
- PCs0x0902–0x0926 terminate the scene interaction: delay, reset local scenery states, restore Ego animation, set cursor/user input back on, stop.

### Subordinate LSCR213: source-driven object-image animation

It runs a source loop: inspect dialogue/speech state (Var3, Var25) and Local1, pick random values, compute a state index, issue **drawObject(1098, state=Local2)**, breakHere and jump back. The exact distribution of selected IM01..IM06 states is **not yet proved for actual runtime input variables**. It is nevertheless original source-coded image animation, not an inferred GIF.

Bank100 original paired object1098 has **6 IM states, size 32×24**. It also contains bank objects1096 (single state) and1097 (three states), all used by the script. Source Room97 itself stores separate paired scene objects such as 1048,1063,1066. Use room-qualified resource origin to draw the correct image.

### Parallel independent animation family in the same scene

Room97 LSCR208 starts local212 on one conditional branch; local212 explicitly sequences source **object1066 states 1→2→3→5→2→4→1→4→2→5→2→4→2** separated by 12 breakHere yields and terminates. This is **a different local source-image animation**, not object1098's imported six-state random loop. LSCR208 is fully aligned as shown above, but natural branch reachability has not been captured.

## P4/P6 implications

This is a single system spanning (a) **foreign source-room OBCD/OBIM import**, (b) three positioned FLOB image components, (c) a short image-step animation, (d) a **concurrent** random six-state loop with explicit start and stop, and (e) user-driven dialogue selection and actor animation. A static room exporter that only decodes local OBIMs will miss the visuals. A uniform GIF of all six states will not preserve the original timing, randomization or dialogue-gated start/stop.

**Next verification:** official descumm on tagged LSCR202/213/208/212; pinned ScummVM runtime entering the relevant Room97 logical alias with recorded mode, Bit561–566, Var175, Var176, Var177, Var304, Ego and actor9 state, FLOB 1096/1097/1098 source IDs, draw positions, exact palette/transparent indexed pixels; compare per-update front/back buffers. This report is static source evidence only.
