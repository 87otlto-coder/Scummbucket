# MI2 Room21 — camera-driven two-bank RGB inversion and coupled Ego lighting (18 November 2026)

**Evidence class:** read-only original DOS VGA MONKEY2.000/.001 archive, stored SHA-256 of MONKEY2.001 `ad045372e0d49626503bb50fca29a687ec8e01ef75d9b8bca702a366d143819e`. Opcode-by-opcode independent **narrow Scumm v5** walk, including nested arithmetic expressions, variable-indexed writes and signed jump target checks; compared to pinned [ScummVM v2026.4.0 script_v5.cpp](https://github.com/scummvm/scummvm/blob/v2026.4.0/engines/scumm/script_v5.cpp), [script.cpp](https://github.com/scummvm/scummvm/blob/v2026.4.0/engines/scumm/script.cpp), [vars.cpp](https://github.com/scummvm/scummvm/blob/v2026.4.0/engines/scumm/vars.cpp) and [palette.cpp](https://github.com/scummvm/scummvm/blob/v2026.4.0/engines/scumm/palette.cpp). **No official descumm comparison, actual runtime activation / frame comparison, original interpreter test, or native indexed/RGB parity.** All original copyrighted input and private outputs remain off Git.

## Static verification

| Room21 resource | Original body offset (.001 XOR-decoded byte position) | Bytes walked | Instructions | Valid jumps |
| --- | ---: | ---: | ---: | ---: |
| **ENCD** | `0x1A3FE7` | **155/155** | **29** | **7/7** |
| **LSCR208** | `0x1A705B` | **140/140** | **22** | **5/5** |
| **EXCD** | `0x1A3F9A` | **37/37** | **6** | **2/2** |

Physical Room21 RMHD width **456**, height **144**, wider than the normal 320-pixel viewport. Tagged CYCL chunk is only **10 bytes** (8-byte header + two zero payload bytes), with **no palette cycling records**. Therefore its major dynamic RGB effect is **script-driven without populated CYCL**. Local208 is not merely present: **ENCD explicitly starts it at PC0x071**, across ordinary static entry branches, while it guards its own execution on VGA Var49==19.

## Room21 entry sets up 7 control points, not 6

At ENCD PCs 0x051 and0x063, native v5 `setVarRange` writes **seven elements** each, unlike many other rooms' six-element arrays:

- `Var[285..291]` X knots: **[0,0,187,225,266,320,999]**.
- `Var[291..297]` initial intensity knots: **[0,255,255,25,220,220,220]**.

**IMPORTANT overlapping-storage correction:** the two `setVarRange` groups begin at **Var285** and **Var291**, respectively, so the 7th value of the X group at **Var291** is immediately **overwritten by the 1st value of the intensity group**, 0. The actual live global-variable storage after both instructions is:

| Variable indexes | Values |
| --- | --- |
| `Var285..290` | **[0,0,187,225,266,320]** |
| `Var291..297` | **[0,255,255,25,220,220,220]** |

Thus do **NOT** promote 999 as an accessible seventh X breakpoint in the shared global49 source code: `Var291=0` at the time global49 runs. The extra seventh *intensity* entry `Var297=220` exists, whereas the 7th *X* assignment is clobbered. This could matter when actorX exceeds the last valid X knot at320; reachability and original DOS edge behavior are unverified.

ENCD also:
- at **PC0x038** checks VGA Var49==19;
- at **0x03F** applies `SO_ROOM_INTENSITY(253,16,79)`;
- at **0x044** applies `SO_ROOM_INTENSITY(27,80,190)`;
- at **0x06E** starts local202; at **0x071** **starts local208**; at **0x074** starts local212;
- at **0x077** tests `isScriptRunning(42)`; when it is not running, PC0x080 requests a second `startScript(global49)`, and PC0x083 applies a room-scroll restriction `SO_ROOM_SCROLL(160,160)`. Because local208 already starts global49 during its initial nested invocation under VGA, this conditional direct start does **not** gate all possible start49 execution.

**Room21 EXCD** has sound/verb updates but no direct stopScript49 or54.

## Fully aligned local208: three coupled palette regions and a camera formula

Pinned `vars.cpp` maps **Var[2] to `VAR_CAMERA_POS_X`**, in native world/screen camera-center X coordinates. Local208 executes:

1. **PC0x000:** only run under `Var49=VAR_VIDEOMODE==19` (VGA).
2. **PC0x007:** `Local2 = 9999` (cached prior value sentinel).
3. **PC0x00C–0x011:** `Var100=0` and jump into the first brightness calculation **without first sampling the camera**, ensuring deterministic initial setup.
4. **PC0x014 (subsequent loops):** `Var100 = VAR_CAMERA_POS_X - 160`.
5. **PC0x01F:** `base = Var100 + trunc(Var100×65 /100) +27`, computed with original 16-bit-int SCUMM expression stack.
6. **PC0x036:** `left = 280 - base` (stored `Local0`).
7. **PC0x041:** `right = base + Var160` (stored `Local1`). Var160 is an additional global state offset, **not** implicitly zero for all saves.
8. **PC0x04C–0x054:** if `right` unchanged from cached `Local2`, yield and resample camera; if changed, proceed.
9. **PC0x05C:** **`SO_ROOM_INTENSITY(right,80,190)`**, targeting **111 palette entries**.
10. **PC0x062:** **`SO_ROOM_INTENSITY(left,16,79)`**, targeting **64 entries**.
11. **PC0x068/0x06F:** write **Var292=left**, **Var293=left** (control-point indices 1,2).
12. **PC0x076/0x07D:** write **Var295=right**, **Var296=right** (control-point indices 4,5).
13. **PC0x084:** **`startScript(global49)`**, then `breakHere` and jump to PC0x014.

A source-constrained algebraic invariant is **`left + right = 280 + Var160`** prior to per-channel RGB clipping, independent of camera X. The right-side global state offset `Var160` modifies only the `right` scale; it is *not* subtracted from `left`.

### Sample counterfactual illumination states (Var160=0 for illustrative arithmetic only)

Assume normal 320-pixel viewport camera center can range160..296 in this 456-pixel-wide room, absent other camera-scroll restrictions. **These are source-derived values, not observed screen colors.**

| Camera center X | delta= X−160 | left scale on indices16–79 | right scale on indices80–190 |
| ---: | ---: | ---: | ---: |
| **160** | 0 | **253** | **27** |
| **200** | 40 | **187** | **93** |
| **250** | 90 | **105** | **175** |
| **296** | 136 | **29** | **251** |

**Engine RGB nuance:** pinned `darkenPalette` computes `base_R/G/B × scale /255` with integer arithmetic and clips components to **252** in original-style v5, so the invariant holds on raw scale variables, not on output RGB or perceived luminance. Original indexed pixel values are not modified by these commands.

### The third channel: actor-X bank 192–207 is continuously reprogrammed

The persistent **global49** light script (previously fully aligned in [Room93](MI2_ROOM93_ACTOR_POSITION_PALETTE_LIGHTING_20261117.md)) interpolates Ego X using shared X knots285..290 and brightness knots291..296, then changes RGB **192–207**.

Room21 local208 **writes four of those live brightness knots** whenever camera/state scale changes, then **restarts global49**. Under pinned ScummVM `runScript`, these calls use non-recursive start semantics and **replace** any old global49 instance, clearing the last-intensity cache and forcing a fresh evaluation of the new curve.

Given current values of `left/right`, the X/brightness curve intended for global49's normal actor X=0..319 path becomes:

- (0, left), (187, left), **(225, 25)**, (266, right), (320, right).

Thus the game implements **coupled camera-position-dependent palette reweighting (indices16–190) and Ego-position-dependent lighting (indices192–207)**. The latter's control points shift as the camera does, so a simple static X→brightness function is insufficient.

This is **source-proven interaction between palette bands and global-script lifecycle**. It is a strong candidate for P4 multi-layer/dynamic-scene validation; the actual visible RGB output and temporal phase are not yet recorded.

## Why this matters for P4

A correct source-driven scene model needs separately time-stamped:
- camera world X vs screen scroll and room-scroll restrictions;
- `Var160` and the computed `left/right` scales;
- the two room-base-RGB scaling operations (16–79,80–190);
- overwrites to brightness control-point globals292/293/295/296;
- **global49 stop/restart** with fresh script-local cache and actor-X interpolated range192–207;
- original base CLUT, VGA mode, actor location and current scene resource;
- RGB+indexed screen/actor/mask comparison under recorded engine frame phases.

A CYCL-only inventory would see **zero animation** here; the original scripts encode a **camera-coupled three-region lighting system**. Do **not** simulate it as a static background GIF or two separate perpetual effects with unrelated clocks.

**Future gates:** independent official descumm on Room21 ENCD and LSCR208; actual pinned ScummVM natural Room21 entry, camera center at several source positions, Var160 changes, global49 restarts, RGB palette range hashes, indexed native framebuffer and actor/cel layers. Compare the 999 “seventh X point” overwrite and bounds before interpreting X>320. Preserve original archives unchanged/private.

**Status:** fully source-aligned scripts with precise formulas and engine-source semantics, **not observed runtime or pixel-verified reconstruction**.
