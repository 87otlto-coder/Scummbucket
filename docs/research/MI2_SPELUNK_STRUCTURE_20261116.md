# MI2 spelunking — structural animation targets (16 November 2026)

Status: RESEARCH ONLY. Original DOS VGA archive read, no game execution, no ScummVM frame capture, no Windows verification, no claim of animation playback. Independent one-off parser was used read-only against an uploaded archive; findings should be rerun with ScummBucket before implementation/acceptance.

## Source provenance

- Uploaded archive: mi2.zip, member pair mi2/MONKEY2.000 and mi2/MONKEY2.001. These are the only members treated as game resource input.
- Raw MONKEY2.000: 11,135 bytes, SHA-256 cde7aa8980317e3a750fbb3b49884cdddaf1ff3d4231a0c840b22cceed9033f1.
- Raw MONKEY2.001: 9,080,329 bytes, SHA-256 ad045372e0d49626503bb50fca29a687ec8e01ef75d9b8bca702a366d143819e.
- Archive bytes were not modified. No game resources or copyrighted artwork are committed.
- Tool method: standard-library Python, ZIP member read, XOR 0x69, bounded big-endian length-tagged chunks, LOFF room links, IMHD image counts, RMHD dimensions, CYCL, script chunk boundaries, RMIM/IM00 ZP children, and index-directory links. The temporary exploration script is not a validated ScummBucket tool.
- Cross-check against existing inventory: 110 room bundles, 127 CYCL records, 158 multi-image object candidates. Room 7 ROOM starts at decoded offset 392340 and is 784x144, agreeing with existing research. This is structural consistency, not independent correctness proof for rendering.

## Newly prioritized room comparison

All sizes are decoded native archive room dimensions. A CYCL chunk exists even when its record count is zero. LSCR means local script *chunks*, not executed scripts. An IMxx state is stored imagery, not demonstrated animation.

| Room | Resolution | CYCL records | Object pairs | Stored IMxx states | Multi-image objects | Zero-image OBIM objects | Local scripts | Background ZP layers | Associated COST IDs | Research interpretation |
| ---: | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- | --- |
| 44 | 320x144 | 0 | 20 | 40 | 12 | 0 | 6 | 0 | 130 | Unmixed object-state-heavy target |
| 48 | 320x144 | 0 | 41 | 9 | 1 | 34 | 18 | 3 | 39, 40, 74 | Script-heavy/occlusion-rich, many objects with no stored images |
| 55 | 320x144 | 0 | 37 | 72 | 16 | 10 | 23 | 2 | none bundled | Strongest candidate for repeated script-driven image updates |
| 72 | 320x144 | 0 | 18 | 36 | 12 | 0 | 6 | 1 | 81 | Compact coordinated state-reset/selection target |
| 79 | 320x144 | 0 | 11 | 25 | 7 | 2 | 18 | 3 | 92,104,125,134 | Object states + costumes + 3 ZP layers |
| 103 | 320x200 | 0 | 18 | 36 | 18 | 0 | 2 | 0 | 160,161,162 | 18 two-state objects, but no direct-object script patterns found locally |
| 47 | 480x144 | 4 | 27 | 52 | 11 | 8 | 22 | 1 | 83,84,85,86 | Compound palette/object/script/costume/scrolling candidate |
| 51 | 320x144 | 12 | 4 | 3 | 1 | 3 | 7 | 1 | 3,38,50,51 | Largest cycle count plus actor-costume candidates |

These are source structures only. Do not infer room identity, active soundtrack, scene animation, temporal order or player reachability from bundle co-residence.

## Room 44 — direct source observations

- ROOM: decoded MONKEY2.001 offset 3,513,409; size 110,035 bytes; 320x144.
- 20 paired OBIM/OBCD objects, all with at least one IMxx image. Twelve have multiple stored states: 448:5, 452:2, 453:2, 454:3, 455:2, 456:2, 459:2, 460:2, 461:3, 462:3, 463:3, 464:3.
- Six LSCR chunks (ids 200, 201, 202, 203, 205, 206). One bundled COST resource, index ID 130. No CYCL entries and no background ZP01/ZP02/ZP03 children found under RMIM/IM00.
- Unaligned byte-pattern survey, same opcode signatures as ScummBucket script_candidates.py: 15 drawObject-like matches, none setState-like. 4 matches appear in ENCD, 11 in LSCR 201.
- Particularly useful probes in LSCR 201: object 461 literal state patterns 1/2/3 at decoded offsets 3,622,866 / 3,622,882 / 3,622,916; object 452 variable-state pattern (raw operand 161) at 3,622,930; object 453 variable-state pattern (162) at 3,622,936; object 454 variable-state pattern (163) at 3,622,942. These are NOT instruction-boundary-verified.
- Hypothesis: this room offers a tractable experiment for conditional object image switching without palette cycling or background ZP masking. Variable selection and branch gates must be established with descumm before claiming an animation sequence.

## Room 48 — direct source observations

- ROOM: decoded MONKEY2.001 offset 4,134,176; size 58,391 bytes; 320x144.
- 41 OBIM/OBCD object IDs 512–552. Thirty-four OBIMs have declared zero images and no IMxx state chunks (typically 32-byte OBIMs); only nine images are stored across the seven other objects. Object 514 has 3 stored states; object 512,515,517,519,540,546 each have one. This is a major warning against interpreting object count as scenery image/animation count.
- Eighteen local scripts with IDs 200–217. Longer payload chunks include LSCR 206 (2,610 bytes), 209 (3,636 bytes), 211 (2,433 bytes), 212 (1,498 bytes). Three bundled COST indices 39,40,74; two SOUN indices 65,66, merely storage associations.
- Three background ZP children: ZP01 at 4,164,842 (634 bytes), ZP02 at 4,165,476 (824 bytes), ZP03 at 4,166,300 (290 bytes).
- No CYCL records. Unaligned survey gives 12 setState-like byte patterns, none drawObject-state-like. Candidates: obj 546 set0 in ENCD at 4,180,187, obj 514 set1 and set0 in LSCR 202 at 4,180,460 and 4,180,467; obj 546 set1 in LSCR 207 at 4,183,334 and 4,183,848. All remain unaligned/unverified candidates.
- Hypothesis: object state gating, actor/costume execution and multi-depth occlusion may dominate. A scan limited to image-state counts would miss this room's potential complexity.

## Cross-room leads

- Room 55: 16 multistate objects and 23 LSCR chunks; 164 raw direct-object state-operation byte-pattern matches (163 draw-like, one set-like), concentrated in many object IDs. Especially promising for script-disassembly-driven, nonuniform event sequences. Pattern count is NOT an executed event count.
- Room 72: 12 multistate objects; unaligned LSCR 200 patterns repeatedly set objects 731–748 to state zero then use variables 356–359 as draw state selectors for 731–734. Hypothesis: coordinated batch-reset and scripted display.
- Room 103: 18 paired objects, all exactly two states, 320x200; only 2 local scripts, and no raw direct-object state pattern matches from ENCD/EXCD/LSCR. Global scripts, verb handlers and other opcode forms are outside this scan: DO NOT interpret the absence as proof of static images.
- Room 47: 4 CYCL records, 11 multi-image objects, 22 local scripts and 4 bundled costumes in a 480x144 scrolling room. This is a logical later compound-scene gate, after isolated controls are understood.
- Rooms 104–107 are only 8x8 and include multi-image resources. Do not rank purely by multi-image count; investigate whether these are image-bearing in-game scenes or holding/utility rooms before allocating rendering effort.

## Source-backed engine implications (ScummVM v2026.4.0)

1. ScummVM engines/scumm/script_v5.cpp, o5_drawObject and o5_setState: script bytecode changes object state, possibly via variables; no wall-clock playback follows from mere state inventory. The ScummBucket byte-pattern survey is expressly UNALIGNED and does not prove opcode execution.
2. ScummVM engines/scumm/object.cpp, getObjectImage and drawObject: missing IMxx image for a requested state yields a null image and early return in the normal v5 drawing path. Hence zero-image OBIM objects must not be synthesized into visible frames from their mere presence; object logic and state still require investigation.
3. ScummVM engines/scumm/palette.cpp, initCycl and cyclePalette: the DOS v5 cycle-update path tests cycl->flags & 2 for direction; there is no use of other flag bits in that inspected function. Thus room 35/38 raw flag 0x0004 is unconsumed by this specific ScummVM rotation path, NOT established as meaningless in original DOS data. Room 64's raw rate 65,494 makes 16384/rate truncate to zero and the cycle update skips zero-delay entries. Preserve warnings for every anomalous raw flag and rate.
4. ScummVM has explicitly optional MI2 enhancement workarounds in script_v5.cpp: room 13 script 200/object 108 conditional door-state correction in o5_setState, and room 22 script 201/object 237 Captain Dread head glitch handling in o5_drawObject. An enhanced ScummVM reference can differ from authentic archive-defined DOS script execution. Log engine version and enhancement toggles for every later comparison.

Pinned upstream paths:
- https://github.com/scummvm/scummvm/blob/v2026.4.0/engines/scumm/script_v5.cpp
- https://github.com/scummvm/scummvm/blob/v2026.4.0/engines/scumm/object.cpp
- https://github.com/scummvm/scummvm/blob/v2026.4.0/engines/scumm/palette.cpp

## Later validation plan — explicitly not performed here

1. Reproduce structural counts and source offsets with ScummBucket's inventory CLI using a private authorized MONKEY2.000/.001 pair, preserving hashes and diagnostics.
2. Independently run descumm on ENCD plus LSCR 201 in room 44, ENCD and LSCR 202/206/207/209/211/212 in room 48, and the relevant room 55 and 72 scripts. Verify every cited raw pattern at an actual opcode boundary, including operand modes, jumps and script callers. Reject false positives.
3. Map direct script state selectors to valid IMxx states; distinguish drawObject vs setState, state 0, wait/print/delay/yield, random and condition-dependent paths.
4. Capture frames/timer/object states, actor footprints, depth-plane masks, palette and script slots in unmodified vs explicitly configured ScummVM. Room 44 tests object switching; Room 48 tests 3-plane layering; Room 55 tests coordinated object transitions.
5. Require independent indexed foreground pixel comparison with the engine, no fitted per-frame phase and explicit provenance. Separate archive-decoded, source-code, runtime-observed, inferred and synthetic results.

Research priority: Room 55 script event graph; Room 44 pure object states; Room 48 metadata-only objects and 3-plane occlusion; then Room 72 batch selection and Room 47 mixed mechanisms. Existing verified Room 7/23 tests remain baseline gates, not tests rerun by this session.
