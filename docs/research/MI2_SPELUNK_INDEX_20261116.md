# MI2 spelunking — research index and next-evidence gates (16 November 2026)

**Project:** ScummBucket original DOS VGA `MONKEY2.000/.001`; archive resource member SHA-256 `ad045372e0d49626503bb50fca29a687ec8e01ef75d9b8bca702a366d143819e`.

**Further primary-source review:** [MI2_PRIMARY_SOURCE_CROSSCHECK_20261116.md](MI2_PRIMARY_SOURCE_CROSSCHECK_20261116.md) corroborates and qualifies earlier source-only findings.\n\n**Scope:** research-only, read-only original resource and DOS binary inspection, narrowly scoped static SCUMM v5 bytecode walking, pinned ScummVM source review. **No debugger, ScummVM gameplay, Windows acceptance tests, new engine features, or rendered-frame validation performed.** No copyrighted original game content has been committed. The source tool used for private exploration is an independent one-off research prototype, NOT a verified new ScummBucket decoder.

## Index of independently useful findings

| Document | New source-backed knowledge | Next evidence gate |
| --- | --- | --- |
| [MI2_PRIMARY_SOURCE_CROSSCHECK_20261116.md](MI2_PRIMARY_SOURCE_CROSSCHECK_20261116.md) | ScummVM v5 palette counters and 60 Hz script-unit scheduling; nested immediate scripts; same-box eviction; per-clip Z masks; descumm/GrogVM/DREAMM evidence hierarchy | Confirm Room35/81 timing with indexed traces and original interpreter comparison |
| [MI2_ROOMS35_36_37_CROSSROOM_CYCL_STATE_20261117.md](MI2_ROOMS35_36_37_CROSSROOM_CYCL_STATE_20261117.md) | Fully aligned entry/exit scripts and pump verb connect Rooms 35–37 through Bit92; Room36's five palette cycles are VGA-gated and script enabled/disabled | Verify room transitions, local pump invocation and native pixel output |
| [MI2_ROOM36_PUMP_CUTSCENE_SCRIPT200_20261117.md](MI2_ROOM36_PUMP_CUTSCENE_SCRIPT200_20261117.md) | Full 279-byte 158-yield actor cutscene; Bit763 alternate branch, cutscene skip, sound and Bit92 toggle | Capture both pump directions, palette counters and native graphics |\n| [MI2_ROOM36_SCRIPTED_PALETTE_FADES_20261117.md](MI2_ROOM36_SCRIPTED_PALETTE_FADES_20261117.md) | Full 95/124-byte Room36 scripts201/202; 40 passes of five VGA-only cycle-speed updates per fade | Capture both pump directions, palette counters and native graphics |\n| [MI2_MODE_BIT567_ROOM108_UI_20261117.md](MI2_MODE_BIT567_ROOM108_UI_20261117.md) | Identify Bit567 Regular/Easy mode; Room108's 34 image states belong to startup/protection UI, not known scenery | Align menu script and capture both difficulties |
| [MI2_ROOM26_WATERFALL_MAP_BOX_STATE_20261117.md](MI2_ROOM26_WATERFALL_MAP_BOX_STATE_20261117.md) | Source-aligned Room26 25-walkbox two-topology map with Bit93 switching; Beach/Cottage/Waterfall navigation also reads Bit92 | Capture Bit93 map variations and dispatch scripts |
| [MI2_ROOMS38_39_TELESCOPE_GLOBAL159_20261117.md](MI2_ROOMS38_39_TELESCOPE_GLOBAL159_20261117.md) | Fully align global159: telescope-on-statue, cached five-brick choice, actor and cross-room camera/image cutscene | Verify shutters/mirror state and 43-jump executable sequence |
| [MI2_ROOM39_BRICK_DIFFICULTY_REVEAL_20261117.md](MI2_ROOM39_BRICK_DIFFICULTY_REVEAL_20261117.md) | Fully align Room39 script203: selected brick and Bit755 gate success/fallback, Easy bypass | Capture brick puzzle both difficulty paths |
| [MI2_GLOBAL43_44_68_TRAPDOOR_CUTSCENE_20261117.md](MI2_GLOBAL43_44_68_TRAPDOOR_CUTSCENE_20261117.md) | Fully align global68/43/44: Room39 trapdoor to Room40 and alternate Room37 exit; actor/costume/sound sequences | Measure clip paths and Room40 object423 states |
| [MI2_ROOM40_SLIDE_AND_MAPPIECE_20261117.md](MI2_ROOM40_SLIDE_AND_MAPPIECE_20261117.md) | Fully align Room40 object423 toggle (state2→1→0 or other→1→2), source verb caller and map-piece pickup | Check Room40 visual parity, owner and inventory state |
| [MI2_ROOM36_PUMP_HISTORY_ROOM27_POSTER_20261117.md](MI2_ROOM36_PUMP_HISTORY_ROOM27_POSTER_20261117.md) | Fully aligned 1804-byte Room27 poster script links Bit763 to first-use pump cutscene history and conditional narrative | Capture first/repeat/skip pump and poster branches |
| [MI2_PSEUDOROOMS_ROOM93_SCENE_INSTANCES_20261117.md](MI2_PSEUDOROOMS_ROOM93_SCENE_INSTANCES_20261117.md) | 24 script-defined room aliases; Room93 holds eight logical instances with dynamic overlays, boxes, doors, state and animation | Verify pseudo-room mapping, instance objects, pixels |
| [MI2_ROOM93_ACTOR_POSITION_PALETTE_LIGHTING_20261117.md](MI2_ROOM93_ACTOR_POSITION_PALETTE_LIGHTING_20261117.md) | Fully aligned global49 actor-X RGB interpolation for indices192..207 with precise signed truncation | Capture dynamic palette at known X positions |
| [MI2_ROOM93_LECHUCK_RANDOM_MOVEMENT_20261117.md](MI2_ROOM93_LECHUCK_RANDOM_MOVEMENT_20261117.md) | Room93 randomized appearance script204 chains into global154 actor3/LeChuck costume77 movement | Capture random trigger and actor/costume path |
| [MI2_ROOM36_PALETTE_PHASE_PERSISTENCE_20261117.md](MI2_ROOM36_PALETTE_PHASE_PERSISTENCE_20261117.md) | Pinned ScummVM proves cycle-speed writes preserve counters/RGB phase; Room36 40-pass fade discrete delays | Capture ramp shutdown/restart and counter phase |
| [MI2_ROOM55_TALK_ACTOR_DISPATCH_20261117.md](MI2_ROOM55_TALK_ACTOR_DISPATCH_20261117.md) | Partial preliminary source-aligned speaker dispatch (now superseded by complete controller) | See complete script212 report |
| [MI2_ROOM55_SEVEN_PAIR_SPEECH_SYNC_20261117.md](MI2_ROOM55_SEVEN_PAIR_SPEECH_SYNC_20261117.md) | Exhaustive 415/415-byte 77-instruction script213 state synchronizer; seven paired objects follow speaking flags | Observe paired object pixels and Bit210 overlay |
| [MI2_ROOM55_COMPLETE_SPEAKER_CONTROLLER_20261117.md](MI2_ROOM55_COMPLETE_SPEAKER_CONTROLLER_20261117.md) | Exhaustive 590/590-byte 116-instruction script212; Var25 TALK_ACTOR, actor1–8 distance-dependent script202 modes, cleanup | Descumm comparison and speaker-sensitive native capture |
| [MI2_SPELUNK_STRUCTURE_20261116.md](MI2_SPELUNK_STRUCTURE_20261116.md) | Room 44/48/55/72/79/103 structural targets; source offsets; raw opcode candidates | Cross-check structural inventory; verify candidate opcode alignment |
| [MI2_SPELUNK_CODECS_AND_MASKS_20261116.md](MI2_SPELUNK_CODECS_AND_MASKS_20261116.md) | 1,047 stored object image states; object codec and 0–3 Z-plane coverage; rare strip modes | Source-native decode tests and engine pixels |
| [MI2_SPELUNK_EVENT_SURFACE_20261116.md](MI2_SPELUNK_EVENT_SURFACE_20261116.md) | V5 engine event phase ordering, palette changes, scripts, actor/camera movement | Real phase-stamped engine trace |
| [MI2_SPELUNK_SOUND_RESOURCES_20261116.md](MI2_SPELUNK_SOUND_RESOURCES_20261116.md) | 199 `DSOU`-linked sounds, first embedded ROL/ADL/SBL/SPK tags, three SBL sources | Complete alternative parsing, original sample decode |
| [MI2_ROOM55_STATIC_EVENT_LOOPS_20261116.md](MI2_ROOM55_STATIC_EVENT_LOOPS_20261116.md) | Eight aligned local-script bodies; 5–10-yield two-state loop; nonrepeating random 3–11 image-state variants | Authentic descumm, natural entry and measured yields |
| [MI2_ROOM55_ENTRY_CALL_GRAPH_20261116.md](MI2_ROOM55_ENTRY_CALL_GRAPH_20261116.md) | Fully aligned ENCD invokes scripts 224/200; source candidate dispatcher to loops | Align scripts 200/212 and runtime caller traces |
| [MI2_ROOM44_COMPOSITE_FACE_SCRIPT_20261116.md](MI2_ROOM44_COMPOSITE_FACE_SCRIPT_20261116.md) | Full 402-byte local script, composite object-based face gestures gated by talk/message variables | Pixel-accurate component composition and script state capture |
| [MI2_ROOM48_ACTOR_OBJECT_SEQUENCE_20261116.md](MI2_ROOM48_ACTOR_OBJECT_SEQUENCE_20261116.md) | Full 113-byte local script, actors 7/8 movement, wait, object state and class changes | Actor/costume and 3-depth-mask capture |
| [MI2_ROOM72_DYNAMIC_OBJECT_LAYOUT_20261116.md](MI2_ROOM72_DYNAMIC_OBJECT_LAYOUT_20261116.md) | Full 487-byte local script, indirect array-indexed object placement, 1–4 column layouts | Resolve array values and natural object placement |
| [MI2_ROOM103_GLOBAL_MASK_STATES_20261116.md](MI2_ROOM103_GLOBAL_MASK_STATES_20261116.md) | 18 two-state objects; second image states all opaque-black plus transparency; global script 52 candidate draws | Complete script52 descumm and black-mask compositing |
| [MI2_GLOBAL_SCRIPT_PATTERN_SURVEY_20261116.md](MI2_GLOBAL_SCRIPT_PATTERN_SURVEY_20261116.md) | 86 raw direct-object patterns in bundled global scripts across 13 rooms; high-value room108 | Verified opcode/call graph across global scripts |
| [MI2_CYCL_BACKGROUND_OBJECT_COVERAGE_20261116.md](MI2_CYCL_BACKGROUND_OBJECT_COVERAGE_20261116.md) | 127 CYCL records split: 88 BG only, 29 BG+object, 3 object only, 7 neither | Source-to-runtime palette and object layer comparison |
| [MI2_MIXED_WATER_EVENT_LOOPS_20261116.md](MI2_MIXED_WATER_EVENT_LOOPS_20261116.md) | Room24 random state1–3 with yields + 8 CYCL; Room35 sequential state1–8 + 2 CYCL; Room81 random state1–3 + delay18 + 7 CYCL; Room51 finite transitions + 12 CYCL | Descumm alignment, natural entry and timing trace |
| [MI2_P2_TRANSPARENT_BACKGROUND_STRIPS_20261116.md](MI2_P2_TRANSPARENT_BACKGROUND_STRIPS_20261116.md) | 60 transparency-aware RMIM SMAP strips in ten rooms; Room49 has 25 mixed codecs | Underlay/alpha/Z-mask indexed comparison |
| [MI2_ORIGINAL_DOS_EXECUTABLE_AND_SAVE_20261116.md](MI2_ORIGINAL_DOS_EXECUTABLE_AND_SAVE_20261116.md) | MZ fingerprint for original executable and four audio drivers, native save header and SHA-256 | Independent original-DOS disassembly/save-format research |

## Which next experiments have the highest information yield?

**Priority A — verify a combined animation mechanism that already has source-coded runtime logic.**

1. **Room 35 waterfall:** record one natural room entry, source-derived eight image states, and the two abnormal-flag (`0x0004`) CYCLs. Questions: does local script202 run, what timer controls each state and palette cycle, and do native pixels match independent composite? Its deterministic order minimizes fitting freedom.
2. **Room 24 shoreline/foam:** ENCD directly starts script200, which selects non-repeating random IM01–IM03, one yield per accepted state. Capture the random choices and independent RGB palette changes; preserve both evidence channels.
3. **Room 81 water:** ENCD directly starts script206, with non-repeating random selection and `delay(18)`. Compare `delay` versus Room24's `breakHere` in real elapsed engine updates.
4. **Room 22 object-only CYCL:** investigate CYCL6/7/8, which affect stored object240 pixels but no static RMIM pixels. A background-only reference comparison can miss them.

**Priority B — compare fundamentally different script/layer semantics.**

5. **Room 55:** complete full `descumm` of scripts 200/212; prove ENCD→200→212→201/203–207 call targets and script209 random dwell, then observe runtime subset. Avoid splicing arbitrary uniform animation loops.
6. **Room 72:** trace array values 361+, 367+, 371+ and count variables; compare dynamic draw placement in indexed native resolution.
7. **Room 44:** composite object facial states with `VAR_TALK_ACTOR` and `VAR_HAVE_MSG`; source allows partial face/expression updates without COST.
8. **Room 48:** three depth planes and actor wait; distinguish zero-image logical objects from renderable sprite images.
9. **Room 103:** global script52 18 black replacement state candidates, verify actual image erasure/coverage.
10. **Room 49:** 25 transparent background strips, mixed 38/48/88 codecs, scrolling and two depth planes; an important *P2 first-principles codec/underlay gate*, but not the first scene to attempt visually.

**Priority C — source-only continued spelunking, no debugger needed.**

11. Expand verified global SCUMM script call graph across room bundles; account for `0x2000` indirect array addressing and bit/local variables.
12. Examine code paths for `o5_roomOps` dynamic palette color, shadows, manipulation and cycle-speed changes; distinguish CYCL presence from active state.
13. Enumerate and decode all ROL/ADL/SBL/SPK alternatives inside `SOUN`, but do not claim MIDI playback without semantics. Use Room13 SBL candidates as first sample fixtures.
14. Read the original 16-bit DOS executable with static tools as a possible independent reference for palette flags and scheduler; keep DOS EXE/IMS/save/ROM bytes out of Git.

## Evidence rule

For each discovered capability distinguish:
- **archive-decoded**: known bytes, chunks, offsets, indices, source hashes;
- **engine-source-backed**: opcode and draw semantics in pinned ScummVM code;
- **independently aligned static script**: bytecode fully walked with bounded operands and branch targets, but not yet cross-checked by descumm;
- **hypothesis**: room visual interpretation, exact source causal interaction, anticipated runtime behaviour;
- **runtime-observed**: only after actual external capture, **NONE added by this expedition**;
- **pixel-verified**: only after native indexed reconstruction compared with independent real capture, **NONE added by this expedition**.

All private original archives, generated previews, evidence captures and output reports belong in `F:\Dev\SCUMMBUCKET\FIXTURE`, external disassemblers/emulators in `TOOLS`, future reusable decoder/test code in `SOURCE\ScummBucket`. No additions to the three workspace top-level folders. Never silently overwrite original game archives.

## Final boundary of this expedition

The original native rendering mechanism is **partially understood but not completed**. These notes preserve exact hypotheses and source-aligned candidates so the next Work/Windows session has specific, reproducible tests instead of rediscovering resource format facts. No verified P4 runtime capability should be claimed merely because a script appears to loop or a palette cycle range intersects art.
