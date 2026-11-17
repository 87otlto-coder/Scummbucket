# MI2 Room55 — TALK_ACTOR driven animation dispatch and script202 callers (17 November 2026)

**Evidence class:** read-only original DOS VGA `MONKEY2.001` SHA-256 `ad045372e0d49626503bb50fca29a687ec8e01ef75d9b8bca702a366d143819e`, direct byte/offset inspection of Room55 LSCR[212] and LSCR[200], interpreted using pinned [ScummVM v2026.4.0 v5 opcode implementations](https://github.com/scummvm/scummvm/blob/v2026.4.0/engines/scumm/script_v5.cpp), [script variable table](https://github.com/scummvm/scummvm/blob/v2026.4.0/engines/scumm/vars.cpp), [script scheduling and indirect variables](https://github.com/scummvm/scummvm/blob/v2026.4.0/engines/scumm/script.cpp). **Source-aligned control-flow subregions only**; the full 590-byte LSCR212 has NOT been walked by an exhaustive decoder, and official descumm has NOT been run. No emulator execution, real rendered-pixel comparison or original game data committed.

## Discovery: the dispatcher selects animations based on the current speaking actor

Room55 **LSCR212** tagged chunk starts at decoded offset `0x497EA6` (decimal 4,816,550), with **590-byte bytecode body starting `0x497EAF`** (4,816,559). The first bytes are an exact SCUMM v5 machine-speed gate, followed by an **actor identity snapshot**:

- **PC 0x000**: `isEqual(Var[6],0)`, with the v5 reverse branch convention; **PC 0x007** `stopScript(0)` when the machine-speed variable is zero.
- **PC 0x009**: `9A 00 40 19 00` → `move Local[0] = Var[25]`. **This is a variable read, not the literal integer 25** because opcode `0x9A` sets parameter-variable flag bit 0x80; `0x4000` is the destination local variable.
- Pinned `vars.cpp::ScummEngine::setupScummVars` assigns **`VAR_TALK_ACTOR = 25`** in SCUMM v5. Consequently, `Local[0]` is a *snapshot of which actor is talking*.

### Aligned dispatcher landmarks

These PC positions are genuine **instruction boundaries in the inspected branch header**, determined by the 7-byte direct `isEqual(Local0,actorID)` opcode and its 16-bit relative branch:

| PC (hex) | Condition | Source dispatch consequence |
| --- | --- | --- |
| `0x00E` | Local0 == **7** | `startScript(201)` at 0x015; jump to common wait |
| `0x01B` | Local0 == **5** | Direct jump to common wait, no child start in this immediate arm |
| `0x025` | Local0 == **11** | `startScript(203)` at 0x02C |
| `0x032` | Local0 == **8** | Enter a longer, conditional animation branch, choosing among `startScript(202,[8])`, `startScript(202,[5])`, `startScript(202,[4])`; branch conditions depend on computed values and actor/object state |
| `0x0CF` | Local0 == **9** | `startScript(204)` at 0x0D6 |
| `0x0DC` | Local0 == **10** | `startScript(205)` at 0x0E3 |
| `0x0E9` | Local0 == **12** | `startScript(206)` at 0x0F0 |
| `0x0F6` | Local0 == **6** | `startScript(207)` at 0x0FD |

**Important qualifier:** Actor 8's inner `0x032–0x0CE` logic is a **variable/position-sensitive selector**, not yet a complete path proof. The direct `startScript(202)` bytecode calls are at `0x066` (argument8), `0x076` (argument5), `0x0A6` (argument4), `0x0B6` (argument5), `0x0C6` (argument8). The exact conditions leading to each call are pending full decoder/descumm confirmation.

### The missing mode source of LSCR202 is now recovered

The earlier [Room55 animation loops report](MI2_ROOM55_STATIC_EVENT_LOOPS_20261116.md) established that LSCR202's first argument `Local[0]` selects three internal object617 animations:

| Caller argument | Script202's earlier fully aligned behaviour |
| ---: | --- |
| **8** | random nonrepeating source object617 states **8–11** |
| **4** | random nonrepeating source states **4–7** |
| **5** | default mode; alternate object617 states **1 ↔ 3** |

These aren't 11 states combined into a simple universal loop. **The talking-actor-8 dispatch selects which facial/graphics mode becomes active.** The visual interpretation “facial” remains a *hypothesis* pending runtime and object image inspection, but the caller/parameter linkage is directly encoded.

### Source loop waits for dialogue actor to change

The source contains at approximately **PC 0x107–0x10F**:
- `0x107: breakHere`
- `0x108: isNotEqual(Var25, Local0)` followed by **relative -8**, i.e. the branch returns to **PC 0x107 when `Var25 == Local0`** (because v5 `jumpRelative` jumps on a *false* condition).
- When the **current TALK_ACTOR becomes different from the snapshot**, control flows onward into the cleanup block beginning **0x10F**.

This is not an autonomous infinite background loop: the controller has a source-coded **voice/speaker lifecycle**. The following cleanup section includes actor-ID branches, direct source-object redraws and `stopScript` calls including `stopScript(201)`, `stopScript(203)`, `stopScript(202)`, `stopScript(204)`, `stopScript(205)`, `stopScript(206)`, and `stopScript(207)` in the corresponding branches; these are script operations, not proof all children were running.

**Source call-chain status:** Room55 ENCD **fully aligned** `startScript(224)` and `startScript(200)`, Room55 LSCR200 has direct `2A D4 FF` at body `0x124` for `startScript(212)`, and LSCR212 contains the verified actor-variable header and direct child dispatch. LSCR200's full 302-byte source path remains to be independently boundary-walked; do not state an unconditional observed call execution.

## Implementation consequence / why this is worth keeping

This closes a major uncertainty in the earlier [Room55 caller graph](MI2_ROOM55_ENTRY_CALL_GRAPH_20261116.md): scripts201/203–207 are **potential speaker-reactive object animation loops**, not generic scenery loops that should all start on room entry. Script202's `Local0` options are supplied by its parent dispatcher, and actor8 has a further scene-sensitive choice.

For an accurate P4/character-animation event model, retain:
- `VAR_TALK_ACTOR` (Var25) at each script-start, yield and speaker change;
- snapshot `Local0`, current script slot/identity, start/stop of child local script;
- caller arguments to script202 (4,5,8);
- original source script and room ID (local script numbers are room-scoped);
- camera, object state, costume and current speech/message activity; and
- actual renderer/timer phases if captured later.

**Next source-only step:** finish a **full** bytecode walk of LSCR212's 590 bytes and LSCR200's 302 bytes; validate actor8's value/geometry-based mode selector; inspect LSCR213 and LSCR211 for independent scheduled object state changes; verify exact calls with an official pinned descumm output.

**Future runtime test:** turn talking actor 7/8/9/10/11/12/6 on/off in Room55 under pinned ScummVM, logging animation child, its selected state, stop point and indexed frame/mask. Do not call this pixel-verified until matching source and observed output exist.

No private copyrighted game input, decompressed sprites or sound was committed.
