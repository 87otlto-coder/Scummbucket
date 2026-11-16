# MI2 Room 103 — eighteen two-state masks and global script 52 (2026-11-16)

**Research-only**, performed with the original-style DOS VGA archive and a private in-memory/native-sized image preview. No ScummVM gameplay, no original DOS run, no independent pixel-accuracy comparison, and no claims of script execution. No art or reconstructed screenshots are committed.

Original raw members: MONKEY2.000 SHA-256 `cde7aa8980317e3a750fbb3b49884cdddaf1ff3d4231a0c840b22cceed9033f1`; MONKEY2.001 SHA-256 `ad045372e0d49626503bb50fca29a687ec8e01ef75d9b8bca702a366d143819e`.

## The structural trap

Room 103 has a **320×200** `RMIM > IM00` background, 18 paired `OBIM/OBCD` objects (IDs **1116–1133**), **two** image states per object, and only 2 `LSCR` chunks. A scan restricted to `ENCD/EXCD/LSCR` yields **zero direct-object draw/set pattern matches**.

However, `DSCR[52]` links a **6,471-byte `SCRP` global script** stored in this same room bundle, beginning at decoded MONKEY2.001 **8,456,455**. An independent byte-pattern survey found **18 potential direct `drawObject(obj,state=2)` instructions**, one per object. This is **not yet an independently instruction-boundary-confirmed full script disassembly**. ScummVM v5 `o5_drawObject` source supports the parameter interpretation, but caller/branch reachability and actual execution remain unverified.

### Six triple-object groups in global script 52

The following offsets are **relative to the SCRP script body beginning at chunk +8**. Within each group, three candidate operations select **state 2**:

| Group (code order) | Object IDs | Candidate body offsets |
| --- | --- | --- |
| A | 1119,1120,1121 | 0x0741, 0x0748, 0x074F |
| B | 1116,1117,1118 | 0x09E7, 0x09EE, 0x09F5 |
| C | 1122,1123,1124 | 0x0B2B, 0x0B32, 0x0B39 |
| D | 1131,1132,1133 | 0x127A, 0x1281, 0x1288 |
| E | 1128,1129,1130 | 0x14D7, 0x14DE, 0x14E5 |
| F | 1125,1126,1127 | 0x164D, 0x1654, 0x165B |

The groups are nonconsecutive numerically and separated by substantial script sections. Do not infer they are one uninterrupted 18-state animation; there may be independent dialogue/cutscene steps and branches.

## Preliminary source-image findings

A private reimplementation of the source-indexed v5 strip decoding path produced a **black background** and **18 color images in state IM01**, arranged as sepia-like illustration fragments. Critically **all 18 images in IM02 have only one opaque RGB color: black (0,0,0)**, with varying transparency masks. This is supported by observed decoded pixels from original bytes, but pixel-perfect fidelity against ScummVM is unverified. Therefore classify these as **source-decoded black-silhouette replacement candidates**, not conventional two-frame motion animations.

For 11 of 18 objects the preview's IM01 vs IM02 opaque alpha-pixel count matches exactly; the other seven differ by small amounts. A black-color image may erase, cover or mask a previously drawn illustration on a black canvas, but determining the actual visual effect requires the runtime compositor and script graph. **Do not label IM02 a 'blank image'**: its opaque black pixels are meaningful and may overwrite artwork.

The original v5 `CDHD` header stores object X and Y in eight-pixel units, and the `IMHD` source provides image dimensions. These exact source positions were decoded for all 18 objects:

| Object | Screen-origin candidate (x,y) | Native dimensions |
| ---: | --- | --- |
| 1116 | (0,32) | 72x104 |
| 1117 | (0,136) | 80x64 |
| 1118 | (80,144) | 120x56 |
| 1119 | (248,0) | 80x72 |
| 1120 | (232,72) | 88x64 |
| 1121 | (232,136) | 88x64 |
| 1122 | (176,0) | 144x40 |
| 1123 | (248,40) | 72x64 |
| 1124 | (280,104) | 40x64 |
| 1125 | (256,24) | 64x104 |
| 1126 | (240,128) | 80x72 |
| 1127 | (184,160) | 56x40 |
| 1128 | (0,0) | 160x40 |
| 1129 | (0,40) | 80x24 |
| 1130 | (0,64) | 64x80 |
| 1131 | (0,128) | 72x72 |
| 1132 | (72,136) | 72x64 |
| 1133 | (144,144) | 88x56 |

The spatial positions form clusters in distinct left/right regions. They do not indicate any camera pan. The precise order and compositing of colored versus black replacement states must come from interpreter-aligned script and runtime execution.

## Why this is important for P2/P4

1. An `IMxx` transition can change **an entire visual region or silhouette**, not just animate a sprite limb.
2. A black-looking source image is **not equivalent to alpha transparency**, and state 2 may be an active occlusion/erasure operation.
3. **Global script ownership is independent of local script counts**. A room-level animation-candidate inventory missing `SCRP` opcode references can be materially incomplete.
4. Full reconstruction may require a **stateful back-buffer update history** and dirty rectangles, not simply composite whichever IMxx state is selected onto a fresh black background.
5. The 18 small geometry records provide tractable per-object index/mask fixtures if/when a faithful v5 image renderer is verified.
6. Keep Room 103 isolated from Room 7/23 gameplay-only acceptances: its timing/event source is likely a distinct script-driven mechanism and its 200-pixel height differs from the common 144-pixel scene.

## Verification next time

- Disassemble the entire 6,471-byte global script with authentic descumm; validate the 18 candidates as opcode boundaries and determine all conditions, state-1 draw sources, script callers, yields, object ordering and timeline.
- Confirm source pixel indices and alpha handling with ScummBucket's maintained decoder and sample comparisons, especially opaque-black versus transparent source strips.
- Capture any actual Room 103 execution with object states, script position and indexed front/back framebuffer. Compare before/after image areas and state 2.
- Export a **conditional region-event timeline**, not a guessed 18-frame looping GIF.

Pinned source: https://github.com/scummvm/scummvm/blob/v2026.4.0/engines/scumm/object.h (v5 `CodeHeader` x/y/w/h), https://github.com/scummvm/scummvm/blob/v2026.4.0/engines/scumm/script_v5.cpp (`o5_drawObject`), https://github.com/scummvm/scummvm/blob/v2026.4.0/engines/scumm/object.cpp (`drawObject`, `getObjectImage`).
