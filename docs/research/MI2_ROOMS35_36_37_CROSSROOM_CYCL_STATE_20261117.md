# MI2 Room 35–37 cross-room environmental animation state (17 November 2026)

**Evidence:** Read-only original DOS VGA `MONKEY2.001` (`SHA-256 ad045372e0d49626503bb50fca29a687ec8e01ef75d9b8bca702a366d143819e`) decoded by a *private narrow v5 instruction walker*, checked against pinned ScummVM v2026.4.0 source. **No runtime, original interpreter, full independent descumm comparison or framebuffer acceptance.** Do not commit original game bytes, extracted art or audio. Source locations below refer to XOR-0x69-decoded member; offsets unchanged by XOR.

**Major result:** Room 35's eight-state image loop is conditional, Room 36's five palette cycles are **script-controlled**, and Room 37 plus an interactive pump in Room 36 manipulate a shared persistent `Bit[92]`. These are three interdependent environment states, not three autonomous animated GIFs.

## 1. Independently instruction-aligned entry/exit paths

| Room / resource | Tagged chunk absolute offset | Body length | Complete narrow walk | All branches aligned |
| --- | ---: | ---: | ---: | --- |
| 35 `ENCD` | `0x2B2516` (2,827,542) | 160 bytes | 31 instructions | Yes, 4 relative branches |
| 35 `EXCD` | `0x2B24FD` | 17 bytes | 4 instructions | Yes |
| 36 `ENCD` | `0x2BFAE5` | 72 bytes | 18 instructions | Yes, 4 branches |
| 36 `EXCD` | `0x2BFAD3` | 10 bytes | 3 instructions | Yes |
| 37 `ENCD` | `0x2CAF10` | 42 bytes | 10 instructions | Yes, 1 branch |

Source-derived algorithm outcomes below are conditional on the original input variables / verb triggers, and do **not** prove gameplay always reaches those instructions.

### Room 35 entry, bytecode PC 0x000–0x09F

- Stop sound 35; set Ego actor (`Var[1]`) walk speed **(12,4)** using `o5_actorOps`.
- If `Bit[567]` is nonzero, **set `Bit[92] = 1`**; otherwise leave `Bit[92]` unchanged. `Bit[567]` is not proved to be the only writer to this state.
- If `Bit[92]` **set**: stop sound 34; set object 362,361,365 states to **1**; set their class-32 flag using encoded class `160 = 0x80|32`; clear object360's class32 via raw class `32`; set box10 flags=1 and box11 flags=0; **jump around** the `startScript(202)` caller.
- If `Bit[92]` **clear**: start sound 34; set objects 362,361,365 states to **0**; clear their class32; set class32 on object360; set box10 and box11 flags **128**; **execute `startScript(202)` at entry-script PC 0x07F**.
- Both branches join at PC 0x082, with class query for object360 raw `147=0x80|19`. If the class predicate succeeds, the script renames object360 to “gaping hole”; otherwise it bypasses that rename. Both eventually set `Var[160] = 0` and terminate.
- **Source-backed correction to 16 November hypothesis:** local script202 does indeed contain the deterministic object364 state 1→8 loop with one `breakHere` after each state, but the *room entry script only starts it in the Bit92-clear branch*. Current static reconstruction must model this condition, not schedule the loop unconditionally. Other possible callers to script202 have not been exhaustively excluded.

### Room 35 exit, 17 bytes

Conditional on `Var[160] != 36`, stop sound34; then restore Ego walk speed to **(8,2)**; terminate. This confirms speed change has an intended exit reset, not necessarily a costume animation change. Interpret `Var[160]` as an observed script variable used for transition gating; its complete semantic role is not established.

### Room 36 entry, bytecode PC 0x000–0x047

- Stop sound34.
- Test `Bit[92] == 0`.
- On **Bit92 clear**: start sound35; **if `Var[49] == 19`**, issue five `o5_roomOps(SO_CYCLE_SPEED)` commands for cycles **1..5** with speed arguments **33,32,35,21,20** respectively; then jump to common exit.
- On **Bit92 set**: do not start sound35; **if `Var[49] == 19`**, set all cycles **1..5** speed arguments **0**, disabling them in ScummVM's `cyclePalette` implementation; then common exit.
- Both paths set `Var[160] = 0` and terminate.
- A zero speed parameter yields `_colorCycle[a-1].delay = 0`. A nonzero value yields `delay = 0x4000 / (speed * 0x4C)`, integer division, per pinned `script_v5.cpp::o5_roomOps`.
- **`Var[49]` is definitively `VAR_VIDEOMODE` for ScummVM v5**, not an unidentified game-state variable: `vars.cpp::ScummEngine::setupScummVars` maps `VAR_VIDEOMODE=49`; `setVideoModeVarToCurrentConfig` assigns **19** for default VGA, **13** for EGA (<v6), different numbers for Amiga and other modes. Thus Room36 explicitly **gates these palette commands on VGA video mode**. It is not safe to assume that `Var49==19` is always true in alternate render modes.

**Room36 raw CYCL source vs script-overridden delay**:

| CYCL | Source range | Source stored rate | Initial delay `16384/rate` | VGA enabled speed arg | Effective scripted delay `16384/(arg*76)` | VGA disabled delay |
| --- | --- | ---: | ---: | ---: | ---: | ---: |
| 1 | 160–167 | 2611 | 6 | 33 | 6 | 0 |
| 2 | 168–175 | 2534 | 6 | 32 | 6 | 0 |
| 3 | 176–183 | 2688 | 6 | 35 | 6 | 0 |
| 4 | 184–187 | 1689 | 9 | 21 | **10** | 0 |
| 5 | 188–191 | 1536 | 10 | 20 | 10 | 0 |

These are integer **engine timer-unit** thresholds, not physical frame counts. Room36 combines five palette cycles with nine transparency-aware SMAP background strips and ZP plane data per the previous `MI2_P2_TRANSPARENT_BACKGROUND_STRIPS_20261116.md`.

### Room36 exit, 10 bytes

If `Var[160] != 35`, stop sound35. Otherwise retain it across that exit. This mirrors Room35's exit conditional on next room36. The actual sound mixing / audible transition requires a runtime trace.

### Room37 entry, 42 bytes

The fully aligned first operations set:
- `Var[578]=128`;
- **`Bit[92]=1`**;
- `Bit[525]=1`;
- `Bit[93]=1`.

Then, conditional on `Bit[51]`, it can start local script203 and clear Bit51. Thereafter start local script202, write `Var[32]=201`, terminate. The first Bit92 write is unconditional in this entry code, but actual entry to Room37 still requires a gameplay/cutscene path.

## 2. Object366 (pump) verb7 is fully aligned and conditionally toggles Bit92

The `pump` is paired object **366** in Room36 (`CDHD obj_id 366`, `OBNA = pump`). Its `OBCD/VERB` chunk begins at decoded offset `0x2BF9F1`. Verb table maps **verb7** to the handler starting at **`0x2BFA2B`** (offset relative to the VERB block header, not the payload). This handler runs to the start of the subsequent verb24 handler at `0x2BFA75`; length **74 bytes**, **11 narrow-walker instructions consumed**, all **six** signed relative branch destinations land on valid instructions or the terminus.

Derived control flow:

| Body PC | Conditional action |
| --- | --- |
| `0x00` | If **`Local[0] == 0`**, jump to the toggle block `0x35` |
| `0x05` | Otherwise, if **`Local[0] != 89`**, jump to a short refusal message `0x15` |
| `0x0C` | When **`Local[0] == 89`**, invoke `doSentence(verb24, Var[7], object0)`, then exit |
| `0x15` | Otherwise print a refusal message, then exit |
| `0x35` | If **`Bit[92] == 1`**, write `Bit[92]=0` |
| `0x44` | If **`Bit[92] != 1`**, write `Bit[92]=1` |
| `0x49` | Stop object script |

**Source-confirmed control dependency:** This interactive verb handler **toggles Bit92 only when invoked with local argument `Local[0]=0`**. Other local values either delegate to verb24 or display a message; they do not toggle this bit through this handler. The handler's external caller arguments, expected normal interaction and graphical response have **not** been observed. Do not claim every pump click immediately flips the scene or calls the handler with `Local[0]=0`.

Source bytecode operands were interpreted per [ScummVM v5 script and object script execution](https://github.com/scummvm/scummvm/blob/v2026.4.0/engines/scumm/script_v5.cpp) and [SCUMM variable addressing](https://github.com/scummvm/scummvm/blob/v2026.4.0/engines/scumm/script.cpp); `0x4000` variable reference is a local variable, not global Var0. `Var[7]` in delegated `doSentence` is kept as a literal global variable reference pending its full gameplay meaning.

The relationship now has **three independent source-aligned links**: Room35 ENCD responds to Bit92; Room36 pump verb7 can toggle Bit92 and Room36 ENCD changes five cycle speeds in VGA; Room37 ENCD sets Bit92=1. The actual causal gameplay path across those entry/verb triggers still requires a captured sequence.

## 3. Engine interpretation and architectural consequence

Pinned original-reference implementation:
- [ScummVM v2026.4.0 script_v5.cpp](https://github.com/scummvm/scummvm/blob/v2026.4.0/engines/scumm/script_v5.cpp): `o5_actorOps`, `o5_notEqualZero`, `o5_equalZero`, `o5_isEqual`, `o5_roomOps` case 16, `o5_setClass`, `o5_setState`, `o5_startScript`, `o5_stopSound`.
- [vars.cpp](https://github.com/scummvm/scummvm/blob/v2026.4.0/engines/scumm/vars.cpp): `VAR_VIDEOMODE=49`, `VAR_EGO=1`, video-mode assignment 19 VGA / 13 EGA.
- [palette.cpp](https://github.com/scummvm/scummvm/blob/v2026.4.0/engines/scumm/palette.cpp): `initCycl` and `cyclePalette` threshold and delay-zero disabling.

**P4 design requirement:** Represent *scenery configuration as state-dependent and cross-room*, not merely `room_id → all CYCL records + looping OBIM frames`. Dependencies include bit/global variables, script entry/exit, video mode, active sounds, actor movement parameters, object classes/states, walkbox flags, which child scripts were started, and palette-speed overrides. An inventory of all stored cycles is not the same as a list of active cycles.

**Suggested focused future trace:** capture Room35 and Room36 entries under both Bit92 values and VGA, logging var49, var160, Bit567, 92, 525, 93, object360/361/362/364/365 states/classes, box10/11 flags, script202 status, sounds34/35, all five Room36 cycle delays, and palette RGB hashes; then explicitly test Room36 pump handler and Room37 entry transition. The evidence should be acquired without overwriting original saves or archives.

**Research discipline:** The 160+17+72+10+42 byte lengths and full instruction alignment are source inspection, not `descumm` cross-validation or runtime observation. The pump verb7 instruction boundaries are now independently aligned, but natural-gameplay invocation and runtime effects are not observed. All original asset bytes and scratch decoders remain private.
