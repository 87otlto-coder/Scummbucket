# MI2 Room39 — source-aligned five-brick selection and difficulty bypass (17 November 2026)

**Evidence:** read-only original DOS VGA `MONKEY2.001` (SHA-256 `ad045372e0d49626503bb50fca29a687ec8e01ef75d9b8bca702a366d143819e`). Original `OBCD/OBNA` object names, indexed `SCRP[159]` (fully walked in [Room38/39 telescope report](MI2_ROOMS38_39_TELESCOPE_GLOBAL159_20261117.md)), and **Room39 LSCR203** have been cross-referenced with pinned ScummVM v2026.4.0 v5 opcode handlers: [script_v5.cpp](https://github.com/scummvm/scummvm/blob/v2026.4.0/engines/scumm/script_v5.cpp) (`o5_isEqual`, `o5_move`, `o5_notEqualZero`, `o5_animateActor`, `o5_setState`, `o5_startScript`). **No game runtime, independent official descumm, or pixel validation.** No copyrighted original resources committed.

## Five values in global159 are *brick object IDs*, not arbitrary frame labels

`SCRP[159]` conditionally initializes `Var[251] = getRandomNr(4)+392` when Var251 is zero. The inclusive random range yields **392,393,394,395,396**. All five are concrete **Room39 OBCD IDs** whose original `OBNA` source string is “brick”. They are logical objects (no stored OBIM image states). This gives the persistent random value a **meaningful object-reference interpretation**, rather than a generic five-choice visual variation.

In global159's Room39 branch, the corresponding five values draw image states **1–5**, respectively, on all three source-image objects **416,417,418** (each five stored states), and then set one of single-state objects **411,412,413,414,415**. The exact world-screen picture associated with each case remains unverified.

This is a *reusable graphics/puzzle linkage*: store selected **logical object ID**, associated overlay image triplet state, and any clue/reveal flags as separate fields. Do not persist only “animation frame 1 of 5.”

## Room39 LSCR203 — complete control-flow evidence

- Tagged `LSCR[203]` source body begins at `0x2F4A78`, length **145 bytes**.
- Private narrowly implemented v5 instruction walker consumed **145/145 bytes**, **34 instructions**, all **17 relative branches** landed on boundaries; source bytecode is independently aligned to the extent supported by this walk.
- Four principal outcomes and the essential instruction PCs:

| PC | Source-coded action | Meaning |
| --- | --- | --- |
| `0x000` | `notEqualZero(Bit567)`, else jump to 0x012 | Difficulty split: Bit567 is the Regular/Easy selection flag |
| `0x005` | `Local[0] = Var[251]` | **Easy-mode route** copies the cached brick target |
| `0x00A` | `Bit[755] = 1` | Easy mode sets an additional state prerequisite |
| `0x00F` | jump to 0x065 | Easy mode bypasses local 0x012–0x061 brick-based animation decisions |
| `0x012–0x061` | inspect `Local[0]` as a concrete ID392..396, choose Ego costume animation action 10/17/12, default action10 | Regular-mode branch varies actor gesture by which brick is selected |
| `0x061` | `delay(30)` | One script-time delay; not 30 display frames |
| `0x065` | Ego animate3, `setState(388,1)`, animate250, `delay(45)` | Object388's original name is **“trap door”**; rendered effect unobserved |
| `0x075` | compare `Local[0] == Var251` | Exact brick ID match test (SCUMM v5 opcode `0xC8` uses variable RHS) |
| `0x07C` | if `Bit755 != 0`, start global script44; else start global43 | Correct target **plus** prerequisite selects a distinct branch |
| `0x08D` | start global script43 | Incorrect brick selects the other branch |
| `0x090` | script termination | Both paths terminate |

**Do not overstate:** Calling script44 for the source-coded match/precondition is stronger than ordinary source-pattern scanning, but its complete scripted consequence and visible animation need separate inspection. A particular gameplay entry to LSCR203 is not runtime-confirmed.

### Prerequisite bit source

Global script159 writes **`Bit755=1`** in each of its five conditional Room39 overlay branches when the source conditions for the mirror/shutter sequence and chosen Var251 value are met. This creates an explicit source-coded dependency between prior telescope/statue cutscene and subsequent brick selection. Room39 LSCR203 has a separate, direct **Easy-mode bypass** that sets the same bit without executing its own brick-choice gesture branch.

**Careful interpretation:** Bit755 is a *state prerequisite* in this known code path; do not claim its complete puzzle meaning, permanence, or all writers have been exhaustively decoded until current-room and global script evidence is reviewed. The source script can reuse Var251 only if initialized by a prior script; actual startup/cutscene control remains unobserved.

## Follow-on evidence gates

1. Confirm official `descumm` of tagged Room39 LSCR203 vs 145-byte aligned walk.
2. Track the callers of local203, and inspect full global43/44 effects before labeling outcomes.
3. Capture Regular mode with deliberate incorrect/correct brick, Bit755 unset/set, Var251 known, and separately Easy mode. Record script PC, object388/411–418, actor animation, palette, room and native indexed pixels.
4. Compare trigger paths from telescope-on-statue global159 with the brick interaction. Exports should label *hypothesized* transitions until gameplay verifies them.
5. No original resource or game artwork in Git; all real screenshots/data captured under FIXTURE.

**Bottom line:** This is a five-way, cached random **puzzle target** which controls a three-image-state visual and downstream interaction. Source control flow is aligned; runtime and pixel fidelity remain unverified.
