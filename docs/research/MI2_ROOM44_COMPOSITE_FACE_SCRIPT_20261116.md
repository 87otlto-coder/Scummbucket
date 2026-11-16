# MI2 Room 44 — static talk/face compositor script (2026-11-16)

**Evidence class:** original archive source bytes decoded with a narrow, opcode-aligned v5 walker, and semantic opcode cross-check against pinned ScummVM v2026.4.0. **No descumm cross-validation, no runtime gameplay, no rendered-frame verification and no Windows debugger run.** No original art or script bytes are committed.

Input hashes (unchanged): `MONKEY2.000` cde7aa8980317e3a750fbb3b49884cdddaf1ff3d4231a0c840b22cceed9033f1; `MONKEY2.001` ad045372e0d49626503bb50fca29a687ec8e01ef75d9b8bca702a366d143819e.

Room 44 native dimensions **320×144**. LSCR **201** starts at decoded MONKEY2.001 offset **3,622,713**, containing a **402-byte** bytecode body following the 9-byte `LSCR` header.

## Main result: fully aligned selective script

A narrow static walker consumed **402/402 bytes** as **82 v5 instructions**, including `equalZero`, `isEqual`, `isLess`, `move`, `add`, `getRandomNr`, `expression`, direct/indirect `drawObject`, `jumpRelative`, `breakHere` and `stopObjectCode`. **Every static relative branch targets a decoded instruction boundary.** This is stronger than the original raw 11 `drawObject` byte-pattern hits, but remains preliminary until independently checked with descumm.

### Source-supported control inputs

- **Global `Var[3]`** = `VAR_HAVE_MSG` in ScummVM v5 bindings.
- **Global `Var[25]`** = `VAR_TALK_ACTOR`; this bytecode explicitly compares it to **5**.
- **Bit-variable references** `0x8219`, `0x8223`, `0x8224`, `0x821A` (conditional binary controls; a `0x8000`-tagged reference is not an ordinary plain integer global).
- Regular variables **161–164**, plus **524** (a dynamic object ID), and temporary local variables `0x4000–0x4002`.
- Source-stored object states for multiple expressive head/hand/mouth components of an illustrated character lying in bed; private source-native preview supports this **visual classification**, but no ScummVM pixel comparison has verified it.

The script comprises several mutually gated paths. It explicitly checks the message/actor flags, uses random selection, maintains a variable counter, and changes image states for multiple objects. These facts do NOT establish the animation timing of recorded voice/dialogue, or runtime reachability of every branch.

### Key decoded landmarks (relative to LSCR bytecode start)

| Bytecode PC | Source-backed action |
| --- | --- |
| `0x0000` | Tests bit-var `0x8219`; one outcome jumps to yield near end, effectively gating the update |
| `0x0005` | Draws object 447 using default image state |
| `0x0034`, `0x0039` | Tests `Var[3]` and `Var[25] == 5` before selecting facial states |
| `0x004A` | Random-number expression with `getRandomNr(2) + 1` into variable 161 |
| `0x007F`, `0x0084` | Tests/increments variable 164, a state-sequencing counter |
| `0x0090`, `0x00A0`, `0x00C2` | Draws object 461 in explicit states 1, 2 and 3 on different paths |
| `0x00D0–0x00DC` | Draws objects 452/453/454 with states from variables 161/162/163 |
| `0x0123–0x012D` | Loads local object-selection tuple **(462,463,464)** |
| `0x0142–0x014C` | Loads alternate tuple **(452,459,460)** |
| `0x0151` | Draws a **variable-selected object** using variable state 161 |
| `0x015C` | Draws an object ID held in global Var[524], with no explicit state operand |
| `0x0170–0x0176` | Draws objects 453/454 with variable states |
| `0x0181–0x0187` | Draws two variable-selected objects with variable state 161 |
| `0x018D` | `breakHere` (yields script scheduler) |
| `0x018E` | Jumps **-401** bytes back to the script start `0x0000` |

The original script has **one explicit unconditional yield in the cyclic control flow**, after a number of branching object updates. Changes to several image components can therefore be scheduled within one update of the script interpreter; **whether they become visible in the same rendered frame still requires engine-phase capture**.

### Why this is more than a multi-frame object

Room 44 has **20 paired objects and 40 stored image states**, without CYCL records or background Z-plane children. Its 201 script uses *several independent image objects at once* to build changing face/gesture displays, including conditional component replacement and dynamic object IDs. Treating each object independently as a loop would not recreate the composite visual result.

This is a promising P4 **composite facial/talking-head** test case. Unlike Room 55's random hold on a standalone two-state object, Room 44 ties image selection to **dialogue/message state and interacting visual layers**. It should eventually output an observed- or script-parameterized event graph, plus separate native image components and z/transparency properties. Do not invent a dialogue lip-sync cadence.

## Follow-up (not run)

1. Independently disassemble LSCR 201 with descumm and validate 82 opcode boundaries, conditional jump polarity, all object/state operands, and the behavior of bit-var references.
2. Locate callers and writers for bit flags `0x8219/0x8223/0x8224/0x821A` and global variables 161–164,524 in local/global scripts.
3. Decode representative object images and placement independently; capture source-to-compositor layer ordering, transparency and any same-coordinate replacement rules.
4. Run a configured original DOS VGA ScummVM capture of the conversational interaction, record script bytecode PC, global/bit vars, object states and native front pixels.
5. Preserve branch context and render phase for each event; compare exact indexed foreground frames, never reuse the captured final framebuffer as reconstruction input.

References: https://github.com/scummvm/scummvm/blob/v2026.4.0/engines/scumm/script_v5.cpp; https://github.com/scummvm/scummvm/blob/v2026.4.0/engines/scumm/vars.cpp; https://github.com/scummvm/scummvm/blob/v2026.4.0/engines/scumm/object.cpp.
