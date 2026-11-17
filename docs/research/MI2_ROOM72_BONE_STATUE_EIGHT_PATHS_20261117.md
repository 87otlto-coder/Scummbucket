# MI2 Room72/71 — eight authored three-symbol statue paths from global script88 (17 November 2026)

**Status:** new high-confidence **archive-derived source logic**. Input original DOS VGA `MONKEY2.000/.001` from read-only private uploaded `mi2.zip`; .001 SHA-256 `ad045372e0d49626503bb50fca29a687ec8e01ef75d9b8bca702a366d143819e`. Static v5 opcode and variable semantics cross-checked against primary [ScummVM v2026.4.0 `script_v5.cpp`](https://github.com/scummvm/scummvm/blob/v2026.4.0/engines/scumm/script_v5.cpp) (`o5_expression`, `o5_getRandomNr`, `o5_stringOps`, `o5_isEqual`, `o5_startObject`), [`script.cpp`](https://github.com/scummvm/scummvm/blob/v2026.4.0/engines/scumm/script.cpp) (v5 branch and direct/indirect variable logic). **No full official descumm run, real gameplay, renderer/palette trace or original DOS interpreter confirmation.** Original complete resource bytes, textual puzzle strings and private derived artwork are NOT committed.

## Crucial corrected symbol order

Room72 original OBCD objects **741..748**, each named `ugly bone thing`, have verb19 handlers that each directly assign three ASCII values to **Var375, Var377, Var376** **in that order**. Room72 `LSCR205` compares String46's sequential characters to **Var375, Var377, Var376 in that same order**, **not** to Var375/376/377 numerical order.

The physically significant comparison order is therefore:

| Source OBCD ID | First `Var375` | Second `Var377` | Third `Var376` | Encoded three-symbol code |
| ---: | :---: | :---: | :---: | :---: |
| 741 | H | R | L | **HRL** |
| 742 | P | A | H | **PAH** |
| 743 | L | H | P | **LHP** |
| 744 | A | H | R | **AHR** |
| 745 | H | R | P | **HRP** |
| 746 | R | L | P | **RLP** |
| 747 | L | P | A | **LPA** |
| 748 | R | A | H | **RAH** |

These short three-symbol keys are **source-coded logical state values**, not a claim about the exact letters drawn in the game's original image pixels, nor a translation of the five letters into body-part names.

This **corrects the prior research note** [Room72 symbols and caller gap](MI2_ROOM72_ORPHAN_PALETTE_AND_BONE_CODES_20261117.md), which initially displayed the same three values sorted by variable number, obscuring the actual comparison order.

## Missing source located: global script88 loads String resource46

The original .000 **DSCR directory entry88** points to a `SCRP` stored with physical **Room60** at decoded .001 offset **`0x4E7F4B`**, tagged chunk length263 bytes; script body starts `0x4E7F53`, 255 bytes. The source contains:
1. A direct bit-state assignment setting `Bit530=1`.
2. `o5_expression` evaluating **`Var100=8-1=7`** (an exact expression, not `getRandomNr(8)`).
3. A second expression evaluating **`Var100=getRandomNr(Var100)+1`**, producing an integer **1..8 inclusive** under pinned ScummVM's inclusive RNG contract.
4. Eight `isEqual(Var100,1..8)` branches. Each selected branch executes v5 `stringOps.loadstring(String46,<inline string>)`, where the original inline string comprises **13 capital A/H/L/P/R letters plus a literal final period**. The eight original full strings are deliberately **not reproduced** in this Git research note.
5. The 8 cases then jump to common termination. No ninth case was omitted: the two-stage `getRandomNr(7)+1` yields 8 choices.

An initial raw search also found **candidate** `startScript(88)` call bytes in global script1 (stored Room4) at .001 file offset **`0x36B8A`** and Room60 local script212 at **`0x4E5322`**. These caller candidate positions and their source preconditions **have not been exhaustively opcode-walked**. Thus the 8-string selector is real source code, but which startup/room paths re-roll it is unobserved.

## Explicit four-object route sequences

The original eight strings each begin with **four concatenated three-symbol tokens**, all matching exactly one of the eight original statue verb19 codes above. Converting those 12-character prefixes to source OBCD IDs yields:

| Choice in global88 | Original statue object IDs, ordered | Source token sequence |
| ---: | --- | --- |
| **1** | **741 → 742 → 746 → 744** | HRL / PAH / RLP / AHR |
| **2** | **742 → 747 → 741 → 744** | PAH / LPA / HRL / AHR |
| **3** | **743 → 748 → 747 → 745** | LHP / RAH / LPA / HRP |
| **4** | **744 → 747 → 745 → 743** | AHR / LPA / HRP / LHP |
| **5** | **745 → 744 → 747 → 745** | HRP / AHR / LPA / HRP |
| **6** | **746 → 741 → 744 → 747** | RLP / HRL / AHR / LPA |
| **7** | **747 → 746 → 741 → 744** | LPA / RLP / HRL / AHR |
| **8** | **748 → 747 → 746 → 741** | RAH / LPA / RLP / HRL |

All eight sequence prefixes are **internally consistent with the OBCD symbol table**; **32/32 3-character tokens** resolve to one of the eight statue IDs. The 13th alphabetic character in each source string lies after those four triples. Its intentional use is not demonstrated by this decoder and must not be mislabeled a guaranteed new object or terminator; an additional literal period follows it.

**Important distinction:** The source encodes solution *targets*, not a guaranteed map layout or proof that each required statue is visible when needed. The **Room72 procedural source renderer** randomizes which bone-statue objects are placed in various logical room instances; their availability and natural player navigation require runtime or complete call-graph validation.

## Direct puzzle validation logic from Room72 LSCR205

Complete original LSCR205 body is **199 bytes**, starts `0x5EC192`; see prior [full narrow walk](MI2_ROOM72_PSEUDOROOMS_RANDOM_LAYOUT_PALETTE_20261117.md). The critical original opcode spans can be independently checked:

- PC0x00D: `startObject(Local0,verb19)`, invoking selected statue's unique three-value assignment.
- PC0x012 `getStringChar(String46,Var459)`; PC0x019 `isEqual(Var100,Var375)`.
- PC0x020–0x02B: compute `Local1=Var459+1`, read String46[Local1]; PC0x032 compare to **Var377**.
- PC0x039–0x044: compute `Local1=Var459+2`, read String46[Local1]; PC0x04B compare to **Var376**.
- All three comparisons must succeed to set `Var160=1` (source PC0x052). Mismatches set Var160=0.
- On the success branch (with additional progression guard `Var457<=9`), PC0x07C executes **`add Var459,3`**. PC0x08D then compares Var459 against **12**; when equal it sets **Bit365=1**. The subsequent branching can route to physical Rooms71/73 or logical132 depending on flags/state.
- **Do not claim player completion is automatic**: active room state, flag365, Var457 and the physical layout affect later branches. The comparison mechanism and four-token target are static archive-derived facts.

## Source-backed Regular/Easy distinction: Room71 resets progression only on one difficulty path

Physical Room71 ENCD tagged chunk starts **`0x5D842D`**, body at `0x5D8435` (59 bytes). At body PC **0x01D** there is `equalZero(Bit567)` with relative +10, followed by two `move` instructions:
- **Regular Mode, Bit567=0:** source sets **Var457=0** and **Var459=0**, initializing the puzzle attempt index.
- **Easy Mode, Bit567=1:** branch skips these two assignments and preserves existing values.

The identification of Bit567 as **Regular/Easy mode** is original script-backed in [difficulty analysis](MI2_MODE_BIT567_ROOM108_UI_20261117.md). This is a source entry-script conditional, **not a claim that natural Easy gameplay always enters the room or uses the puzzle**.

## Implementation consequences for ScummBucket

- Preserve separate identities for String resources, original object VERB state data, variable banks, room-local and global scripts, logical/physical rooms and randomized initial selections.
- A P4/P6 preview needs to distinguish **target data** (eight four-statue sequences), **procedural presentation** (Room72 layouts), **dynamic interaction** (object verb19), and **actual runtime state** (Var459 pointer, Bit365, difficulty, room). A single GIF or static collage misses the system.
- This is a candidate for *source-derived deterministic puzzle manifests* in P1/P4 research, but do not auto-generate solved-room screenshots or simulated actions and mislabel them as captured gameplay.
- Record original .000/.001 hashes and exact source offsets; test and verify with official pinned descumm and ScummVM or original-DOS gameplay before declaring supported reconstruction.

**Evidence boundary:** original source code + fully aligned relevant local-script snippets, interpreted using authoritative engine source. No observed interaction, no source independent decoder release/test, and no pixel-verified output.
