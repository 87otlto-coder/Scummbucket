# MI2 Room19 imports two complete banks of animated effects: physical Rooms104–107 (17 November 2026)

**Evidence and limits:** Original DOS VGA MONKEY2.000 and MONKEY2.001 read-only, MONKEY2.001 stored-byte SHA-256 ad045372e0d49626503bb50fca29a687ec8e01ef75d9b8bca702a366d143819e. Source script contents independently walked with private narrow v5 opcode parser, primary semantics checked against [ScummVM v2026.4.0 script_v5.cpp](https://github.com/scummvm/scummvm/blob/v2026.4.0/engines/scumm/script_v5.cpp) and [object.cpp::loadFlObject](https://github.com/scummvm/scummvm/blob/v2026.4.0/engines/scumm/object.cpp). **No official descumm crosscheck, executed game sequence, framebuffer or original interpreter parity.** Original resource bytes not committed.

## Finding: all 20 source bank objects appear in Room19's scripted cutscenes

Four source rooms with unusually small **8×8 RMHD** have 20 paired OBCD+OBIM objects and **116 stored IMxx states**, all referenced by explicit original SO_LOAD_OBJECT opcodes in scripts stored with Room19:

| Bank physical room | Object IDs (continuous) | Paired objects | Stored source image states | Fully walked import callers |
| ---: | --- | ---: | ---: | --- |
| **104** | 1134–1136 | 3 | **28** | global SCRP99 |
| **105** | 1137–1142 | 6 | **53** | Room19 LSCR203 and LSCR205 |
| **106** | 1143–1145 | 3 | **20** | global SCRP99 |
| **107** | 1146–1153 | 8 | **15** | Room19 LSCR204 |
| **Total** | **1134–1153** | **20** | **116** | **20/20 IDs imported** |

All four tiny rooms have terminating one-byte ENCD and EXCD, just as Rooms99–102 (8×200) do. The tiny RMIM itself is not the imported sprite: ScummVM loadFlObject copies original paired **OBCD + OBIM**, enabling scripts to draw the states in Room19. The exact purpose of the bank RMIM placeholders remains unresolved.

Room19's own original OBCD object names include multiple **“coffin”**, **“map piece”** and **“key”** entries. These are source labels only; no claim that all foreign images depict a particular object is made.

### Full original script decoding census

| Source script | Original body bytes | Instructions | Relative branch targets valid | Original foreign source loads | Draw calls | Explicit breakHere opcodes |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| **Room19 ENCD** | **55/55** | 12 | 1/1 | 0 | 0 | 0 |
| **Room19 LSCR203** | **5561/5561** | 597 | **128/128** | 5 (Room105) | 28 | 49 |
| **Room19 LSCR204** | **375/375** | 101 | 4/4 | 8 (Room107) | 15 | 36 |
| **Room19 LSCR205** | **59/59** | 11 | 2/2 | 1 (Room105) | 2 | 1 source site, recurring |
| **Room19 LSCR206** | **29/29** | 9 | 3/3 | 0 | 1 | 1 source site, recurring |
| **Global SCRP99** (stored Room19) | **919/919** | 182 | **27/27** | 6 (Rooms104/106) | 16 | 44 |

Counts describe static original instructions (some are in mutually exclusive branches) and do not predict exact visible frame counts or duration. The entire very long 5,561-byte LSCR203 was instruction-aligned, but its full state machine has not been exhaustively interpreted for all reachable branches.

## Source-coded entry and branch links

**Room19 ENCD** fully aligns to 55 bytes / 12 instructions. On **Bit602==1**, it clears Bit602, writes **Bit555=1**, and **starts global script99**. This is a verified source-coded entry caller, not proof that a normal save enters Room19 with Bit602 set.

Global99 starts by testing **Bit366**. If nonzero it prints a line and stops; otherwise it begins a cutscene and, depending on Bit555 and several case distinctions of **Var522 (182..186)**, proceeds through actor/camera/sound and image branches. It may start global98 and wait for a state change before continuing. The main visual part executes:

- **SO_LOAD_OBJECT from Room104:** all IDs **1134,1135,1136**, with multiple drawn image states and source-encoded loops.
- **SO_LOAD_OBJECT from Room106:** all IDs **1143,1144,1145**, also drawn in multiple image states.
- Camera pan (source `panCameraTo`), sound **183**, eventual state **object199=1**, and **startScript(140,[18,19])** plus **startScript(203)**. Thus source code can begin the much longer local Room19 cutscene after the bank104/106 effects.

### Room19 LSCR203 controls source bank105

The fully aligned 5561-byte script includes source imports **1140,1141,1138,1139,1142** from Room105, extensive animation-image draws and 49 explicit yield instructions. Some original image state operands reach **state15** on object1139, and object1138 reaches at least state14; they cannot be treated as one-frame props.

Later its script source (PC0x1591) starts **local204 with the literal argument Bit586**, after which it yields and polls **isScriptRunning(204)** until the child terminates. The same original script contains a direct **write Bit586=1 at PC0x13A0** on one path. This is a stronger local call-chain than a raw pattern match; exact natural runtime branch is unobserved.

### Room19 LSCR204 controls source bank107, two variants

This script's **Local0** selects two mutually exclusive branches:
- **Local0=0:** loads bank107 objects **1147,1148**, draws five source image states across the two components, **8 explicit yields** in branch, then sets both state0 and changes their owner state through source-coded cleanup.
- **Local0=1:** loads **1146,1149,1150,1151,1152,1153**, draws **10 source state/position commands** with **23 explicit yields** in branch, then sets all six states0 and performs owner cleanup.
- Both paths start with one source breakHere and finish with four shared yields after **startScript(140,[19,18])**, environment object states changes, sound cleanup and stop. If Local0 has another value, neither branch is exercised; the shared ending remains.
- Both branches are finite and have different source sound triggers (**184** vs **185**). These are scripted multi-component effects, NOT one generic animation loop.

### Room19 LSCR205/206: speech-gated repeating animation from Room105

- LSCR205 imports bank105 object **1137**, draws it at 8-pixel grid (9,2), and defines a **nine-element local state table [1,2,3,2,3,4,5,3,4]**. It iterates the array, drawing object1137's selected state, yielding once, and repeating.
- LSCR206 starts/stops **local205** in response to the current speaking actor being **actor7** (VAR_TALK_ACTOR Var25); at stop it restores object1137 state1. This is a source-defined *dialogue-driven animation* loop, distinct from the finite special effects in local204.

The image decoder must handle source-image state counts and transparent pixels, not merely import a default FLOB state. Compositor must honor runtime state0 and object ownership cleanup.

## Connection with Rooms99–102

This is **a separate bank family** from the 8×200 Rooms99–102 described in [the 13 pseudo-room cross-resource compositions](MI2_PSEUDOROOM_CROSSROOM_OBJECT_BANKS_20261117.md). Across both families, **59 original source-bank object IDs (39 + 20)** are demonstrably imported using v5 SO_LOAD_OBJECT. These are stored in **eight tiny physical room resources** but drawn in other rooms or pseudoroom instances.

### Future verification

1. Official descumm -5 -o for tagged global99, Room19 ENCD and locals203/204/205/206; retain original hashes and byte-offset/operand maps.
2. In pinned ScummVM, capture Room19 entry with Bit602/555/366/586 and Var522 states, and record every FLOB import, image-state change, owner transition, sound/camera event, script PC and indexed front/back pixel difference.
3. Isolate short vs long local204 effects, repeat local205's 9-state loop with actor7 speaking/not speaking; verify source image pixels/transparency and exact runtime timing.
4. Do not treat unused/unsupported branches or source-level loops as observed gameplay. Keep all original game art and captures private under FIXTURE; research/docs in SOURCE.

**Status:** archive-derived, all above script opcode boundaries aligned and pinned ScummVM semantics; no actual runtime or visual fidelity acceptance.
