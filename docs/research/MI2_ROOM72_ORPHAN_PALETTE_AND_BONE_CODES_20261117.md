# MI2 Room72: local204 caller gap and eight encoded skeleton-statue patterns — 17 November 2026

**Evidence:** original DOS VGA `MONKEY2.000/.001`, read-only private uploaded `mi2.zip`. XOR 0x69 for stored archive resources. SHA-256 **MONKEY2.001** `ad045372e0d49626503bb50fca29a687ec8e01ef75d9b8bca702a366d143819e`; archive index original `MONKEY2.000`. Original source bytes, screenshots, saves and music are excluded from GitHub. Opcode interpretation uses **pinned [ScummVM v2026.4.0 script_v5.cpp](https://github.com/scummvm/scummvm/blob/v2026.4.0/engines/scumm/script_v5.cpp)**; no emulator execution or pixel-accurate rendering.

## 1. The striking negative result: palette intensity script204 has no literal caller inside its own room

[Previous analysis](MI2_ROOM72_PSEUDOROOMS_RANDOM_LAYOUT_PALETTE_20261117.md) completely decoded **Room72 LSCR204**, body offset `0x5EC138`, 81 bytes, 13 aligned instructions; it periodically calls VGA-only palette intensity operations on ranges65–157 and169–187, with randomly selected scale values230–280 and rejection of small changes. The code is real, but whether it runs in any natural scene is **unproven**.

New read-only search:
- Verified the physical Room72 resource contains **ENCD, EXCD, six LSCR scripts (200–205), 18 OBCD object resources**, and **no bundled global SCRP resources**. Two object families are eight identical-named bone-statue scripts and two archways; many additional OBCD entries contain empty VERB tables.
- Exhaustively searched the raw byte streams of **all Room72 ENCD/EXCD/LSCR bodies and all 50 parsed OBCD/VERB handler bodies** for all *literal immediate-argument v5* `o5_startScript(204)` forms: opcodes `0A,2A,4A,6A,8A,AA,CA,EA` followed by byte `CC` (204) and a terminating word-vararg marker `FF`. **No matches.** Also checked source-literal `o5_chainScript(204)` immediate forms `42 CC` and `C2 CC`; none among the Room72 script/handler code.
- Independently parsed the original **.000 DSCR 199-entry index** and mapped **167 populated indexed global SCRP resources** in the .001 archive (global script IDs1..167). Found **one literal** `o5_startScript(204)` occurrence across that global corpus: **global script80**, stored in physical Room46, at decoded script bytecode PC `0x0600`, file offset `0x3A0AE8`.
- Crucially that external caller is preceded **immediately by** `48 04 00 2E 00 03 00` at script PC `0x05F9`, a v5 **`isEqual(Var4=VAR_ROOM,46)`** conditional with relative branch +3; the call `0A CC FF` is **only reached when logical current room equals 46** under pinned ScummVM `jumpRelative` semantics. In that branch `204` resolves to *Room46's* local script204, **not Room72's local204**, because local script identity is associated with the current room resource.
- No claim of full `SCRP80` instruction-boundary validation; this isolated predicate+call opcode span is operand-aligned, and its placement/caller condition is consistent with the exact original bytes and pinned v5 semantics.

**Best current classification:** Room72 LSCR204 is **a source-encoded potential effect without an identified direct static start caller**, and is a **candidate unused/unreachable routine**. It is NOT established dead code. An **indirect script ID**, dynamic call, other global or v5 engine event could potentially invoke it; static absence of literal starts does not prove global runtime unreachability. Equally, its presence is **not** evidence that the room visibly flashes when entered.

**P4 requirement:** The inventory should record effects with `source_present=true`, `caller_verified=false`, `runtime_observed=false` rather than automatically rendering every enumerated palette-affecting script.

## 2. Eight named skeleton statues encode an eight-entry three-symbol table

Room72 includes eight OBCD objects **741–748**, each original OBNA text **`ugly bone thing`**. Their inspected original description text identifies them as strange skeleton statues (not an invented interpretation of the artwork). Every object offers an **OBCD/VERB handler for verb19** containing exactly three direct bytecode writes to global variables **Var375, Var377 and Var376** (in that assignment order), then terminates. **All eight verb19 handlers consume 16 bytes each**, and each assigned value is an uppercase ASCII byte from the set **A/H/L/P/R**.

After reordering as `Var375,Var376,Var377`, the exact original *source-coded* triples are:

| Object ID | `Var375` | `Var376` | `Var377` | Three-symbol sequence |
| ---: | :---: | :---: | :---: | :---: |
| 741 | H | L | R | **HLR** |
| 742 | P | H | A | **PHA** |
| 743 | L | P | H | **LPH** |
| 744 | A | R | H | **ARH** |
| 745 | H | P | R | **HPR** |
| 746 | R | P | L | **RPL** |
| 747 | L | A | P | **LAP** |
| 748 | R | H | A | **RHA** |

These are **not** the object's art pixels, image-state IDs or necessarily readable text on the game screen. They are explicit **script variable assignments** in the original interaction method. The source uses each unique three-letter combination as state data.

The prior complete Room72 `LSCR201` independently selects from **object IDs741..748**, rejecting duplicates in its randomized layout. `LSCR205` reads **three successive bytes of String resource46**, compares them with **Var375–377** and then changes navigation/game state. This provides a concrete cross-resource path for puzzle/state logic:

`random selection of bone objects → variable-selected object interaction / verb19 → three-letter Vars375/376/377 → LSCR205 String46 comparison → route/update game state`.

**Confidence:** Source-coded data flow is strong, but caller sequence, actual letter meaning (e.g. which body parts A/H/L/P/R represent), String46 origin/content, and real successful gameplay path remain **unverified**. The conventional game-story resemblance to a bone puzzle is suggestive, but do not claim exact on-screen symbol shapes or the solved sequence from these bytes.

## 3. Physical versus logical room distinction remains essential

[Pinned ScummVM v5 `o5_pseudoRoom`](https://github.com/scummvm/scummvm/blob/v2026.4.0/engines/scumm/script_v5.cpp) and [`startScene`](https://github.com/scummvm/scummvm/blob/v2026.4.0/engines/scumm/room.cpp) confirm **logical rooms130/131/132 map to physical Room72**. The same resource bundle can contain dormant visual scripts, distinct procedural layouts and active interaction handlers depending on the logical room and global puzzle variables. Do not invent one canonical room72 animation.

## Follow-up gates

1. Decode **String resource46 initialization/writers** and the complete branch semantics of Room72 `LSCR205`'s three-symbol comparison. Infer only what original script bytes establish; if the input is game-generated, preserve source/seed.
2. Trace nonliteral starts of local204 (e.g. `startScript(variable)`, `chainScript(variable)`, cutscene/scroll script variables), and inspect any relevant global cross-room callbacks. Do not call local204 unreachable without a systematic dynamic-call analysis.
3. Capture Room72 logical130/131/132 and observe whether palette changes ever arise; record `LSCR204` live script slots and 65–157/169–187 palette hashes.
4. For eight objects741–748, verify object-state/images, dynamic location, exact original verb dispatch, String46 comparisons and layout puzzle outcome against native indexed screenshots. Keep copyrighted original media under `FIXTURE`, not Git.

**Bottom line:** The same original game bundle combines **procedural physical scenery** and **stateful symbol logic**, plus a **present-but-unconfirmed palette effect**. Parsing all animation-like source bytes is insufficient to classify active environmental animation.
