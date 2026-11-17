# MI2 pseudo-rooms and Room93 eight-way animated environment (2026-11-17)

**Evidence:** Read-only original DOS VGA MONKEY2.000 / MONKEY2.001 (the latter SHA-256 `ad045372e0d49626503bb50fca29a687ec8e01ef75d9b8bca702a366d143819e`), narrow private SCUMM v5 bytecode walker and pinned primary ScummVM [script_v5.cpp](https://github.com/scummvm/scummvm/blob/v2026.4.0/engines/scumm/script_v5.cpp), [room.cpp](https://github.com/scummvm/scummvm/blob/v2026.4.0/engines/scumm/room.cpp) and [script.cpp](https://github.com/scummvm/scummvm/blob/v2026.4.0/engines/scumm/script.cpp). **Archive-decoded and implementation-source findings, NOT observed gameplay, official-descumm comparison, original-interpreter verification, or indexed-pixel fidelity**. Game resources not committed.

## Finding 1: logical room IDs do not always correspond to physical room resources

Original indexed global `SCRP[1]` (stored in room4) contains **five consecutive well-formed `o5_pseudoRoom` instructions**. The bytes are in the original code region, starting at XOR-decoded absolute offsets below, but **the entirety of very long global1 has not been independently opcode-aligned**. The consecutiveness and ScummVM's documented opcode implementation provide high confidence in their structural interpretation, with explicit remaining global-call-path uncertainty.

| Original source opcode offset | Physical LFLF room resource | Logical / pseudo-room IDs registered | Count |
| --- | ---: | --- | ---: |
| `0x35DD7` (220,631) | **72** | 130,131,132 | 3 |
| `0x35DDD` (220,637) | **96** | 149,150 | 2 |
| `0x35DE2` (220,642) | **97** | 141,142,143,145,147,148,155 | 7 |
| `0x35DEC` (220,652) | **98** | 140,144,146,151 | 4 |
| `0x35E1B` (220,699) | **93** | **160,161,162,163,164,165,166,167** | 8 |
| | | **24 distinct logical aliases** | **24** |

The five sources have encoded form `CC <resource-id> <one-or-more alias bytes >=0x80> 00`. In `ScummEngine_v5::o5_pseudoRoom()`, each aliased `j` sets `_resourceMapper[j & 0x7F] = physical_resource`. In `room.cpp`, when entering a logical room number >=0x80 (v5), `_roomResource = _resourceMapper[logical_room & 0x7F]`. **Current logical room ID and physical source resource ID are two distinct fields**.

Why this matters: a file inventory of original `ROOM` resources can be correct and yet miss 24 logical scene identifiers in the interpreter. Do not create 24 copies of original assets; implement derived room instances referencing a shared physical resource with unique state/caller contexts.

## Other pseudo-room families: script-assembled cross-resource objects

The remaining alias groups in the source mapping (physical 96/97/98) are now independently fully decoded: each ENCD loads original OBCD/OBIM from **four foreign source banks 99–102** using SO_LOAD_OBJECT, then positions those assets in the current scene. All 39 bank objects are referenced by those entry scripts. Their 8×200 RMIM resource size is not the imported image size. See [13 aliases and object-bank reconstruction](MI2_PSEUDOROOM_CROSSROOM_OBJECT_BANKS_20261117.md), and [Room97 scripted six-state foreign-object dialogue animation](MI2_ROOM97_IMPORTED_ANIMATED_DIALOGUE_20261117.md).

## Finding 2: Room93 ENCD initializes actor-position lighting and rebuilds the selected logical instance

Room93 `ENCD` source body starts `0x7676AE`, length **215 bytes, 39 aligned instructions, all 16 branches valid**. Its initial operations are:

| PC | Meaning |
| ---: | --- |
| `0x0000` | `roomOps(fade,0x8181)` (source effect word, actual transition appearance not observed) |
| `0x0004` | `setVarRange(Var[285..290], [0,0,100,160,230,320])` |
| `0x0014` | `setVarRange(Var[291..296], [0,100,200,255,200,100])` |
| `0x001E` | start global script **49** (position-driven palette lighting) |
| `0x0021` | start local script **202** (reset 23 logical object states/classes) |
| `0x0024` | start local script **200** (apply one of eight per-logical-room configurations) |
| `0x0027–0x0063` | for logical 165,166,167, set Bit525=1 and Var508=201 |
| `0x0063–0x0090` | if Bit728 set in logical160, adjust palette and disable certain objects and script49 |
| `0x0090` | if Bit731 set, start local script **204** (random actor appearance loop) |
| `0x0098–0x00C5` | if Bit739 set and logical161..163, trigger one of global160 actor events depending on Var38 |
| `0x00C5–0x00D6` | if logical161 and Var102==88, start local206 (animated elevator-door state sequence) |

**Script ordering is critical:** in pinned ScummVM `runScript`, the new child executes nested/immediately until it yields. So the entry code's calls to 202 and 200 are source-ordered, not automatically separated by a rendered frame. Preserve PC, call depth and resulting object dirty areas.

## Finding 3: local202 reset, local200 render-specific alternative object layouts

Room93 `LSCR202` at body `0x767A90`: **262/262 bytes, 49 instructions, no branches**. First issues **23 `setState(object,0)` calls** on objects 872–894 (select members), then **23 `setClass(object,160)`** calls, then sets walkbox flags for boxes2/3 back to zero. This is a deterministic *clear-then-rebuild* operation, not an animated image sequence.

Room93 `LSCR200` at `0x767798`: **630/630 bytes, 129 instructions, all 20 branch destinations valid**. It reads `Var[4]` (current logical room), and selects different active states/classes/boxes.

| Logical room | Source examples of distinctive scene setup |
| ---: | --- |
| **160** | activates hole875, light switch876, chest891, ticket892 conditionally by ownership; hides boxes2,7,8 |
| **161** | door872 state3, door873 state2, elevator door877 state1 or3 depending on Var102, floor indicator878, plaque889, call button890 |
| **162** | door872 state2, door873 state1; **moves/draws object874 at grid (13,6)**; arrow893 |
| **163** | door872 state1, door873 state3; **moves/draws object874 at grid (17,6)**; arrow894 |
| **164** | door872 state3; **moves/draws object874 at grid (22,6)**; hides boxes3/9 |
| **165** | door872 state1, door873 state3; different group of stored object-image indicators |
| **166** | door872 state3, door873 state2; different group of indicator images |
| **167** | door872 state2, door873 state1; different group of indicator images |

ScummVM v5 `drawObject` explicit X/Y coordinates use **8-pixel units**, so the three source `drawObject(874,at ...)` cases imply native positions **(104,48), (136,48), (176,48)** before any further camera or layering transformation. This is a direct example of script-driven *positioned overlay art* on a reused source background.

Original Room93 `OBCD/OBNA` names include `elevator door` (877), `floor indicator` (878), `call button` (890), `light switch` (876), two `door` objects (872,873), `plaque` (889), `ticket` (892), `smashed-up treasure chest` (891), and `arrow` (893/894). These labels are archive strings, not manually inferred rendered images.

## Finding 4: both door handlers define a shared-resource eight-room traversal

Object872 and object873 `OBCD/VERB` handler255:
- object872 handler from `0x766F75`, **185/185 bytes, 32 instructions, 18/18 branches valid**;
- object873 handler from `0x76706D`, **185/185 bytes, 32 instructions, 18/18 valid**.

They inspect `Var4` (logical current room). Routine transitions use `loadRoomWithEgo` specifying destination logical room, target door object and native actor coordinates, and in some cases check actor3's current room first. Object872 mostly navigates toward lower logical IDs; object873 toward higher IDs:

| Trigger state | Source-defined result |
| --- | --- |
| Object872 handler in logical161–164 | load logical160–163 respectively, using door873 and (263,120), if actor3 not already in current logical room |
| Object873 handler in logical160–163 | load logical161–164 respectively, using door872 and (46,120), if actor3 not already in current logical room |
| Object872 handler in logical165 | **Bit93=1**; start global124 with [165,37]; `loadRoomWithEgo(object371,37, -1,-1)` |
| Object873 handler in logical167 | **Bit93=0**; start global124 with [165,35]; `loadRoomWithEgo(object360,35,-1,-1)` |
| Object872 handler in logical166–167 | load logical165–166 respectively |
| Object873 handler in logical165–166 | load logical166–167 respectively |

This provides source-coded *additional writers of Bit93*, beyond Room37 ENCD and Room26 local201/202, and explains why Room26's two-map walkbox sets can be affected by choices made in this virtual-room corridor. **Natural gameplay reachability remains unverified.**

## Finding 5: native scripted animation and random movement within shared room

Other fully walked Room93 original scripts:
- `EXCD` at `0x76768B`, 27/27 bytes, seven instructions: resets global Var508, Var33 and four walkbox flags.
- `LSCR201` at `0x767A17`, 112/112 bytes, 19 instructions, 2 valid branches: source-defined three-round random position and script94 synchronization, dialogue at end; actual displayed outcome unknown.
- `LSCR204` at `0x767BD9`, 179/179 bytes, **37 instructions, 16 valid branches**: `delay(60)` polling loop gated by Bit731 and random values; chooses door872/873 and X value 46/263, uses ego X to avoid/correct placement, calls **global154** with door/X/120 parameters, then variable delay and repeats.
- `LSCR205` at `0x767C95`, 42/42 bytes, 12 instructions, 5 branches: actor-independent image-state transitions for **elevator door877**, then starts local206.
- `LSCR206` at `0x767CC8`, 14/14 bytes, five instructions: `delay(300)`, set elevator door877 state2, yield, state1; no claim of 300 rendered frames.

[Source-only global49 dynamic lighting model](MI2_ROOM93_ACTOR_POSITION_PALETTE_LIGHTING_20261117.md) and [global154 roaming actor3/LeChuck](MI2_ROOM93_LECHUCK_RANDOM_MOVEMENT_20261117.md) are separate documents. They respectively explain *position-dependent palette RGB updates* and *costume-driven environmental actor motion*.

## Important separation for ScummBucket

Resource identity `source_room=93`, logical instance `logical_room=160..167`, currently loaded `_roomResource`, current script identity/PC, actor positions, runtime `Bit93`, object ownership, object states/classes and walkbox masks must be separately tracked. A P1 archive index should register the 24 well-formed pseudo-room aliases and retain confirmation level; a P4 scene compositor should not duplicate a source background or assume eight variants are source files.

**Future gate:** official `descumm -5 -o` for SCRP1 mapping and all Room93 tagged scripts, ScummVM instrumented traversal for logical160–167 with original room/resource IDs, source bounds/overlays, actor+palette hashes, object877 timing, and independent native indexed framebuffer parity. This report is static research only.
