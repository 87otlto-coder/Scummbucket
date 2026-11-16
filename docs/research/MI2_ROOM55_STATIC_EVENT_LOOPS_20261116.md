# P4 MI2 Room 55 — instruction-aligned script-animation spelunking (2026-11-16)

**Research-only; no ScummVM runtime capture, no debugger, no gameplay verification, no Windows test.** This is an independent, narrowly scoped static bytecode walk against the original DOS VGA archive, with opcode and branch semantics checked against ScummVM v2026.4.0 `script_v5.cpp` and variable bindings against `vars.cpp`. The walker covers only the specific instructions needed for the selected scripts; it is **not** a general SCUMM v5 disassembler. Disassembly alignment is source-code-backed but has **not yet been independently confirmed with descumm**. Do not label any of the schedules *observed animation*.

Input members in private `mi2.zip`:
- `MONKEY2.000` SHA-256 `cde7aa8980317e3a750fbb3b49884cdddaf1ff3d4231a0c840b22cceed9033f1`
- `MONKEY2.001` SHA-256 `ad045372e0d49626503bb50fca29a687ec8e01ef75d9b8bca702a366d143819e`.
- ROOM 55 source offset in decoded MONKEY2.001: `ROOM` under LOFF, scripts `LSCR` 200–207, 209 and 211–224. No global `SCRP` resource is stored in the room bundle; this does not exclude calls from elsewhere.

## Main finding: eight self-contained state-scheduling loops

Narrow walker consumed **every opcode byte** of the selected script bodies with no trailing data: scripts 201 (74/74), 202 (149/149), 203 (74/74), 204 (74/74), 205 (74/74), 206 (74/74), 207 (92/92), 209 (74/74). It handled opcode signatures `isEqual`, `isNotEqual`, `move`, `stopScript`, `drawObject`, `expression` with nested `getRandomNr`, `breakHere`, `jumpRelative`, `stopObjectCode`, `equalZero`, `increment`, `isLess`; verified all PC-relative jump targets land on decoded opcode boundaries.

ScummVM v5's `jumpRelative(bool cond)` consumes an **int16 signed relative offset** and takes the jump only if `cond` is FALSE; this is essential to interpreting the conditional source bytes. `getRandomNr(max)` is inclusive 0..max. `vars.cpp` maps v5 global variable index **6** to **VAR_MACHINE_SPEED**.

### Shared structure of scripts 201 and 203–207

- First instruction at body offset 0x0000 tests global `Var[6] == 0`. If true, falls through to `stopScript(0)`; otherwise skips stop and initializes its graphics loop. This is a **machine-speed-dependent gate** in the bytecode, not an inferred visibility condition.
- Initialize one global variable (163 for 201, 165 for 203, 167 for 204, 168 for 205, 169 for 206, 170 for 207), then draw two paired objects in state 1.
- An expression computes a local value `r = getRandomNr(N) + 2` into local `0x4001`. A conditional jump back to the expression rejects consecutive duplicate **raw** `r` values compared against prior local `0x4000`; accepted `r` becomes the new previous value.
- If `r == 2`, the displayed state is remapped to 1; otherwise the displayed state is `r`.
- Draw the variable-selected state for one of the pair, issue `breakHere()` (script yield), and jump back to the expression. The loop has **no archive-defined wall-clock FPS**.
- Script 207 additionally conditionally redraws image-bearing object 638, testing a bit-variable reference `0x80D2` before and after its core random-state loop; its runtime bit value is not established.

| LSCR | Source chunk offset | Body bytes aligned | Paired objects initially state 1 | Object selected in loop | Random max N | Possible loop display states, by bytecode | Stored image count for loop object |
| ---: | ---: | ---: | --- | ---: | ---: | --- | ---: |
| 201 | 4,815,403 | 74/74 | 621 and 620 | 620 | 2 | 1,3,4 | 5 |
| 203 | 4,815,644 | 74/74 | 624 and 623 | 623 | 2 | 1,3,4 | 4 |
| 204 | 4,815,727 | 74/74 | 628 and 627 | 627 | 5 | 1,3,4,5,6,7 | 7 |
| 205 | 4,815,810 | 74/74 | 631 and 630 | 630 | 5 | 1,3,4,5,6,7 | 7 |
| 206 | 4,815,893 | 74/74 | 633 and 634 | 634 | 2 | 1,3,4 | 4 |
| 207 | 4,815,976 | 92/92 | 637 and 636 | 636 | 2 | 1,3,4 | 4 |

**Subtlety:** `getRandomNr(N)` is called until it yields a raw value different from the last accepted raw value. Therefore *random draw attempts* may be arbitrarily many within one script update even though each **accepted** visible-state selection is followed by one yield. Do not turn the raw 164 object-operation patterns in the broader survey into 164 independent animation frames.

### LSCR 202 — three modes of one 11-state object

Chunk begins at source offset **4,815,486**, body consumes **149/149** bytes.

Startup checks `VAR_MACHINE_SPEED`, draws objects 618 and 617 at state 1, then selects one of three mutually exclusive branches according to initial `localVar[0]`:

1. `localVar[0] == 8`: nonrepeating random raw selection `getRandomNr(3) + 8`, so displayed object 617 states **8–11**. One `breakHere` per accepted state.
2. Otherwise `localVar[0] == 4`: nonrepeating random `getRandomNr(3) + 4`, so states **4–7**, also yielding once per accepted state.
3. Otherwise: alternates object 617 state **1**, yield, then state **3**, yield, repeating.

Each branch loops in the bytecode; no actual invocation, mode values or wall-clock cadence have been recorded. Object 617 has 11 stored images.

### LSCR 209 — randomized dwell intervals

Chunk starts source offset **4,816,077**; bytecode body consumes **74/74** bytes.

Object **615**, with precisely **two** stored image states, alternates state 1 and state 2. For each:
- `d = getRandomNr(5) + 5`, giving an integer **5–10 inclusive**.
- Set `localVar[1] = 1`, execute `breakHere()`, increment the counter and loop until it exceeds the sampled `d`.
- Consequently each of the two states persists for **d script yields** (subject to scheduler interruption/stop/overrides), then changes.
- At bytecode body offset **0x0046** a signed jump targets body **0x0000**, creating the alternating loop.

This is a strong candidate for a **script-controlled, variable-duration two-state scene effect**. It does *not* establish the real duration of a yield in rendered frames or milliseconds, or proof that the script runs in game.

## Verified relative control-flow landmarks (script-body offsets)

- 201/203/204/205/206: raw choice expression at **0x001A**; unequal conditional from **0x0027** jumps to 0x001A when raw value repeats; variable draw at **0x003F**; script yield at **0x0045**; jump at **0x0046** targets 0x001A; halt opcode at 0x0049 (normally unreachable in uninterrupted execution).
- 207: choice expression at **0x0023**; reject repeat at 0x0030→0x0023; variable draw at 0x0048; script yield at 0x0057; jump 0x0058→0x0023. The conditional object 638 draws occur at 0x001F and 0x0053, if the bit-var test permits them.
- 202: mode-8 branch at **0x0026**, mode-4 at **0x0058**, alternating branch at **0x0083**. Alternative 1/3 draws at **0x0083** and **0x008A**, script yields 0x0089 and 0x0090.
- 209: first state draw at **0x0000**, choice of dwell d at 0x0006, yield at **0x0018**; state-2 draw at **0x0023**, dwell choice at 0x0029, yield at **0x003B**; loop returns 0x0046→0x0000.

## Why this advances ScummBucket

This room demonstrates that **animation timing may be encoded in script control flow and random-number choices, not just frame resources or CYCL metadata**. The best intermediate output is a conditional event/state-machine specification with random seeds/choices, yielded ticks, object IDs and explicit uncertainty. An arbitrary fixed-FPS GIF of IMxx states would be inaccurate.

### Follow-up gates (not performed)

- Use real `descumm` to independently check all 8 script instruction boundaries and exact output semantics.
- Trace callers for local scripts 201–209, the meaning of localVar[0] at call sites, lifecycle/stop conditions and whether machine-speed gate is enabled under the target original DOS startup.
- Decode the selected object images (including object 638) at native palette indices. Independently verify transparency, object positions, and masks.
- Record script yields/renderer refresh timestamps, random states, object-state calls and indexed front buffer from an instrumented **non-enhanced** ScummVM run, preserving the engine phase. Distinguish source-supported logical transitions from observed frames.
- Add an offline unit-testable conditional event interpreter only *after* establishing the runtime scheduling contract.

### Source references

- `https://github.com/scummvm/scummvm/blob/v2026.4.0/engines/scumm/script_v5.cpp` — `o5_isEqual`, `o5_isNotEqual`, `jumpRelative`, `o5_expression`, `o5_drawObject`, `o5_getRandomNr`, `o5_breakHere`.
- `https://github.com/scummvm/scummvm/blob/v2026.4.0/engines/scumm/vars.cpp` — `ScummEngine::setupScummVars`.
- This note updates the raw-only classification in `MI2_SPELUNK_STRUCTURE_20261116.md` without altering its source-byte candidate counts.
