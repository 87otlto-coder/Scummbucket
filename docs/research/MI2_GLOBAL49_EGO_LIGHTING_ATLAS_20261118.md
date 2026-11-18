# MI2 original VGA: actor-X lighting atlas across 12 physical rooms without palette-cycle records (18 November 2026)

**Evidence:** read-only original DOS VGA `MONKEY2.000/.001` source archive, SHA-256 original MONKEY2.001 `ad045372e0d49626503bb50fca29a687ec8e01ef75d9b8bca702a366d143819e`; physical-room LOFF, original RMHD, CYCL, ENCD, selected LSCR and global SCRP resources. Source instruction semantics checked with pinned [ScummVM v2026.4.0 script_v5.cpp](https://github.com/scummvm/scummvm/blob/v2026.4.0/engines/scumm/script_v5.cpp), [script.cpp](https://github.com/scummvm/scummvm/blob/v2026.4.0/engines/scumm/script.cpp), [vars.cpp](https://github.com/scummvm/scummvm/blob/v2026.4.0/engines/scumm/vars.cpp), [palette.cpp](https://github.com/scummvm/scummvm/blob/v2026.4.0/engines/scumm/palette.cpp). **No official descumm crosscheck, real game playthrough, original interpreter parity or indexed/RGB frame verification.** No copyrighted art or palette bytes in Git.

## Original resource census: 11 ENCD resources contain a source-aligned global49 start; Room34 uses a local controller

Global `SCRP49`, stored with physical Room4 at bytecode offset **0x38B3D**, fully previously independently walked (**218/218 bytes,25 instructions,9 valid relative jumps**), computes actor1/Ego-X interpolation from Var285..290 (six X control points) and Var291..296 (six RGB-scale control points), updating **base-palette RGB indices192–207**, not indexed pixels. The target script restarts non-recursively on re-invocation, dropping prior cached scale.

Original `setVarRange` literal values and **authored** global49 starts in physical room-entry code:

| Physical room | Original RMHD width×height | Source X values at Var285..290 | RGB scale values Var291..296 | Source start49 scope |
| ---: | --- | --- | --- | --- |
| **9** | 320×144 | [0,0,141,180,241,320] | [0,255,200,200,50,50] | ENCD PC0x1A, source complete |
| **13** | 320×144 | [0,0,225,320,320,320] | [0,100,235,200,200,200] | ENCD PC0x1A, source complete |
| **20** | **792×144** | [0,−30,260,343,490,543] | [0,255,255,150,150,255] | ENCD PC0x26, complete |
| **21** | **456×144** | [0,0,187,225,266,320] | [0,255,255,25,220,220] | Conditional ENCD PC0x80; additionally local208 starts/restarts49 under VGA |
| **70** | **640×144** | [0,0,170,273,480,640] | [0,120,255,100,255,255] | ENCD PC0x1A, complete |
| **71** | 320×144 | [0,0,160,320,480,480] | [0,100,255,80,255,255] | ENCD PC0x1A, complete |
| **75** | 320×144 | [0,0,120,215,320,999] | [0,100,255,100,100,0] | ENCD PC0x2D, complete |
| **90** | 320×144 | [0,0,0,0,157,320] | [0,0,0,50,255,50] | ENCD PC0x1F, aligned prefix (remaining instructions unsupported by narrow walker) |
| **91** | 320×144 | [0,0,135,215,275,320] | [0,255,255,200,100,50] | ENCD PC0x2E, complete |
| **92** | 320×144 | [0,115,200,220,221,320] | [75,255,150,150,255,255] | ENCD PC0x1F, aligned prefix (later unsupported instructions) |
| **93** | 320×144 | [0,0,100,160,230,320] | [0,100,200,255,200,100] | ENCD PC0x1E, complete; Bit728/room state may subsequently stop49 |

**A twelfth physical room, 34 (320×144),** seeds Var285..290 **[0,0,199,224,247,340]** and Var291..296 **[0,255,255,90,70,70]** in its fully aligned 96-byte ENCD, but **does not directly start49 from ENCD**. Instead ENCD PC0x41 calls **local203**, a fully aligned **43-byte,12-instruction,5-branch** polling controller containing conditional source **`startScript(49)` and `stopScript(49)`**. Its start condition depends on an incoming `Local0` and `Var1`; ENCD starts it without explicit arguments, so the normal initialized Local0 is zero on that source entry. Investigate external callers and dynamic arg setup before claiming global49 is naturally active in Room34.

**All 12 rooms above have original tagged `CYCL` chunks of length exactly 10 bytes (8-byte header + two zero payload bytes), with no active color cycling records.** This is archive-exact and demonstrates the insufficiency of CYCL-only animation discovery for P4. It does not imply every start49 source call actually runs under all game states.

### Technical exceptions that matter

1. **Room21 has overlapping 7-element ranges** in original ENCD: `setVarRange(Var285,[0,0,187,225,266,320,999])` then `setVarRange(Var291,[0,255,255,25,220,220,220])`. The earlier 999 at Var291 is **overwritten** by the first brightness value; effective X control set in the table is six entries. [Room21 camera-coupled lighting report](MI2_ROOM21_CAMERA_COUPLED_THREE_BANK_LIGHTING_20261118.md) shows local208 updates brightness points and restarts script49 while shading indices16–190 from camera X.
2. **Room20's walkbox geometry exceeds final X=543** (boxes cover native x556–653), so global49 **extrapolates beyond** the final anchor, reaching raw source light-scale>255. The engine does not pre-clamp it to255; output RGB channels are capped252. [Room20 extrapolation and BoxM report](MI2_ROOM20_SWAMP_LIGHT_EXTRAPOLATION_20261118.md).
3. **Room13 has repeated final X=320**, so an actor exactly at or beyond its last knot follows the last defined segment with zero `dx`, potentially reaching global49's original explicit diagnostic. Game walkboxes appear to top out around native X264, so this is **not** automatically a reachable bug; don't claim one without actor position capture. **Room90's first several X knots are also repeated at 0**, which can affect the exact actor X=0 edge; parse original control flow carefully.
4. **Room75's final X999** lies beyond its native width320. It can act as a genuine upper extension of the last brightness segment, but no actor can normally stand at X999 in a 320-wide room. The included zero final scale is a source interpolation endpoint, not proof the color reaches zero in natural gameplay.
5. Global49 **can be stopped** under a conditional in Room93 ENCD; global lighting is not simply “on in all eleven rooms” for all difficulty/bit states.
6. **Global49/54 survive scene transition until explicit stop/replacement/self-stop** in pinned ScummVM: `startScene` invokes `killScriptsAndResources` which kills local/room/object but not global slots. `startScript(49)` nonrecursive replaces prior49; `startScript(54,[actor])` nonrecursive replaces prior actor54 and resets local cache. This matters especially for [Room9 global70](MI2_ROOM9_GLOBAL70_DUAL_LIGHTING_CUTSCENE_20261118.md), [Room13 Largo exits](MI2_ROOM13_LARGO_LIGHT_EXIT_CUTSCENE_CORPUS_20261118.md), and [Room21](MI2_ROOM21_CAMERA_COUPLED_THREE_BANK_LIGHTING_20261118.md).

## New engineering classification

P4 should inventory **SCRIPTED_ACTOR_X_PALETTE_INTENSITY** separately from `CYCL`, scripted random intensity, palette fades, frame/image-state loops and costume animation. Record per-room control-point globals, actor target, palette ranges, active source-script slot/PC, camera/Ego X, original CLUT identity, recursive/nonrecursive start, and current logical vs physical room. Do not infer FPS or a displayed color from source code alone.

Runtime verification matrix should include source room entry in Rooms9,13,20,21,34,70,71,75,90,91,92,93, plus actual left/mid/right actor positions. Compare indexed front-buffer AND active RGB palette. In Room20 specifically test x>=544; in Room21 test cameraX changes and repeated global49 starts. Official pinned descumm crosscheck is a prerequisite before production acceptance.

**Source research only; original game archive unchanged and private.**
