# MI2 Room80 — original script-generated four-verse bone-song clue (17 November 2026)

**Evidence:** read-only original DOS VGA `MONKEY2.000/.001` from private `mi2.zip`, fingerprint .001 SHA256 `ad045372e0d49626503bb50fca29a687ec8e01ef75d9b8bca702a366d143819e`. Physical Room80 LFLF `ROOM` at decoded file offset **`0x64D008`**, original `RMHD` dimensions **320×200**, zero paired OBIM/OBCD objects, 43,940-byte `RMIM` tagged source background, **522-byte `ENCD`** source body at **`0x65806A`**. Independently walked **522/522 bytecode bytes, 85 instructions, 35 signed relative branch targets, all 35 valid instruction boundaries**, under a narrow private v5 parser. Original `EXCD` is 10 bytes; local200 is 6 bytes. Semantics checked against pinned [ScummVM v2026.4.0 script_v5.cpp](https://github.com/scummvm/scummvm/blob/v2026.4.0/engines/scumm/script_v5.cpp) (`o5_stringOps`, `o5_print`, `o5_roomOps`, `o5_cursorCommand`, `jumpRelative`) and [string.cpp](https://github.com/scummvm/scummvm/blob/v2026.4.0/engines/scumm/string.cpp) (`convertMessageToString`, `0xFF 07` substitution). **Not tested with official descumm, ScummVM gameplay, the original DOS interpreter, text glyph framebuffer or audio.** No copyrighted original text/body, image or song is copied to Git.

## Main discovery: the original clue is dynamically typeset from String46

Global **SCRP[88]**, physically stored Room60, chooses one of **eight** authored source string values for **String resource46**. Each contains **13 uppercase A/H/L/P/R characters** followed by a literal period. [Eight path study](MI2_ROOM72_BONE_STATUE_EIGHT_PATHS_20261117.md) proves the first 12 letters form **four consecutive statue-object codes** consumed in Room72.

**Room80 ENCD is the missing *player-facing decoder*.** It reads the same source `String46` sequentially, translates each symbol into a bone name, and prints a four-verse clue using dynamic source string resources **47 and48**.

Original source maps five characters:

| Source byte | Bone name loaded by Room80 `stringOps.loadstring` |
| --- | --- |
| `0x48` H | head |
| `0x41` A | arm |
| `0x52` R | rib |
| `0x50` P | hip |
| `0x4C` L | leg |

Two complete five-way selector blocks occur at **body PCs0x05A–0x0AF** (String47, first bone) and **0x0BA–0x10F** (String48, second bone). Their source `isEqual` false-branch offsets and final jump destinations are all aligned.

### Exact 13-character and 12-link algorithm

- PC`0x04E`: `Local2=0`.
- PC`0x053`: read `String46[Local2]` into global Var100, select mapped bone name and load **String47**.
- PC`0x0B0`: increment Local2.
- PC`0x0B3`: read `String46[Local2]`, select mapped bone name and load **String48**.
- PC`0x110`: print **one reusable template** in text slot **actor254**, substituting **String47 and String48** through embedded `FF 07 2F 00` and `FF 07 30 00` escape controls, respectively. In pinned ScummVM, `convertMessageToString` case7 resolves these *string-resource* references, not actor costume sprites.
- PC`0x14D`: increment Local2; source tests Local2==**4,7,10,13** in sequence.
  - When it becomes **4,7,10** the script prints the corresponding **Verse 2/3/4** heading before the next link.
  - When it becomes **13**, it exits the loop.
  - Otherwise PC`0x1D5` calls `stringOps.copystring(47,48)`, i.e. **the previous second bone becomes the next first bone**. PC`0x1D9` jumps back to **PC0x0B3**, only reading the next character of String46, not re-reading the first.
- Room80 therefore renders **exactly 12 adjacent bone relationships from 13 input characters**, grouped into **four verses of three relationships**: verse1 pairs indices(0,1),(1,2),(2,3); verse2 (3,4),(4,5),(5,6); verse3 (6,7),(7,8),(8,9); verse4 (9,10),(10,11),(11,12).

**Correction to a prior unknown:** the 13th letter is **essential**, not an unexplained surplus character or optional terminator. Room72's four 3-letter statue codes use `String46[0..11]`; the song's **final relationship uses `String46[12]`**. Thus one source data string supports **two different logical interpretations**: four puzzle checks (12 chars) and twelve adjacent lyric relationships (13 chars). Avoid modifying String46 to 12 letters in a future asset pack.

### Source-conditioned UI presentation

- Room80 `RMHD` is **320×200**, unlike the typical 320×144 playable-room source backgrounds. No OBCD/OBIM pair exists: the source text is **dynamically constructed**, not decoded as sixteen image states.
- ENCD PC0 sets the room screen to (0,200). It first tests whether global script42 is already running and terminates this entry script if so; PC0x011 gates the black palette intensity setup on `Var49==19` (VGA) and PC0x018 uses `SO_ROOM_INTENSITY(0,16,255)`.
- Source `beginCutscene([3])` at PC0x01D, initial `breakHere`, `SO_CHARSET_SET(5)`, and text prints with explicit colour170 and screen coordinates from locals. Verse headings occur at PC0x035, 0x15C, 0x184, 0x1AC; reusable paired-bone template at PC0x110.
- At PC0x1DC the script checks video mode and, when VGA, sends `SO_ROOM_INTENSITY(255,16,255)` to restore normal palette. After re-enabling input, `beginOverride` plus `Var106` polling holds a cutscene branch until its state changes. Room80 local200, **6/6 bytes**, writes `Var106=1`, then terminates. How the original input dispatcher triggers local200 requires a runtime trace; script source indicates a possible release condition.
- The finishing branch at PC0x1FE source-calls **global script24 with arguments `[Var102,2]`** and then ends the cutscene. This implies a state-dependent return/navigation callback rather than a fixed unconditionally next-room transition. Its original in-game playback and input/skip behaviour remain unobserved.

## Cross-room puzzle data flow

1. [Global script88](MI2_ROOM72_BONE_STATUE_EIGHT_PATHS_20261117.md) selects one of 8 13-character sources; startup global1 and Room60 LSCR212 include aligned **`startScript(88)` + wait-until-finished** call idioms.
2. **Room80** decodes those chars into a 4-verse **source-dynamic clue**, via String47/48 and text interpolation.
3. [Room72](MI2_ROOM72_GUARANTEED_NEXT_STATUE_LAYOUT_20261117.md) source-interprets the first 12 characters as four selected statue objects, injects the next matching object into a randomized display under the prescribed progress guard and matches an interacted statue's three-letter code.
4. [Room73 transition](MI2_ROOM72_73_74_BONE_MAZE_EXIT_DOOR_20261117.md) conditionally follows the completed 12-character puzzle progression.

This is an original-source **data-driven clue UI + randomized procedural scene + conditional scene transition**, not four independent video assets. For P4/P6, keep the letter sequence as saved game state, the lyric layout as text script output, the statue layout as object IDs/states, and the player/room progression as a separate event model. An arbitrary set of extracted PNGs alone does not reconstruct the authored experience.

## Required validation

- Run official pinned `descumm -5 -o` over Room80 `ENCD`, `EXCD` and `LSCR200`; compare all 85 source instruction boundaries and 35 branch targets.
- Capture natural entry for two distinct global88 seeds. Record String46 value (privately), text resources47/48, `Local2` indices, Verse boundaries, text slot output position and palette, button/skip behaviour, global script42 and global script24.
- Measure actual font glyph positioning against the **320×200 indexed frame**, and verify any UI darkening/fade only after real runtime capture. Preserve original source hashes/edition; no game or generated art in Git.

**Evidence boundary:** original archive source decoding and ScummVM code interpretation verified structurally; actual execution/timing/fonts/palette and native RGB/indexed fidelity **not observed**.
