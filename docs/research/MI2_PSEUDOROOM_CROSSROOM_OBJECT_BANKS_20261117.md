# MI2 procedural pseudo-rooms: Rooms 99–102 are object-image source banks (2026-11-17)

**Evidence:** Read-only original DOS VGA MONKEY2.000/.001; MONKEY2.001 SHA-256 ad045372e0d49626503bb50fca29a687ec8e01ef75d9b8bca702a366d143819e. Original archive, not observed gameplay. All 3 scene entry scripts below were independently instruction-boundary walked using a private narrow SCUMM-v5 decoder, cross-checked with ScummVM v2026.4.0 primary source: [script_v5.cpp](https://github.com/scummvm/scummvm/blob/v2026.4.0/engines/scumm/script_v5.cpp) and [object.cpp](https://github.com/scummvm/scummvm/blob/v2026.4.0/engines/scumm/object.cpp). No official descumm crosscheck, no instrumented ScummVM runtime, no pixel-fidelity acceptance. Original bytes remain outside Git.

## 13 logical scene instances assembled from foreign-room objects

Global original startup script 1 contains pseudoRoom mappings that alias physical resource 96 to logical rooms 149,150; resource 97 to 141,142,143,145,147,148,155; resource 98 to 140,144,146,151. The physical resources each have a 320×144 RMHD but their ENCD code dynamically imports objects from four OTHER physical room bundles, 99–102, before drawing them at new coordinates.

ScummVM v5 opcode SO_LOAD_OBJECT is o5_resourceRoutines subopcode 20. The implementation calls loadFlObject(object,source_room). Its source code looks up BOTH original OBCD and OBIM in that source room, creates an FLOB resource holding their contents, calls resetRoomObject to register the floating object in the active local object table, and returns early if that object is already loaded. It does NOT transplant the source room background. Script draw-at coordinates are in eight-pixel units.

### Entire entry-script alignment and instruction inventory

| Physical room | ENCD body offset | Body bytes consumed | Instructions | Relative destinations valid | Foreign object loads | Object draw instructions |
| ---: | --- | ---: | ---: | ---: | ---: | ---: |
| 96 | 0x7BAB59 | 511/511 | 93 | 18/18 | 11 | 11 |
| 97 | 0x7C9DE7 | 1850/1850 | 311 | 51/51 | 60 | 67 |
| 98 | 0x7D6BB9 | 1287/1287 | 226 | 38/38 | 36 | 38 |
| **Total** | | **3648/3648** | **630** | **107/107** | **107** | **116** |

**Static source instruction counts**, including mutually exclusive alias branches, not a single simultaneous runtime render. Some draw operations target local room objects rather than newly imported ones.

### Alias-by-alias source branches

| Physical room | Logical alias | Source-object load operations | Object draw operations |
| ---: | ---: | ---: | ---: |
| 96 | 149 | 5 | 5 |
| 96 | 150 | 6 | 6 |
| 97 | 141 | 9 | 9 |
| 97 | 142 | 12 | 16 |
| 97 | 143 | 7 | 11 |
| 97 | 145 | 8 | 9 |
| 97 | 147 | 8 | 8 |
| 97 | 148 | 9 | 9 |
| 97 | 155 | 7 | 5 |
| 98 | 140 | 9 | 10 |
| 98 | 144 | 6 | 6 |
| 98 | 146 | 12 | 13 |
| 98 | 151 | 9 | 9 |
| **Total** | 13 logical rooms | **107** | **116** |

Each row counts source instructions within the branch selected by an equality test on the **logical current room**. Conditional subbranches and runtime reachability remain unverified.

## All 39 source-bank objects are actually referenced

The original archive directly contains:

| Physical source room | RMHD size | Original paired object IDs | Count | Stored IMxx image states | Imported at least once by Room96/97/98 ENCDs |
| ---: | --- | --- | ---: | ---: | ---: |
| 99 | 8×200 | 1077–1084 | 8 | 8 | 8/8 |
| 100 | 8×200 | 1085–1098 | 14 | 21 | 14/14 |
| 101 | 8×200 | 1099–1103 | 5 | 5 | 5/5 |
| 102 | 8×200 | 1104–1115 | 12 | 12 | 12/12 |
| **Total** | | **1077–1115, contiguous** | **39** | **46** | **39/39** |

All four source rooms have only one-byte, terminating ENCD and EXCD bodies. This is direct evidence for **foreign-object source banks**, not ordinary standalone interactive 8-pixel-wide scenes. Their tiny transparent RMIM background strips remain an *independent* unresolved source-format question. Their **OBCD/OBIM data**, not the tiny RMIM backgrounds, are what the original code imports.

Concrete original source examples:
- Logical 149 loads source objects 1087,1094,1095 from bank 100, 1104 from bank 102 and 1081 from bank 99. It draws 1081 at raw (18,4) = native (144,32) and 1104 at raw (15,9) = native (120,72).
- Logical 150 draws imported 1090 at raw (16,13) = native (128,104).
- Logical 140 draws bank object 1080 at raw (1,4) = native (8,32), and 1110 at raw (16,4) = native (128,32).
- A source object can be drawn at different positions across different logical aliases.

## Animation exists *after* importing external images

Physical Room97 local scripts:
- LSCR212 is fully aligned **91/91 bytes, 26 instructions**: **13 draws** of local object1066's five stored states separated by **12 breakHere yields**, then stops. A separate fully aligned LSCR208 starts LSCR212 and waits for it.
- LSCR213 is fully aligned **98/98 bytes, 19 instructions**: picks an image state conditionally from random value and dialogue variables, calls drawObject(1098, state=Local2), yields once and loops. Object1098 comes from **bank100** and has six stored image states, 32×24. **Caller now established:** fully aligned Room97 LSCR202 starts script213 at PC0x026D and stops it at PC0x08E3; see [Room97 animated dialogue](MI2_ROOM97_IMPORTED_ANIMATED_DIALOGUE_20261117.md).
- LSCR205 fully aligned **220/220 bytes, 36 instructions**: actor7 movement/animation, wait, dialogue and ownership change; a separate kind of scene effect.
- Larger Room97 LSCR202 and scripts203/204 are **not yet fully aligned** by the private narrow walker; do not present them as solved.

## Engineering implications

1. Store **logical room ID, physical scene RMIM resource, and original source room for every floating object** separately. Do not invent local duplicates of source game assets.
2. Export an event for SO_LOAD_OBJECT, its source room/object ID, FLOB registration, and any failure/duplicate skip; subsequent state/position/class changes need independent timeline entries.
3. Resolve OBIM image states and OBCD logic from the bank source room. The active scene background remains the selected physical RMIM 96/97/98, not the bank's 8×200 placeholder.
4. Preserve alias-specific object placement, walkboxes, class flags, Box Matrix creation, and additional actor/palette/script events; source drawings are not known to be final front-buffer pixels.
5. Test logical rooms149/150 first, then140 and141, then all remaining logical aliases. Compare native indexed pixels and floating-object registrations with a pinned instrumented ScummVM build.
6. Official descumm -5 -o and native runtime reference remain mandatory for completion; the static source-aligned archive findings alone are research, not P4 acceptance.

This report contains only original resource metadata, instruction semantics, counts and source references. No copyrighted game binaries, images or audio are committed.
