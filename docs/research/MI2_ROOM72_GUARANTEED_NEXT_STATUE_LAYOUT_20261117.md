# MI2 Room72 — source-proven conditional guarantee of the next required statue (17 November 2026)

**Evidence:** read-only original DOS VGA `MONKEY2.000/.001`, private upload `mi2.zip`; original `MONKEY2.001` SHA-256 `ad045372e0d49626503bb50fca29a687ec8e01ef75d9b8bca702a366d143819e`. This note independently traces a **bounded, bytecode-aligned subgraph** inside Room72's already fully instruction-walked `LSCR201` (840 bytes) and crosschecks variable operands and reversed conditional jumps against pinned [ScummVM v2026.4.0 script_v5.cpp](https://github.com/scummvm/scummvm/blob/v2026.4.0/engines/scumm/script_v5.cpp) (`o5_startObject`, `o5_isEqual`, `o5_isNotEqual`, `o5_expression`, `jumpRelative`) and [script.cpp](https://github.com/scummvm/scummvm/blob/v2026.4.0/engines/scumm/script.cpp) (`0x2000` indexed vars). **No official descumm corroboration, gameplay or pixel testing.** No original image, script bytes, sound or puzzle dialogue copied to Git.

## Key discovery: randomized layout is explicitly amended to include the next correct statue

[Eight authored routes in global88](MI2_ROOM72_BONE_STATUE_EIGHT_PATHS_20261117.md) derive from eight alternative values assigned to String resource46, with four consecutive three-letter statue codes each. Each Room72 bone-statue object **741–748** has a unique three-letter code implemented by its verb19 writer to Var375,Var377,Var376. Room72 `LSCR205` compares those three codes to String46[Var459..Var459+2]; a correct match advances Var459 by three and marks progress through Var457.

**Missing link now identified:** Room72 `LSCR201` **corrects its own random layout** to ensure the next required object ID is among the selected statues whenever **`Var457 == 1` and `Bit365 == 0`** (and the script201 initializer is actually invoked). This is not speculative game-design interpretation; the source contains an exact candidate-search loop and state-array replacement code.

### Control-flow slice, Room72 LSCR201 body PCs

| Source PC | Decoded v5 meaning |
| ---: | --- |
| **0x262** | `isEqual(Var457, 1)` — if false, jump directly to termination at about PC0x344 |
| **0x269** | `equalZero(Bit365)` — if false (Bit365 set), also skip the correction block |
| **0x26E** | `Local1=741` — begin an explicit object-ID search |
| **0x273** | `startObject(Local1, verb19)` — query this object's embedded three-symbol state writer |
| **0x278–0x2B7** | Read `String46[Var459]`, `[Var459+1]`, `[Var459+2]` and compare to `Var375`, **`Var377`**, **`Var376`** in that order |
| **0x2BB** | If any comparison failed, increment Local1 and jump **back to PC0x273** to test the next object; source has no explicit separate maximum guard |
| **0x2C1** | Once a matching object ID is found, branch on `Var370==1` (one selected statue) |
| **0x2DB** | If no one-statue branch, test `Var370==2` |
| **0x30B** | If no two-statue branch, test `Var370==3` |
| **0x344** | Source termination; no animation `breakHere` in LSCR201 |

### Source mechanism by selected statue count

**Var370=1:** Compare the matching `Local1` to `Var[371+1]`. If already present, leave it; otherwise set **`Var[371+1]=Local1`**.

**Var370=2:** Compare the matching ID against **`Var[371+1]`** and **`Var[371+2]`**. If present, leave the current choices. If absent, compute `getRandomNr(1)+1` (slot **1 or 2**) and replace `Var[371+selectedSlot]` with the matching ID.

**Var370=3:** Compare the matching ID against **`Var[371+1..3]`**. If absent, compute `getRandomNr(2)+1` (slot **1,2 or 3**) and replace one source array entry with the matching ID; otherwise preserve the three choices.

This is **conditional fairness in a procedurally assembled visual puzzle**: the next required object gets deliberately added to the randomized choice set without fixing all other visible objects or a universal layout.

### Source-boundedness and uncertainty

- The original eight source strings have **32 tokens across eight seeds**, and all **32 tokens match exactly one of objects741–748**. Thus, for intact original String46 values, the candidate search from 741 is mathematically bounded to at most **eight different verb19 probes**, even though its script has no explicit max-object-ID test. If String46 is altered/uninitialized, this guarantee does not hold; execution could access out-of-range object IDs.
- The correction runs only after source `Var457==1` and before `Bit365` is set. **Var457==0 on Regular-mode Room71 entry**, per original ENCD. Therefore **do not claim this corrective algorithm guarantees the first statue of an attempt**; the code may rely on other source paths/room rerolls.
- Room72 `LSCR200` is the separately decoded **487-byte no-yield layout renderer**. It draws the selected object IDs from Var371+ using `drawObject` and raw 8-pixel placement units, including one, two and three-object scenarios. When LSCR201 runs before LSCR200 on the same source entry path, its corrected object array is consumed by that layout script.
- The observed user-facing puzzle sequence still depends on the actual source RNG, logical rooms130/131/132, the current string seed, actor/object script dispatch, possible script cancellation, and actual image/Z-mask state. None was captured here.
- The source says **which ID must be included in the chosen slots**, not that every player always sees or can click the object under every natural game state. That is a later runtime/interaction verification.

## Testable consequences / engineering implications

1. **P4 procedural scene model:** source phase `choose` → `check next target` → `inject required object if absent` → `render`; record RNG draws, slot replacement, source variable IDs and image provenance.
2. **Regression vectors:** all eight global88 seeds; Var370 in {1,2,3}; required ID initially present vs absent; previous progress Var457=0/1; Bit365=0/1; all three logical pseudo-room IDs; and repeated statue object745 in seed5's four-token route.
3. **Validation:** independently descumm Room72 LSCR201/205 and global88; confirm native indexed frame/mask under actual game layouts, especially a seeded case with the required target initially absent. Confirm `Var459` moves in 3-character steps and the fourth correct token can set Bit365.
4. **Source safety:** input game archives remain unchanged and out of Git; log private captures under `FIXTURE\CAPTURES`, evidence manifests under `FIXTURE\REPORTS`, reusable test implementation only under `SOURCE\ScummBucket`.

**Evidence boundary:** deterministic original-source control logic verified by bytecode and pinned engine semantics; execution reachability, observed fairness in a save state, original-DOS interpreter semantics and native pixel fidelity **not verified**.
