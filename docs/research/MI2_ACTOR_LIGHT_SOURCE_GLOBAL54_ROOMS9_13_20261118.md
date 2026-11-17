# MI2 source-level dual actor lighting: global54 in Rooms 9 and 13 (18 November 2026)

Evidence: read-only original DOS VGA MONKEY2.001 (stored-byte SHA-256 ad045372e0d49626503bb50fca29a687ec8e01ef75d9b8bca702a366d143819e) and paired MONKEY2.000 resource directory. Source opcodes crosschecked with pinned ScummVM v2026.4.0 script_v5.cpp, script.cpp, palette.cpp, vars.cpp. Original game data and screenshots remain outside Git. **No descumm, runtime, original DOS stepping or native RGB/pixel fidelity acceptance.**

## Discovery: a second, parameterized actor-X lighting controller

Previous research fully decoded global49, an actor-Ego X-interpolated palette intensity controller for palette indexes 192–207, especially Room93: see MI2_ROOM93_ACTOR_POSITION_PALETTE_LIGHTING_20261117.md.

The original indexed global SCRP54 is stored with physical Room4 at .001 bytecode body offset **0x38C99**, length **224 bytes**. A separate narrowly scoped SCUMM v5 opcode walker consumed **224/224 original bytes, 25 instructions and 9/9 valid relative branch targets**. Embedded original debug text identifies it as an **actor-light-source script**.

Its incoming Local0 is an **actor ID**:
1. At PC0 guard Var49=VAR_VIDEOMODE==19 (VGA); otherwise stop.
2. At PC0x007 call getActorRoom(Local0) and compare to Var4 (logical current room). If the actor is elsewhere, yield and re-check instead of updating the palette.
3. At PC0x013–0x033 search X control points in Var285..290, beginning with an index of 5.
4. At PC0x033–0x086 interpolate intensity between neighbors in Var291..296 using getActorX(Local0), integer expression arithmetic and signed division truncating toward zero.
5. At PC0x086 compare interpolated Local6 to cached Local7. If changed, PC**0x08D** issues roomOps(SO_ROOM_INTENSITY,Local6,**208,255**), then stores Local7=Local6.
6. The script contains a source-coded divide-by-zero diagnostic (PC0x09B–0x0DB) and a one-breakHere polling loop returning to PC0x007.

The palette range **208..255** comprises **48 indices** and is separate from global49's **192..207** (16 indices). Pinned ScummVM palette.cpp darkenPalette scales the current room's **base RGB palette**, clipping channel output at 252 in ordinary v5. The source indexed pixel bytes remain unchanged; cached output scale prevents redundant palette updates.

## Rooms 9 and 13 set up independent brightness curves

Both original ENCD resources begin with an instruction-aligned setVarRange for six 16-bit X values at Var285..290, followed by six 8-bit intensity values at Var291..296, then directly **start global49**.

| Room | X control points | Intensities | Original object names corroborating context |
| --- | --- | --- | --- |
| 9 | [0,0,141,180,241,320] | [0,255,200,200,50,50] | piano, Jojo, barkeeper, metronome, upper deck |
| 13 | [0,0,225,320,320,320] | [0,100,235,200,200,200] | Largo LaGrande, dresser, bed, voodoo doll |
| 93 (earlier report) | [0,0,100,160,230,320] | [0,100,200,255,200,100] | eight logical pseudo-room corridor variants |

The first (0,0) pair is a sentinel, not an active segment at native actor X=0. The controller's effective first brightness is 255 in Room9 and 100 in Room13.

### Source-authored starts of actor-tracking global54

- Room9 LSCR201, body 0xA8BF7 (30 bytes): **startScript(54,[actor9])** at PC0x00E. The same short source script positions actor9 in Room9 at native (33,108).
- Room13 LSCR201 body 0xF9A05 (83 bytes): **startScript(54,[actor6])** at PC0x04C.
- Room13 LSCR209 body 0xFA118: **startScript(54,[actor6])** at PC0x07F.
- Room13 LSCR211 body 0xFA3DA: **startScript(54,[actor6])** at PC0x04A.
- Global70 (stored Room9) includes source-literal startScript(54,[actor6]) candidates at two offsets (body PCs 0x00D8 and 0x024A); **the complete parent branches are not yet fully walked**.

The caller bytecode is a valid immediate script-ID 54 with source word-vararg actor6/9, not an assumption from a raw occurrence of palette color. **These are authored call sites, not observed simultaneous execution**. A source-consistent scene could have global49 tracking Ego and global54 tracking actor6 or9, writing different palette ranges as their X coordinates change.

## Source-derived brightness samples (actor X in 0..319)

Interpolation uses exact integer truncation toward zero; samples assume the entry-seeded arrays remain unchanged.

| X | Room9 RGB scale | Room13 RGB scale |
| ---: | ---: | ---: |
| 0 | 255 | 100 |
| 50 | 236 | 130 |
| 100 | 216 | 160 |
| 141 | 200 | 184 |
| 180 | 200 | 208 |
| 210 | 127 | 226 |
| 225 | 89 | 235 |
| 241 | 50 | 230 |
| 300 | 50 | 208 |
| 319 | 50 | 201 |

Room13's repeated X=320 points make the **exact endpoint 320** a potential divide-by-zero path; the script already contains an error-message branch. Runtime actor X bounds must be checked before declaring it reachable. A 320×144 static RGB export would discard the distinction between changing source RGB and unchanged stored indexed pixels.


### Original CYCL resources confirm this is not normal palette rotation

Both Room9 and Room13 carry a tagged CYCL chunk of **10 bytes total** (8-byte header plus **two zero payload bytes**): Room9 CYCL at decoded .001 offset **0xA114A**, Room13 at **0xF0FEE**. These contain **no palette-cycle records**. Therefore the actor-driven changing RGB values in global49/global54 are a separate animation mechanism, and a room-census based only on populated CYCL would miss both. This establishes source-encoded effects, not observed RGB changes in live gameplay.

## P4 architecture and validation

Record both light-controller script IDs (49/54), target actors, current logical and physical rooms, runtime X breakpoints and brightness arrays, script PC and scheduler phase, RGB ranges 192..207 and 208..255, and source RGB palette identity. P4 should retain dynamic palette transforms as independently composable state rather than pre-baking a frame into object art.

Next independent gates: official descumm cross-check of global54, Room9/13 entry/actor-callers; instrument both actors and palette ranges during genuine scenes with VGA Var49=19; compare indexed framebuffer **and native RGB palette**. Original DOS interpreter corroboration remains needed if ScummVM semantics diverge.

**Evidence status: source-decoded and source-interpreted; not runtime-observed or pixel-verified.**
