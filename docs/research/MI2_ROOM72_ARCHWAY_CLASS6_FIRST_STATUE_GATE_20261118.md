# MI2 bone maze: archway class-6 routing and first required-statue gate — 18 November 2026

**Evidence class:** read-only original DOS VGA archive (`MONKEY2.001` SHA-256 `ad045372e0d49626503bb50fca29a687ec8e01ef75d9b8bca702a366d143819e`), independent complete narrow walk of original Room72 LSCR202, and direct aligned handler/entry spans from original Room71 OBCD and Room72 ENCD. Engine semantics crosschecked against pinned [ScummVM v2026.4.0 `script_v5.cpp`](https://github.com/scummvm/scummvm/blob/v2026.4.0/engines/scumm/script_v5.cpp) (especially `o5_ifClassOfIs`, `o5_setClass`, `o5_isLess`, `jumpRelative`) and [`object.cpp`](https://github.com/scummvm/scummvm/blob/v2026.4.0/engines/scumm/object.cpp) (`getClass/putClass` masks `0x7F`). **No descumm cross-validation, live playback, original DOS runtime verification or native-pixel comparison.**

## The central clarification: `ifClassOfIs(obj, 0x86)` REQUIRES class 6 present

Pinned ScummVM `getClass(obj, cls)` masks `cls &= 0x7F`, so `0x86` asks for **class6**. In `o5_ifClassOfIs` a class operand with high bit `0x80` is a **positive** class-presence test; without the high bit, it represents absence. Specifically:
- `setClass(obj, 0x86)` **sets class6**.
- `setClass(obj, 0x06)` **clears class6**.
- `ifClassOfIs(obj, 0x86)` **continues on class6 present** and executes its signed jump to the alternate branch **when class6 is absent**.

Failing to honor the reversed v5 `jumpRelative(bool cond)` convention would invert this entire maze and misclassify the first required-object guarantee.

## Exact Room72 LSCR202 routing

Original tagged Room72 `LSCR[202]` begins `0x5EC086`; bytecode body at **`0x5EC08F`**. Full independent source walk: **142/142 bytes, 23 instructions, 8 distinct jump targets (all aligned)**. The original script accepts `Local0` (the archway being used) and `Local1` (opposite archway/entry target).

| Script PC | Original condition/action | Consequence |
| ---: | --- | --- |
| `0x000–0x01F` | if `Var102==73`, **set** class6 on archway **731** or **clear** class6 on alternative archway by matching `Local0==731` | The room-arrival context can override previous arch markers before routing |
| `0x01F` | `ifClassOfIs(Local0, 0x86)`; conditional jump on false to **PC0x04E** | **class6 present** follows return/retain path; **absent** follows new-step path |
| `0x028` | `Var456=1` | Mark preserve-layout route |
| `0x02D–0x04B` | if `Var102==71` load **physical Room71** (obj721); if `Var102==73` load **physical Room73** (obj749) | Return to prior physical side when context matches |
| `0x04E` | `Var456=0` | Mark new-layout route |
| `0x053` | **increment Var457** | Advance maze progress |
| `0x056–0x065` | if progress **exceeds 9**, request Room71; otherwise continue | Conditional limit/exit; live scheduler semantics not captured |
| `0x065–0x073` | **clear** class6 on `Local0`; **set** class6 on `Local1` | The opposite arch is designated as the marked route for the next room instance |
| `0x073–0x08D` | `loadRoomWithEgo(Local1, logical132, X=60 or264,Y=107)` depending on `Local1==731` | Visit same physical Room72 resource through pseudo-room132 |

**Precise guard:** the v5 `isLess(Var457, 9)` test jumps forward when progress is **at most 9**, so the explicit Room71 request executes when it becomes **10 or greater**. Previous notes calling the exit threshold merely `9` should retain the correct inequality.

### Room71 archway setup and difficulty dependence

Original Room71 `OBCD/VERB` handlers for two `back tunnel` objects are **source-aligned**:

- **Object720**, source VERB `0x5D81AF`, handler verb11 at tagged offset12: in **Regular Mode** (`Bit567=0`) execute `setClass(731,0x86)`, then `loadRoomWithEgo(731,logical130,x36,y107)`; in **Easy Mode** skip the setClass and request the same pseudo-room.
- **Object721**, source VERB `0x5D820C`, handler verb11 at tagged offset12: in Regular Mode execute `setClass(732,0x86)`, then `loadRoomWithEgo(732,logical132,x285,y107)`; in Easy Mode skip the class set and request the same pseudo-room.
- **Object730** original `tunnel` also has a separate default verb255 handler requesting `loadRoomWithEgo(731,logical131,x36,y107)`. The exact natural player selection and object touchability of all three entrances remain to be captured.

These handlers do **not** guarantee initial class6 state of every arch in every save; other scripts may mutate class flags. They do show source-authored Regular/Easy differences.

### Two archway handlers in Room72 call the same transition script

Both original Room72 archway `OBCD` names are **`archway`**, IDs **731** and **732**. The relevant source-local calls in their verb11 handlers use **`startScript(202,[731,732])`** and **`startScript(202,[732,731])`**, respectively, under state-dependent branches (logical room 132 and difficulty/other checks). The two arguments therefore map exactly to current versus opposite arch for the class6 transition above.

**Architectural distinction:** `Local0/Local1` are **object IDs**, not visual image-state numbers; class6 changes a gameplay marker, while object drawing is performed separately by Room72 LSCR200. Class6's exact rendered affordance is unverified.

## Why the first required puzzle statue is conditionally guaranteed, not universally

Original Room71 ENCD, `0x5D8435`, resets **Var457=0** and **Var459=0** in **Regular Mode** (Bit567 clear); the Easy branch skips reset. During a source path that enters a preliminary arch scene with `Var457=0`, a **class6-absent** arch selection executes Room72 LSCR202's **Var457++** (to1), sets **Var456=0**, and requests logical room132.

Room72 ENCD begins with the exact conditional:
- if `Var102 !=132`, run **LSCR201** procedural initializer;
- if `Var102==132` **and Var456==0**, **also** run LSCR201;
- if `Var102==132` and `Var456!=0`, skip the initializer (retain previous layout).

As soon as LSCR201 runs in the newly requested room132 **with Var457==1 and Bit365==0**, its already independently source-aligned target-injection block searches objects741–748 for String46's next three-letter token and **inserts the matching ID into the currently selected one/two/three statue slots if missing**. See [target-injection proof](MI2_ROOM72_GUARANTEED_NEXT_STATUE_LAYOUT_20261117.md) and [eight seed paths](MI2_ROOM72_BONE_STATUE_EIGHT_PATHS_20261117.md).

**Therefore:** there is a concrete **source-consistent first-progress path** from a Regular-mode reset to the *first required statue being guaranteed among displayed choices*: reset `Var457=0` → take a class6-absent arch → `Var457=1,Var456=0` → enter logical132 → LSCR201 injects next required statue. This closes the earlier uncertainty about why the correction guard is `Var457==1` rather than zero.

**Important limits:** It does **not** prove every possible first visual layout has the target; the preliminary `Var457==0` scene itself lacks the injection block. It also does **not** prove every player path enters the progress route or that `Bit365` is clear and String46 initialized in all saves. Other global game-state writers, actor room-changing script cancellation, original DOS interpreter behaviour and native visible image state remain untested. Do not elevate a conditional source route to a guaranteed universal gameplay invariant without actual runtime traces.

## Next validation gates

1. Official `descumm -5 -o` comparison for original Room71 ENCD, Room71 objects720/721, Room72 ENCD, Room72 object731/732 verb11, LSCR201 and **LSCR202**.
2. Capture Regular/Easy initial Room71 tunnel interactions. Log `Bit567,Bit365,Var102,Var456,Var457,Var459`, classes6 of 731/732, logical room vs physical72, LSCR201/202 call stack and object selections.
3. In Regular source path from `Var457=0`, intentionally choose a class6-absent arch; confirm the next generated scene includes the first correct statue and the source runtime counters actually reach progress1 in intended order.
4. Compare indexed Room72 SMAP/OBIM and dynamic layouts for before/after injection; keep source provenance, RNG selections and native pixel hashes. No original archives in Git.

**Status:** read-only source-evidence and pinned engine semantics only; no full original- or ScummVM-runtime acceptance.
