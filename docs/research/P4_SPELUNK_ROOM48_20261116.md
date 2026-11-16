# P4 spelunking — Room 48: parent-gated scenery and verb-triggered scripts

**16 November 2026 · Static archive and ScummVM source research. No
native Windows game run, test acceptance, or indexed frame comparison.**
[Structured evidence register](../validation/P4_SPELUNK_ROOM48_20261116.json).

## Room and mechanism split

The original DOS VGA MI2 archive identifies Room 48 as the **antique
dealer's shop** through original `OBNA` short names. Its `ROOM`
chunk starts at **4,134,176** (58,391 bytes); it has **41 paired OBCD
and OBIM records** but only **seven image-bearing objects** (nine stored
IMxx states total). The other **34** objects have zero stored IMxx
states: they should not be fed to the image-state decoder as though
frames were missing. The room has **18 local LSCRs**, one ENCD and one EXCD.
All 41 objects have nonempty `VERB` chunks, unlike Room 44's 20
noninteractive object headers. The original `CYCL` chunk has **zero**
active records (only its terminator).

Game resource hashes:
- MONKEY2.000 `cde7aa8980317e3a750fbb3b49884cdddaf1ff3d4231a0c840b22cceed9033f1`
- MONKEY2.001 `ad045372e0d49626503bb50fca29a687ec8e01ef75d9b8bca702a366d143819e`

### The previously unresolved parent reference

| Field | Source object 517 | Source object 515 |
|---|---|---|
| `OBNA` noun | parrot chow | sign |
| OBCD ordinal within ROOM | **19** | **20** |
| Original bounds | (240,32) 24×32 | (240,32) 24×32 |
| Declared stored `IMxx` states | 1 | 1 |
| OBCD offset | 4,176,758 | 4,177,144 |
| OBIM offset | 4,169,640 | 4,169,100 |
| Raw v5 parent index | **20** | 0 |
| Raw v5 CDHD flags | **0x80** | 0 |

The v5 flags `0x80` resolve to parentstate **1** in ScummVM
[`resetRoomObject`](https://github.com/scummvm/scummvm/blob/v2026.4.0/engines/scumm/object.cpp#L1074-L1163).
The engine's
[`resetRoomObjects`](https://github.com/scummvm/scummvm/blob/v2026.4.0/engines/scumm/object.cpp#L832-L902)
iterates source OBCD order using the first free local slot; a clean
room with no preexisting nonempty slots would therefore assign the
20th OBCD (sign 515) to slot 20. **This relationship is strongly
supported by the original archive, but the actual slot-20 mapping
must still be confirmed from a live room object table.**

The
[`drawRoomObject` parent gate](https://github.com/scummvm/scummvm/blob/v2026.4.0/engines/scumm/object.cpp#L600-L618)
requires the immediate parent state's low nibble to equal 1 before
object 517 can draw normally. For a clean sequential load,
[`drawRoomObjects`](https://github.com/scummvm/scummvm/blob/v2026.4.0/engines/scumm/object.cpp#L620-L645)
would visit slot 20 (the sign) before slot 19 (the parrot-chow child),
so the child can overlay the parent if both are enabled. The
independent queued draw path and runtime placement could differ.
**Not observed:** those objects' actual state at a captured frame,
visibility or final pixels.

This is **parent-gated layered scenery**, not evidence that two
single-state object resources should be exported as two animation frames.

## From hook verb handler to local scripts

Room 48's `hook` (object **516**, source ordinal **36**) has an OBCD
`VERB` chunk at **4,179,225** (199 bytes). Its event **0x07**
pointer value is **37**. Per the ScummVM Tools v5 `descumm`
verb-header format, the pointer is relative to the **VERB chunk
start**, producing entrypoint **4,179,262**, not relative to the
payload start. The next conditional sequence contains two possible
`startScript(201)` byte runs at **4,179,269** and **4,179,282**.
They occur inside that verb handler, not merely in arbitrary room
text. Event **0x08** has a separate entry at **4,179,255**, with
a script-209-shaped call. The independent disassembler has **not**
been run here, so reachability and instruction alignment remain open.

A bounded local-source path is visible:

```text
Room 48 object 516 VERB event 0x07
  -> [condition-dependent] local script 201
       -> setState(517,1)
       -> setState(515,1)
       -> delay(20)       [engine script units, not milliseconds]
       -> local script 202
            -> [conditional actor/cutscene activity]
            -> waitForActor(8)   [candidate control]
            -> setState(517,1)
            -> setState(515,1)
            -> local script 214
```

Original relevant source offsets:

| Source | Opcode lead | Offset |
|---|---|---:|
| ENCD | `setState(517,0)` candidate | 4,180,234 |
| LSCR 201 | `setState(517,1)` | 4,180,325 |
| LSCR 201 | `setState(515,1)` | 4,180,336 |
| LSCR 201 | `delay(20)` | 4,180,340 |
| LSCR 201 | `startScript(202)` | 4,180,349 |
| LSCR 202 | `waitForActor(8)` candidate | 4,180,434 |
| LSCR 202 | `setState(517,1)` | 4,180,440 |
| LSCR 202 | `setState(515,1)` | 4,180,451 |
| LSCR 202 | `startScript(214)` | 4,180,471 |
| LSCR 211 | `setState(517,0)` unaligned lead | 4,189,731 |

Script 201 chunk: 4,180,301 (52 bytes),
SHA-256 `c198be0ecb77050cc6bf517b0f353a437b70922c92c6931de1224c3fdda3c6b9`.
Script 202 chunk: 4,180,353 (122 bytes),
SHA-256 `a1349b1625eca8a17a12e2db774542e674cfd7a674ead8e3a026d3f0ccacbd6a`.
Script 211 chunk: 4,187,749 (2,433 bytes),
SHA-256 `551e14befbc33894a4d081540f38e35bbd8988d51a2351a833924eacb9659c4e`.

The ENCD also has local script-start patterns for scripts
205 and 203 at offsets **4,180,198** and **4,180,201**, and a
conditional-looking call to 202 at **4,180,238**. This means the
source contains *several possible entries* to the later actor/state
sequence. No specific player-triggered path has been proven executed.

## Independent actor-script loops also exist

The sign/parrot-chow state mechanism should not cause us to dismiss
Room 48 as visually static. Other local scripts have source tail
back-jumps that target their respective body starts:

| Script | Body start | Last relative jump | Target | Preceding `breakHere` |
|---:|---:|---:|---:|---:|
| 210 | 4,187,682 | 4,187,745 | 4,187,682 | 4,187,744 |
| 213 | 4,191,689 | 4,191,705 | 4,191,689 | 4,191,704 |
| 214 | 4,191,718 | 4,191,806 | 4,191,718 | 4,191,805 |

Source bytes also include `o5_animateActor`-shaped commands
for actors **9** (script 210) and **7/8** (scripts 213/214).
These are strong **actor animation candidate** mechanisms; the
current archive inspection does not establish the actors' live COSTs,
whether those paths execute on entry, or how often their states change.

## Interpretation and next verification gates

**Compared with Room 44:** this room is dominated by object-verb
handlers, actor interactions and conditional rendering. The object
515/517 pair should be represented as explicit source layers with a
parent gate and state changes, *not* an invented animation loop.

**Static next:**
1. Independently disassemble hook 516's `VERB` event 0x07, LSCR
   201, 202, 211, and ENCD. Confirm actual instruction boundaries
   and call graph; do not blindly trust a raw opcode occurrence.
2. Determine the conditions permitting the hook caller and all
   script-211 resets, including any global script calls.
3. Check whether scripts 210/213/214 are started under ordinary
   gameplay or remain dormant; classify actor COSTs separately.

**Later Windows native capture:** confirm room-local slot 20, parent
state, child's state/visibility and actual draw queue. Record
script-slot/PC, `setState` mutations, actor 8 wait, source masks and
indexed frontbuffer. A successful script-level or image decode does
not automatically validate the reconstructed view.

**Evidence status:** source structure + ScummVM opcode semantics,
not independent descumm alignment or runtime behavior. No original
script byte listings, dialogue, graphics, game data, third-party
source, binaries, captures or synthetic playback in Git.
