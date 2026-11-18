# MI2 Room22 — complete entry/exit/local-script census, Captain Dread head-animation bug, and enhancement-dependent travel (18 Nov 2026)

**Evidence:** original Monkey Island 2 **DOS VGA** `MONKEY2.000` (SHA-256 `cde7aa8980317e3a750fbb3b49884cdddaf1ff3d4231a0c840b22cceed9033f1`) and `MONKEY2.001` (SHA-256 `ad045372e0d49626503bb50fca29a687ec8e01ef75d9b8bca702a366d143819e`), decoded **read-only in memory** from private `mi2.zip`. V5 opcode and branch semantics reviewed against **pinned [ScummVM v2026.4.0 `script_v5.cpp`](https://github.com/scummvm/scummvm/blob/v2026.4.0/engines/scumm/script_v5.cpp)** and [`script.cpp`](https://github.com/scummvm/scummvm/blob/v2026.4.0/engines/scumm/script.cpp). **Private narrow opcode walker, NOT official descumm or runtime execution**. No native indexed/RGB screen validation, no original-DOS emulator, and no copyrighted source art/dialogue committed.

## 1. First complete Room22 script-corpus alignment

A bounded **opcode-by-opcode narrow v5 parser** decoded **all 8 original Room22 room-owned script bodies** (ENCD/EXCD/LSCR200–205), consuming **5,394/5,394 bytes**, **544 instructions**, **141/141 relative jump references landing at valid instruction boundaries**, no overrun. All resource bodies are interpreted with their exact 8-/9-byte chunk/LSCR header offsets, and branch targets are relative to the end of their signed displacement operands, per pinned v5 code.

| Resource | Original decoded .001 body start | Original code bytes | Independently aligned instructions | Valid relative branches |
| --- | --- | ---: | ---: | ---: |
| EXCD | `0x1C3AB5` | 17/17 | 3 | 1 |
| ENCD | `0x1C3ACE` | 46/46 | 13 | 5 |
| local200 | `0x1C3B0F` | 44/44 | 10 | 0 |
| local201 | `0x1C3B44` | **2,308/2,308** | **243** | **63** |
| local202 | `0x1C4451` | **2,484/2,484** | **248** | **64** |
| local203 | `0x1C4E0E` | **57/57** | **11** | 4 |
| local204 | `0x1C4E50` | **221/221** | 7 | 2 |
| local205 | `0x1C4F36` | **217/217** | 9 | 2 |
| **Total** | | **5,394** | **544** | **141** |

This establishes **instruction and relative-branch alignment**, not independent verification of all dialogue, SCUMM string control codes, soundKludge semantics, executable branch reachability, scene pixels or scheduler frame/timing parity. The parser was tailored to the opcode/subopcode combinations encountered in these eight source scripts and is not a full generic SCUMM interpreter.

Reproducible private code body SHA-256 prefixes (first 20 chars), in order EXCD, ENCD, locals200..205:
`16c25f9257f6cd5cbb53`, `a503047774b0539062a8`, `fab563f4c31f67686738`, `fc1f5bd0bb86d6e9338e`, `ddf1b8db0e11ec52741a`, `3f2519dc59c030e93267`, `369be52795860ef919e6`, `93abba7f7225f9c24639`.

## 2. Original named interactive Dread is object239, but the overlay graphics are separate objects

**Correction to earlier research:** original OBCD chunk `0x1C3671` has CDHD **object ID239**, OBNA **`Captain Dread`**, and its OBIM at `0x1C0EA1` contains no IMxx states (IMHD only). OBCD `0x1C3A7E` is **object ID240 with empty OBNA**, and OBIM `0x1C0EC1` has a stored IM01 picture. This unnamed source art is what contains the three image-only palette-index ranges CYCL6–8. The earlier description of *named object240 Captain Dread* was **incorrect** and has been corrected in linked reports.

Additional original Room22 OBCD object IDs:
- 234 **cabin door**;
- 238 **Captain Dread's map**;
- 235,236,237 and240 **unnamed image components**, with image states 235: IM01–03, 236: IM01–03, 237: IM01, 240: IM01.
- 239 **Captain Dread**, named interaction target with source VERB dispatch.

**OBCD source connection:** object239 VERB default handler (verb255, original VERB relative code PC0x229) directly `startScript(201)`. Its other listed source verbs80/90 contain conditional actor/dialogue image transitions, including a Bit129-gated draw of object237; these are independently instruction-aligned in the VERB region (57 instructions). Thus **the named interactive character dispatches an animation using *unnamed* OBIM fragments**, not a single named object's image-state animation. Exact visual grouping and Z-mask remain unverified.

## 3. Entry starts a standing graphical proxy driven by actor4 talk state

Room22 **local200** is only 44 bytes: actor4 `actorOps(default,costume0,talkColor12,ignoreBoxes)`, place actor4 into Room22 at **(87,78)**, action251; clear image states for objects236 and237; draw object235 state1; set **Bit129=0**; start **local203**.

**local203** then loops continuously:
- First yields while `Var25=VAR_TALK_ACTOR != 4`.
- When actor4 becomes talk actor, repeatedly select a **different** state from `getRandomNr(2)` (values0..2) for **object236**. A randomized state **0** is possible when previous state differs, so do not discard hidden states or assume 1..2 only.
- After each selected `drawObject(object236,state)`, yield; when actor4 is no longer talk actor, restore object236 state1 and resume the listening loop.
- Source body 57B/11 instructions with four valid branch references. This is a **speaker-driven object-image animation** using actor4 for text/speech state and **costume0**, not evidence that visible character motion is a COST cel sequence.

Room22 **ENCD** nested-starts local200, positions Ego at cabin-door object234, then chooses **unnamed object240 state1 if Bit321=0**, else state0. It starts **local202 if Bit321=1**, else **local201 only when Bit125=0**. The branches are mutually exclusive. **EXCD** starts global162 with `[22,82]` only if next-room variable72 equals82; otherwise stop. These are exact source gates, not observed movement.

## 4. Exact original head-turning bug: 32-byte block with omitted Bit129 test

**local201** (243 aligned instructions) contains **three repeated 32-byte head-motion blocks**:

| Local201 drawing PC | Preceding guard | Following original source 32B effects | Safe skip target |
| --- | --- | --- | --- |
| **0x095** | **PC0x090 `equalZero(Bit129)`**; jumps to0x0BB if already set | object237 state1; delay60; object235 state2; breakHere; object235 state3; object236 state1; delay30; set Bit129=1 | **0x0BB** |
| **0x107** | **PC0x102 `equalZero(Bit129)`**; jumps to0x12D if set | same actions; delay60 and30 | **0x12D** |
| **0x184** | **NO Bit129 guard directly before draw** | same 32B actions except initial delay**12** (rather than60) and later delay30; set Bit129=1 | **0x1AA** |

The source block boundaries are **exactly** end-of-draw PC +32:
- first draw ends at0x09B; +32 → **0x0BB**;
- second ends at0x10D; +32 → **0x12D**;
- third ends at0x18A; +32 → **0x1AA**.
All are verified valid instruction starts.

Pinned [ScummVM's `o5_drawObject` implementation](https://github.com/scummvm/scummvm/blob/v2026.4.0/engines/scumm/script_v5.cpp) documents an **optional minor-bugfix workaround** for original MI2 Room22 **local201**, drawing **object237,state1** when **Bit129 already set**: it increments the source script pointer by **32** and returns. This exactly reproduces the missing third guard's 32-byte skip while leaving original source data untouched. The first two source-controlled guard paths already jump over equivalent blocks; the third path is the original omission. **This is strong independent source-code corroboration of the precise glitch mechanism**, still not a measured graphical before/after capture.

If `kEnhMinorBugFixes` is enabled, ScummVM's rendered result **can differ from original DOS execution by design**. Do **not** use an enhancement-on ScummVM preview as an unqualified native-original pixel oracle.

## 5. local201 dialogue progression changes the next room-entry animation state

Additional fully aligned local201 source:
- At PC0x018 **move(Bit125,1)** in a source difficulty-dependent opening branch.
- At PC0x63D **move(Bit321,1)** within a charter/conversation branch. This same flag is the ENCD image-state and script201/202 switch. Later PC0x8C1 tests Bit321.
- Two separate `startScript(204)`/ `startScript(205)` pairs plus `breakHere`/ `isScriptRunning` polling wait for the resulting message branches. The exact start positions include PCs0x570,0x58A,0x5A4 and0x5BF; source stops scripts205/204 at PCs0x5D1/0x5D3 on the corresponding exit route.
- Room22 **local204** (7 instructions) is an original Dread dialogue routine gated by Bit124 (first-time line branch).
- **local205** (9 instructions) is a distinct original dialogue routine gated by Bit126, with two wait-for-message operations.
- The script also contains a source branch that requests **loadRoomWithEgo(object241,Room23,-1,-1)** at PC0x8F9 after starting global script162 [22,23].

**Do not model `move(Bit321,1)` as an immediate sprite redraw**: ENCD sets object240's state only when room entry actually executes, and other object operations may occur in the active script.

## 6. local202 is a distinct travel/dialogue controller, not an alternative looping head animation

Fully walked **2,484 bytes /248 instructions/64 aligned branches**, local202:
- starts global16 [5], sets Ego actor action250, draws object235 state2 and3 with yields, resets object236 state1 and delay30;
- handles source navigation/menu verbs (including object ownership checks for objects245 and238), **without assuming text UI is always shown**;
- contains authored room-change requests to **Room46**, **Room27**, **Room7**, **Room24** and a `loadRoom(82)` branch. It passes original transition script IDs117/124/96 and dynamic sentence handlers 97, among others. These are source destinations, not a verified itinerary through every branch.
- The source's two branch guards at PCs**0x03C** and **0x041** read **Bit70** and **Bit69**. Pinned ScummVM's `o5_notEqualZero` has a **MI2-specific `kEnhGameBreakingBugFixes`** path triggered for Room22 local202 (and other specific scripts), which can alter reads of these and related bits according to inventory item owners and difficulty. Thus original/bugfixed navigation logic can diverge, independently of the head-animation visual fix.
- This controller includes cutscene/override and object pickup operations (e.g. object238), so it should not be converted into a repeating animation.

**Original interactive objects** provide extra entry paths: named Captain Dread object239 default verb255 starts local201; cabin door object234 default verb255 starts global162 [22,23] and loads room23; the source map object238 handlers can call shared global24. These are additional script entrypoints beyond ENCD.

## 7. Two different engine corrections affect the same room

Pinned source supports two separable tests:
1. **Head artifact**: `ScummEngine_v5::o5_drawObject`, `kEnhMinorBugFixes`, local201, object237/Bit129, skip32 bytes; compare exact indexed pixels, object states and source PC with enhancement **off/on**.
2. **Possible dead-end navigation fix**: `ScummEngine_v5::o5_notEqualZero`, `kEnhGameBreakingBugFixes` (with `kEnhRestoredContent` possible), local202, Bit70/Bit69, ownership of items519/295, Bits55/366/67/567. Compare branch outcome and room destination with enhancements **off/on**.

The engine comments say the original game sometimes fails to set Bit70 upon a map-piece purchase, and that fixing it can expose a potential travel dead-end without the lighthouse lens. **These are source-declared compatibility workarounds, not proof this state was reached in any user's save**. Do not merge the head-animation fix and travel-dead-end fix under one fidelity flag.

## 8. Acceptance-ready test matrix

| Case | Input condition / source state | Expected source check | Runtime oracle still needed |
| --- | --- | --- | --- |
| R22-A | Room22 entry, Bit321=0, Bit125=0 | ENCD→200→201; object240 state1, local203 started | Which source backgrounds/objects visible after entry |
| R22-B | Room22 entry, Bit321=1 | ENCD→200→202; object240 state0 | Distinct travel UI and first frame |
| R22-C | actor4 begins/ends talking | local203 advances nonrepeating random0..2 state of object236; restores state1 | RNG, exact script ticks and front-buffer |
| R22-D | local201 head event with Bit129=0 | draw237/state1 then 32B sequence, set Bit1291 | Indexed and RGB native graphic output |
| R22-E | third local201 head event with Bit129=1 | original unguarded block vs optional ScummVM 32B bypass | Compare enhancement off/on, PC and pixels |
| R22-F | local201 reaches charter branch | PC0x63D sets Bit3211 | Subsequent ENCD branching; avoid immediate redraw assumption |
| R22-G | local202 Bit70/69 conditions and inventory owners | original condition vs enhancement-altered `notEqualZero` | Two configurable engine profiles, room destination |
| R22-H | all eight CYCL on Room22 native entry | source delays/ranges, object240 IM01 186..191 | Actual cycle counters and visible object layer |
| R22-I | cabin door to Room23, exit to Room82 | object234/EXCD global162 transitions | Caller and post-entry original state |

**Next step after spelunking:** run official descumm and source-independent portable harness against original files; then profile original runtime with ScummVM and **enhancements explicitly recorded**. This is a research checkpoint, not P4 completed. Original game archives/ROMs and captures stay private under FIXTURE. Code and tests belong under SOURCE, third-party ScummVM/debuggers under TOOLS.
