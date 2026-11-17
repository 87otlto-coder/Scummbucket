# MI2 logical rooms 130–132 / physical Room72: procedural layout initializer, 48-slot exchange and string-conditioned puzzle state (2026-11-17)

**Evidence:** original DOS VGA `MONKEY2.000/.001` inspected without modification; `MONKEY2.001` stored SHA-256 `ad045372e0d49626503bb50fca29a687ec8e01ef75d9b8bca702a366d143819e`. Independent private v5 narrow walker checked against pinned ScummVM [script_v5.cpp](https://github.com/scummvm/scummvm/blob/v2026.4.0/engines/scumm/script_v5.cpp), [script.cpp](https://github.com/scummvm/scummvm/blob/v2026.4.0/engines/scumm/script.cpp) including indirect array operands, `o5_stringOps` and branch polarity. **No original DOS/ScummVM gameplay, official descumm comparison, rendered scene or pixel parity.** Do not commit original game bytes or art.

## Context: three logical instances, one physical resource

Original `SCRP[1]` stores a well-formed `o5_pseudoRoom` instruction mapping **logical room IDs 130,131,132 to physical resource72**, among 24 alias IDs across five shared resources (see [pseudo-room inventory](MI2_PSEUDOROOMS_ROOM93_SCENE_INSTANCES_20261117.md)). The source RMIM/OBIM decode covers physical resource72; the current logical `Var4` controls distinct layouts and transitions.

Prior [Room72 dynamic object script200](MI2_ROOM72_DYNAMIC_OBJECT_LAYOUT_20261116.md) already fully decoded **487 bytes / 74 instructions**, including variable-indexed image state and draw placement. This report adds its **upstream initializer and downstream interaction** rather than redoing that work.

## Full independent opcode walk

| Original script | Body absolute offset | Body bytes consumed | Instructions | Relative target verification |
| --- | --- | ---: | ---: | --- |
| Room72 `ENCD` | `0x5EB??` (see tagged source for precise offset) | **195/195** | **40** | **7/7** valid |
| Room72 `LSCR201` | `0x5EBD3E` | **840/840** | **130** | **57/57** valid |
| Room72 `LSCR202` | `0x5EC08F` | **142/142** | **23** | **10/10** valid |
| Room72 `LSCR203` | `0x5EC126` | **9/9** | **4** | zero branches |

The ENCD row offset is intentionally omitted until a source-index read cross-check; full body length and alignment are independently established. **No independent official descumm run has been claimed.**

## LSCR201: fixed vs randomized layouts, with correct nested variable decoding

Source:
- If `Var4=130` or `Var4=131`: set count/control variables `Var356,357=1`, `Var358,359,360,366=0`, `Var370=3` and `Var371[1..3] = 741,742,743`.
- If `Var4=132` and `Var102=71`: use the same fixed three-object setup (the source has its own `Var4==132` / `Var102==71` branch).
- Otherwise when `Var4=132`, generate a parameterized layout from `getRandomNr` calls:
  - `Var356 = 1..4`, `Var357=Var356`; conditional `Var358` and `Var359` random **1..3** when their branches run;
  - `Var360 = 0..4` and the indicated subset of `Var361[]` uses **IDs735..738**;
  - `Var366=0..2`, and subset of `Var367[]` uses **IDs739/740**;
  - `Var370=1..3`, and `Var371[1..Var370]` uses IDs **741..748**, with explicit rejection/retry to avoid duplicate selected IDs in this last group.

**Variable-addressing correctness:** With SCUMM v5's `0x2000` indirect flag, a trailing index operand that *also* has 0x2000 is **a variable reference whose value supplies an index**. Thus `Var[371+Var[100]]` is correct for the randomized object-selection/entry branch. A naïve parser printing this trailing word as `Var[8292]` is **wrong**; `0x2064` means *indirection through Var100*. By contrast a trailing word without 0x2000 is an immediate index (e.g. `Var371[1]`). The parser was corrected before taking the completed walk; this is a material source-decoder lesson.

### Conditional string-resource comparison

From LSCR201 body PC`0x0262` onward, when **`Var457==1` and `Bit365==0`**, the script iterates logical object IDs beginning with **741**, runs their `VERB19` object script (source), then uses `o5_stringOps` to read **three successive characters from `rtString[46]`** beginning at index `Var459`. The three values are compared to **`Var375`, `Var377`, `Var376`** in that order.

Upon a matching three-character sequence, a branch uses `Var370` (active object count) to place the selected matching ID into an appropriate `Var371[]` slot, subject to non-duplication checks; nonmatching candidates increment the examined ID and retry. This is a **puzzle/state-specific source-derived arrangement**, not indiscriminate environmental motion. The original string resource contents and natural puzzle state have **not** been executed or separately interpreted; do not ascribe a specific game solution or rendered meaning.

## ENCD: object choice, one-yield animation, table exchange

Room72 ENCD (195 bytes, 40 aligned instructions) can conditionally launch **local201**, depending on logical room/Var102/Var456. It always then calls **local200**, which applies the selected object-image layout before the remainder of entry logic.

It then reads Ego actor room. If Ego is in room **0**:
- Choose one object from `Var[371+1..Var370]` through an inclusive random index into `Var100` (the expression computes `getRandomNr(Var370-1)+1`).
- Put Ego into logical room **132** at that object's location.
- `drawObject(selected_id, state2)`; start local203 with that exact object ID.
- Swap **48 pairs** `Var[356+i] ↔ Var[406+i]` for `i=0..47` using a temporary Var100.
- Run a brief cutscene: set Ego costume81, actor action7, **five explicit `breakHere` yields**, restore costume1, end cutscene.

If Ego was **not** in room0, the same **48 pairwise variable swaps** still run, but the short costume-change sequence is skipped. Thus the swap isn't optional merely because the actor is already present.

Room72 local203 is a **nine-byte, four-instruction** transient object animation: **two `breakHere` yields, then draw the supplied object in state1**, stop. This establishes why the state2 selection is not necessarily permanent once its child script has resumed.

## LSCR202: selected-object interaction can leave the logical scene

Original **142-byte** Room72 local202 has complete 23-instruction alignment and 10 valid branch targets. It changes the selected object's class based on `Var102` / object ID, updates `Var456` and `Var457`, and conditionally issues `loadRoomWithEgo` into:
- **physical Room71** at (160,127),
- **physical Room73** at (145,120),
- or **logical Room132** via a selected object and target positions (60,107) or (264,107).

This demonstrates interaction-conditioned travel and object class state, in addition to image compositing.

## Impact and evidence discipline

The archive holds one physical resource72 background and 18 objects, but the actual scene layout is **a function of logical room alias, previous room, puzzle bits, random choices, variable arrays, selected object and actor state**. A parser that copies OBIMs at their original CDHD offsets or simply concatenates stored IMxx states cannot fully reconstruct this mechanism. The native pose, transparency and room source-art pixels still require independent per-frame validation.

**Next gate:** official `descumm -5 -o` on LSCR201/200/202/203 and ENCD, then instrumented ScummVM captures with seeded RNG and direct variable logs `Var102,356..405,406..453,456,457,459,370..374, Bit365`, as well as selected object, class, image-state, logical Room130–132, physical Room72 and actor positions. Keep all original game inputs and captured frames private under FIXTURE.

**Status:** fully source-aligned code and pinned engine semantics, not real-game rendering fidelity.
