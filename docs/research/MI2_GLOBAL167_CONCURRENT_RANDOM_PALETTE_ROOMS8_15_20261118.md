# MI2 global167 — concurrent randomized RGB palette scripts in Rooms8 and15 (18 November 2026)

**Evidence class:** read-only original DOS VGA MONKEY2.000/.001, original MONKEY2.001 SHA256 `ad045372e0d49626503bb50fca29a687ec8e01ef75d9b8bca702a366d143819e`; fully aligned v5 original global SCRP167 and Room15 ENCD, aligned leading Room8 ENCD call span. Semantics checked against pinned [ScummVM v2026.4.0 script_v5.cpp](https://github.com/scummvm/scummvm/blob/v2026.4.0/engines/scumm/script_v5.cpp) (o5_expression, o5_getRandomNr, o5_startScript, o5_roomOps), [script.cpp](https://github.com/scummvm/scummvm/blob/v2026.4.0/engines/scumm/script.cpp) (runScript recursive vs nonrecursive, stopScript slot iteration), [palette.cpp](https://github.com/scummvm/scummvm/blob/v2026.4.0/engines/scumm/palette.cpp) (darkenPalette). **No official descumm comparison, original DOS runtime, instrumented ScummVM, RGB palette capture or pixel accuracy.** No original game bytes/captures committed.

## Fully verified global167 source: a reusable seeded-amplitude random palette intensity loop

Global SCRP[167] is stored in an indexed physical room bundle (original script body at decoded .001 offset **0x5A3A84**). The script is **60/60 bytes, eight instructions, two valid relative jumps**, fully consumed by a narrow v5 operand-aware walker.

| Body PC | Decoded source operation |
| ---: | --- |
| 0x000 | If Var49=VAR_VIDEOMODE !=19 (VGA), jump to stop at PC0x03B |
| 0x007 | Compute Local5=255−trunc(Local0/2) via v5 expression |
| 0x016 | Compute Local4=trunc(Local0/4); **Local4 is not consumed by any later opcode in this 60-byte script** |
| 0x021 | Compute Local3 = getRandomNr(Local0) + Local5, with original inclusive random maximum |
| **0x02F** | **roomOps(SO_ROOM_INTENSITY, Local3, Local1, Local2)** — RGB scale over caller-provided inclusive palette range |
| 0x037 | breakHere: yield to script scheduler |
| 0x038 | Unconditional relative jump to **PC0x021**; resample forever until stopped |
| 0x03B | stopObjectCode |

Hence `scale = 255−trunc(A/2)+randomInteger(0..A)` for caller amplitude **A=Local0**. The script contains no raw frame assets, palette-cycle resource references, explicit timer delay or RGB keyframes. Each loop resamples brightness, scales room-base RGB in the caller-supplied range and yields. The actual number of rendered update frames between changes depends on script scheduler phase and whether a sample maps to the same RGB values as its predecessor.

## Original literal callers, source arguments and exact opcode flags

| Room | Original source call | Encoded opcode | Arguments [amplitude,startIndex,endIndex] | Source-predicted raw scale |
| ---: | --- | --- | --- | --- |
| **8** cartographer's room | ENCD PC0x000 (absolute `0x972EC`) | **0x6A** | **[30,148,156]** | **240..270** |
| **8** same room | ENCD PC0x00C (absolute `0x972F8`) | **0x6A** | **[20,169,179]** | **245..265** |
| **15** woodsmith room | ENCD PC0x000 (absolute `0x136DE5`) | **0x6A** | **[20,75,95]** | **245..265** |

Source object names corroborate room context: Room8 contains map, cartographer, monocle and pile of paper objects; Room15 contains woodsmith, workbench, wood polish, fish plaque and peg-leg objects. This identification is source-name-backed, not a claim about exact rendered artwork.

Room15 ENCD is **68/68 bytes, 13 fully aligned instructions, two valid branches**. Room8 ENCD's **first 24 bytes** encode the two complete, valid v5 startScript call operations above, but its later bytecode was not entirely consumed by the private narrow walker; do **not** declare whole Room8 ENCD independently decoded.

### Critical source scheduling discovery: recursive starts *permit both Room8 scripts to remain alive*

Pinned `o5_startScript` calls `runScript(script, (opcode&0x20)!=0, (opcode&0x40)!=0, args)`. Room8 and15 original opcode **0x6A** has bit **0x40 set**, so **recursive=true**. In pinned `ScummEngine::runScript` the existing same-ID script is stopped only when **recursive==false**:

- **Room8 first start** launches global167 for palette **148..156** and runs nested until the first `breakHere`.
- **Room8 second start** launches **another independent global167 instance** for palette **169..179**; because recursive=true, the first is **not canceled** and both have independent script slots and locals.
- **Room15** launches one recursive global167 instance for palette **75..95**. Other instances could coexist if still active, although original room transitions or explicit stops may clear them; do not claim an arbitrary persistent cross-room overlap without a trace.
- **Global7**, source body `0x37B2B`, includes **stopScript(167)** at PC0x028. Pinned `stopScript` iterates every running script slot of that ID, so this single command is capable of stopping **all concurrently active global167 instances**. See [global7 load-related light cleanup](MI2_GLOBAL7_LOAD_RESET_SCRIPT49_54_20261118.md).

This **contrasts with** Room9 global70's ordinary immediate **0x2A startScript(54,[actor6])** and Room21 local208's 0x2A startScript49: **those nonrecursive calls replace their previous same-ID script instance**. A reconstruction engine cannot model all starts with one blanket singleton policy. Preserve **recursive and freeze-resistant opcode flags**.

### Not CYCL, and not a 20/30-frame animation

Both original Room8 and Room15 CYCL chunks contain **10 bytes total** (8-byte header + two zero payload bytes), i.e. **no palette-cycle records**. RGB intensity commands instead dynamically modify 148–156,169–179,75–95. The indices cover separate source palette slices and potentially affect RMIM, OBIM or costume pixels using those indices; actual coverage and RGB visibility need native source asset inspection.

ScummVM v5 `darkenPalette` scales the current room's **base CLUT** (not the last modified RGB) by `scale/255`, caps resulting components at252 and flags the changed palette range dirty. The raw scale may exceed255 (e.g.270), and that is **not equivalent to preclamping brightness to255**. A random draw of the same scale twice or a saturated RGB base can yield zero visible change, even though a source palette operation occurred.

## P4 implications and next verification

1. New named mechanism **CONCURRENT_SCRIPTED_RANDOM_RGB_INTENSITY**: multiple independent script slots with identical global script ID, separate Local0–Local5 state and disjoint RGB ranges; no CYCL or stored image-frame sequence.
2. Event IR must retain `startScript opcode 0x6A vs 0x2A`, recursive flag, parent invocation PC, script slot ID, source arguments, original resource room, current logical/physical room, VGA guard and exact palette writes.
3. Capture real Room8 entry in VGA; verify **two global167 slots** present simultaneously, sampled scales, scene palette RGB148–156 and169–179 updated on independent scheduler phases, and original indexed pixels/masks. Capture Room15 range75–95 and exit/load behavior including global7 if actually invoked.
4. Compare with official pinned descumm, then with original ScummVM non-enhanced runtime captures. Do not call any visual animation faithful until actual indexed+RGB parity is achieved.

**Result: source-proven original concurrent randomized RGB scripts with clear caller flags, no runtime/pixel verification.**
