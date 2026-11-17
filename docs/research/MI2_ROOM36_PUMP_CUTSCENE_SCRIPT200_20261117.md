# MI2 Room36 pump cutscene — full source-aligned script 200 (17 November 2026)

**Evidence class:** Read-only original DOS VGA `MONKEY2.001`, SHA256 `ad045372e0d49626503bb50fca29a687ec8e01ef75d9b8bca702a366d143819e`. Private narrow opcode walker inspected **every byte of local script 200** (body from decoded file offset `0x2BFB48`, length **279** bytes), consuming **279/279**, **188 instructions**, including **158 explicit `breakHere` opcodes**. All **six** relative control destinations, including the cutscene override escape target, are instruction boundaries. Decoding was cross-checked with pinned ScummVM v2026.4.0 script semantics. **No full descumm comparison, gameplay execution, timer trace, actor/costume framebuffer or P4 acceptance was performed.** No resource bytes committed.

## Call-chain evidence — the pump isn't a static two-state sprite

Room36 object **366** is the named `pump`. The paired OBCD VERB table directs:
- **verb7** to the now fully aligned 74-byte handler described in [cross-room notes](MI2_ROOMS35_36_37_CROSSROOM_CYCL_STATE_20261117.md), which conditionally toggles Bit92 for Local[0]=0; for Local[0]=89 it delegates to verb24 using `doSentence`.
- **verb24** to a four-byte handler at decoded offset `0x2BFA75`: `startScript(200)` followed by `stopObjectCode`.

This establishes an *archive-coded* interaction-to-cutscene call chain, conditional on the game's verb dispatch. The verb24 handler and script200 source are not proof that any particular user action invokes them in a particular state.

## Fully aligned script200 event model

| Bytecode PC | Instruction / script-controlled action | Explicit script yields after action |
| --- | --- | ---: |
| 0x000 | `beginCutscene([1])` | — |
| 0x005 | `beginOverride` with skip target **0x0EF** | — |
| 0x00A | print actor255, one-space text | — |
| 0x00F | Ego `actorOps`: costume **69**, sound **60** | — |
| 0x017 | `animateActor(Ego, action6)` | **18** |
| 0x02D | If **Bit763 nonzero**, skip to PC0x097; else set Bit763=1 | — |
| 0x037 | `animateActor(Ego, action7)` | **18** |
| 0x04D | `animateActor(Ego, action8)` | **29** |
| 0x06E | `animateActor(Ego, action9)` | **13** |
| 0x07F | `animateActor(Ego, action10)` | **20** |
| 0x097 | `animateActor(Ego, action11)` | **4** |
| 0x09F | `animateActor(Ego, action12)` | **40** |
| 0x0CB | **If Bit92 nonzero, start sound35; if Bit92 zero, stop sound35** | — |
| 0x0D7 | `animateActor(Ego, action13)` | **5** |
| 0x0E0 | `animateActor(Ego, action14)` | **11** |
| 0x0EF | `endOverride()`; costume **1**, sound **0**, then `animateActor(Ego, action3)` | — |
| 0x0FD | **If Bit92 nonzero**, set `Bit92=0` and `startScript(202)`; otherwise set **Bit92=1** and `startScript(201)` | — |
| 0x115 | `endCutscene`; terminate | — |

The uninterrupted nominal **number of script-yield opcodes** executed is:
- **158 yields** if Bit763 was initially clear (then set).
- **78 yields** if Bit763 was already set (skips 18+29+13+20 = **80**).
- **Fewer** if player triggers the cutscene override. These are *source opcode counts, not measured displayed frames*. Actor costume actions themselves may contain additional internal costume frame sequencing.

### Why override processing is important

The raw override instruction contains embedded `jumpRelative` operand but **ScummVM's `ScummEngine::beginOverride()` consumes that jump without executing it in ordinary play**. When the override is used for skipping, control resumes at **PC 0x0EF**, not at script termination. That target is exactly the cleanup and state-transition tail: restore costume, toggle Bit92, start follow-up local 201 or 202, then `endCutscene`. 

Therefore **a skipped cutscene should still mutate the environment**. A frame exporter must distinguish normal long/short presentation and skip-to-final-state; stopping playback before the mutation would be wrong. Do not assume the original DOS interpreter's override timing has been directly observed; this is pinned ScummVM semantics plus source-aligned script offsets.

### Environmental state effect

- Initial **Bit92=1**: after the timed animation sequence, sound35 is started, Bit92 becomes **0**, and Room36 script202 is started.
- Initial **Bit92=0**: sound35 is stopped, Bit92 becomes **1**, and Room36 script201 is started.
- Because `o5_startScript` uses `runScriptNested`, the newly started child can execute immediately before the parent finishes `endCutscene`. **This means independent child-script phases must be included in timeline events, not assumed to start a display frame later.**
- Room35's ENCD starts *its own* local script202 (different room-local script number, whose stored animation is object364 states1–8) only when Bit92 is zero. Room36 script202 here is a **different resource**. Resource identity must be `(room_id, local_script_id)`, not `script_id` alone.

## Implementation consequences

A faithful environment animation representation for this case must preserve:
- Room source/edition and full local-script identity;
- persistent **Bit92** and **Bit763**, plus entry/exit state;
- a timestamped sequence of nine costume actions (long path) or five (short path), explicit `breakHere` counts, and any engine timer delta variations;
- sound34/35 changes and costume69/sound60 changes;
- after-cutscene call to Room36 script201/202 and subsequent object/room effects;
- skip/override control flow;
- cross-room reactions of Room35 and Room36 entry scripts;
- current palette-cycle settings, which Room36 ENCD gates with `VAR_VIDEOMODE==19` (VGA) and Bit92.

No rendered animation sequence was inferred or generated. All game bytes remain private and the original archive is unchanged.

## References and next gates

- [ScummVM v2026.4.0 script_v5.cpp](https://github.com/scummvm/scummvm/blob/v2026.4.0/engines/scumm/script_v5.cpp): `o5_cutscene`, `o5_beginOverride`, `o5_animateActor`, `o5_breakHere`, `o5_actorOps`, `o5_print`, `o5_startScript`.
- [ScummVM v2026.4.0 script.cpp](https://github.com/scummvm/scummvm/blob/v2026.4.0/engines/scumm/script.cpp): `beginOverride` consumes the following jump and records escape target; `runScriptNested` child execution and scheduler mechanics.
- [Room35–37 research](MI2_ROOMS35_36_37_CROSSROOM_CYCL_STATE_20261117.md).
- **Next source-only:** decode the complete Room36 local scripts201 (95 bytes) and 202 (124 bytes) to determine whether they alter live palette, object state, actor positioning, traversal or screen effects. Do not confuse their numeric IDs with Room35 script201/202.
- **Future runtime:** capture real pump activation in both Bit92 states with Bit763 initially zero/set; log script PC, per-yield clock, actor costume sequence, sound state, visible palette, script201/202 operations and post-transition native indexed framebuffer. Compare skip path separately.

**Status:** fully aligned original archive script + pinned ScummVM semantic interpretation, **not** verified natural gameplay or pixel-perfect scene rendering.
