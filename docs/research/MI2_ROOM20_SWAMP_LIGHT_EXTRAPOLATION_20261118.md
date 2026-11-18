# MI2 Room20 swamp: lighting extrapolates beyond last X knot into walkable right-hand geometry (18 November 2026)

**Evidence class:** read-only original DOS VGA MONKEY2.000/.001 (MONKEY2.001 SHA-256 `ad045372e0d49626503bb50fca29a687ec8e01ef75d9b8bca702a366d143819e`), native original ROOM20 BOXD/BOXM resources and fully aligned ENCD, complete global script49 source already documented, pinned [ScummVM v2026.4.0 boxes.cpp](https://github.com/scummvm/scummvm/blob/v2026.4.0/engines/scumm/boxes.cpp), [script_v5.cpp](https://github.com/scummvm/scummvm/blob/v2026.4.0/engines/scumm/script_v5.cpp) and [palette.cpp](https://github.com/scummvm/scummvm/blob/v2026.4.0/engines/scumm/palette.cpp). **No runtime actor traversal, descumm comparison, native RGB/frame accuracy or source-interpreter confirmation.** No original game bytes/images committed.

## Room20 original layout and dynamic lighting setup

Room20 physical `RMHD` is **792×144** (viewport normally320 wide). The original OBCD names identify the room's scene context as **swamp**, with **shore**, **path**, **shack**, **coffin**, **crate** and **sign** objects. Room20 CYCL chunk at `0x17B4FB` is 10 bytes total and contains **zero palette cycle records**.

Room20 ENCD body at **`0x18DEF3`**, fully walked **96/96 bytes,20 instructions,3/3 valid branch targets**, executes at:
- PC0x00C `setVarRange(Var285,[0,-30,260,343,490,543])` X breakpoints;
- PC0x01C `setVarRange(Var291,[0,255,255,150,150,255])` brightness control points;
- PC0x026 `startScript(global49)` (Ego-X-dependent lighting on palette indices **192–207**).
The other entry calls start room-specific actor/environmental scripts and state-conditioned objects, whose rendering is not directly validated here.

## Native BOXD: original walkbox coordinates extend beyond the final lighting control point

Original Room20 `BOXD` at **`0x17B617`**, total length **290 bytes**, encodes 14 boxes. In v5, there is a 2-byte box count following the tag, then **20-byte entries**, with the first eight signed 16-bit numbers encoding four quadrilateral corners (see pinned `ScummEngine::getBoxCoordinates`).

The right-hand subset (source encoded XY quadrilateral bounds) is:

| Box index | Minimum native X | Maximum native X | Native Y bounds |
| ---: | ---: | ---: | --- |
| **8** | 373 | 498 | 96–101 |
| **9** | 498 | **556** | 101–109 |
| **10** | **556** | **604** | 109–111 |
| **11** | **604** | **653** | 95–111 |

The room's BOXM at **`0x17B739`** contains original encoded route entries including 9→10 and 10→11 rightward adjacency references. This is **static navigation geometry**, not a runtime trace proving Ego traverses every point. Original box flags/locks and scripted actor positions can still restrict accessibility.

## Why global49 does NOT run off the end of the control-point arrays

The already fully aligned [global49 actor lighting controller](MI2_ROOM93_ACTOR_POSITION_PALETTE_LIGHTING_20261117.md) starts index at5 and, when current actor X is **at or above** final `X[5]`, keeps index5 and interpolates (or **extrapolates**) using the **last known segment i=4→5**. It does not read Var285+6 to get a nonexistent seventh X value on this path. Thus the original right-side Box10/11 native coordinate domain is **source-consistent with deliberate or tolerated extrapolation**.

Room20 last two curve knots are native **(X=490,scale150)** and **(X=543,scale255)**. The original SCUMM expression uses signed integer division truncating toward zero:

`raw_scale(x) = 150 + trunc((x - 490) × 105 / 53)` for `x >= 490` along the final segment.

| Original actor world X | Source-computed *unclamped* lighting scale |
| ---: | ---: |
| 490 | 150 |
| 520 | 209 |
| 542 | 253 |
| 543 | 255 |
| **544** | **256** |
| **556** | **280** |
| **604** | **375** |
| **653** | **472** |

These are **counterfactual arithmetic at selected source-native coordinates**, not a claim that an actor actually occupied these exact positions, nor proof of 11 different displayed frames.

Pinned `o5_roomOps::SO_ROOM_INTENSITY` passes the **int-valued SCUMM scale** to `darkenPalette(scale,scale,scale,192,207)`; source does **not pre-clamp the scale to 255**. The original-style v5 palette routine instead computes each RGB channel `min(252,base_component * scale / 255)`. Thus raw scale>255 can cause greater brightness than a scale255 rendering until individual channels reach the RGB cap252. A native reconstruction that clamps scale at255 before per-component multiplication can be **pixel-inaccurate** on these right-hand source paths.

### Important caveat: scale != emitted RGB

The exact number of visibly changed pixels depends on Room20's original CLUT values 192–207 and whether corresponding indices occur in the background/objects/actor costume. Source script data alone cannot prove an observable frame sequence or pixel extent. Log the active RGB 192–207 palette and indexed image separately during future capture.

## Companion source research and verification priority

- [Room20/other room lighting atlas](MI2_GLOBAL49_EGO_LIGHTING_ATLAS_20261118.md) catalogs different original room curves and empty CYCL despite source-driven colors; this room is notable because original walkboxes cross its rightmost breakpoint.
- [Global54 companion actor lighting](MI2_ACTOR_LIGHT_SOURCE_GLOBAL54_ROOMS9_13_20261118.md) shows independent palette range208–255 and singleton actor targeting, but global54 is **not asserted active** in Room20.
- Capture actual Ego world-X at >543 in Room20, confirm alive global49, read raw Local5 brightness (should match source under unchanged arrays), compare original source 192–207 palette RGB and frontend indexed pixel hashes; check whether walkbox flags, other cutscenes or camera restrict entry into Box10/11.
- Preserve native original room/script IDs, palette phase, source CLUT, actor/camera X, active script slots, and script variable interpolation values. No original assets or archives belong in Git.

**Conclusion:** a cross-resource original-script + physical walkbox proof of an **unclamped extrapolated illumination coefficient** beyond the final control point; actual scene visibility remains unobserved.
