# MI2 Room93 global script49: actor-X-interpolated VGA palette lighting (2026-11-17)

**Evidence:** the original DOS VGA `MONKEY2.001` archive, stored SHA-256 `ad045372e0d49626503bb50fca29a687ec8e01ef75d9b8bca702a366d143819e`, was decoded *read-only*. The original tagged global `SCRP[49]` is **stored with room4** (`SCRP` body at `0x38B3D`), but started by Room93 ENCD. Independent narrowly implemented opcode walker consumed **218/218 bytes**, **25 instructions**, **9/9 aligned relative jumps**, including expressions with nested `getActorX` (opcode `0xC3`). Primary code semantics checked against pinned ScummVM v2026.4.0 [script_v5.cpp](https://github.com/scummvm/scummvm/blob/v2026.4.0/engines/scumm/script_v5.cpp), [script.cpp](https://github.com/scummvm/scummvm/blob/v2026.4.0/engines/scumm/script.cpp), [palette.cpp](https://github.com/scummvm/scummvm/blob/v2026.4.0/engines/scumm/palette.cpp), [vars.cpp](https://github.com/scummvm/scummvm/blob/v2026.4.0/engines/scumm/vars.cpp). No gameplay observed, no independent official `descumm`, no native-pixel acceptance.

## Coupled original source

Room93 ENCD (fully walked 215/215 bytes) seeds two **6-element SCUMM global variable arrays**:

- `Var[285..290]` X breakpoints: `[0, 0, 100, 160, 230, 320]`.
- `Var[291..296]` brightness values: `[0, 100, 200, 255, 200, 100]`.

It starts **global script49 at ENCD PC 0x001E**, *before* it resets object-image states (local202) and applies per-logical-room object/box layout (local200). This call is immediate/nested until global49's first yield.

The 0th entries `X0=0,Y0=0` act as sentinels for the normal coordinate range. For `0≤actorX<320`, the script finds the lower breakpoint with index `i≥1`, and interpolates the **1–5** X/Y points. Thus **the effective brightness at actorX=0 is 100, NOT 0**. The stored (0,0) tuple must *not* be incorrectly included as an active linear segment.

## Script49 control flow

| PC | Source effect |
| --- | --- |
| `0x0000` | Guard: `Var49 == 19`; ScummVM's `VAR_VIDEOMODE` 19 means standard VGA |
| `0x0007–0x0013` | Guard: Ego (`Var1`) actor room equals current logical `Var4` |
| `0x0013–0x0033` | Start `Local0=5`; decrease index until actor X is at/above `Var[285+Local0]` (with lower-index stopping condition) |
| `0x0033–0x006C` | Construct `nextIndex=Local0+1`, `dx=X[i+1]-X[i]`, `dy=Y[i+1]-Y[i]`, and `offset=actorX-X[i]` |
| `0x006C–0x0098` | If `dx!=0`, compute `brightness=Y[i] + (offset*dy)/dx` by integer expression operations. If changed from `Local6`, issue **`roomOps(SO_ROOM_INTENSITY,brightness,192,207)`** and remember it |
| `0x009B–0x00D5` | Anomalous denominator-zero branch prints a special actor253 message instead; source exists, but runtime branch reachability/meaning not established |
| `0x00D5` | `breakHere`; loop back to PC0x0007 |
| `0x00D9` | Stop if video mode guard fails |

The script uses **C++ signed integer division (truncate toward zero)** through ScummVM's `o5_expression`; implementing floor-division on negative slopes would produce subtly wrong brightness by one unit.

### Bounded source-derived brightness curve

| Native actor X | Intended interpolated intensity | Status |
| ---: | ---: | --- |
| 0 | **100** | 1st active control point |
| 50 | 150 | Exact integer interpolation |
| 100 | 200 | 2nd active control point |
| 130 | 227 | Between 100 and160 |
| 160 | 255 | Maximum |
| 195 | **228** | Negative slope, truncation toward zero; Python `//` would give 227 (wrong) |
| 230 | 200 | 4th active point |
| 275 | 150 | Between230 and320 |
| 319 | **102** | Negative slope, truncated toward zero |

The normal piecewise curve is `(0,100)→(100,200)→(160,255)→(230,200)→(320,100)`. **The actor-X value exactly 320 is a separate unresolved edge case**: source lookup starting at index5 can read beyond the intended 6-value X table into adjacent global variable storage; the present research has not observed this boundary. Do not claim the last endpoint is always reached by the actor. Use the above table only within **0..319** and capture any range exceptions.

### RGB colour calculation is not an opacity or indexed-pixel change

Pinned `o5_roomOps` subopcode8 calls `darkenPalette(a,a,a,b,c)`, with `a=brightness,b=192,c=207`. The v5 DOS ordinary palette path reads the **base room palette** via `getPalettePtr`, multiplies each RGB channel by `brightness / 255` using integer arithmetic, clips output to max **252** for v5/v6 up to HE60, and marks the palette indices **192..207** dirty. It does not change the actual stored indexed background pixels. It is a *live actor-position-dependent RGB transform* limited to a 16-colour palette range.

**Reconstruction risk:** exporting one RGB image and moving an actor over it will be wrong. The same indexed surface yields different RGB results as the actor X changes. The scene's logical room (160..167), physical source resource93, base palette, current actor and palette index usage are distinct state variables.

## Test design / limitations

1. Reproduce Room93 ENCD's variable arrays and ensure global49 runs in each logical alias as intended. Record mode `Var49`, logical room `Var4`, source `_roomResource`, Ego actorRoom and X, `Local0..6`, and every palette-update opcode with script PC.
2. Verify sample actor positions on **both slopes**, especially 195 and319, comparing exact `RGB[192..207]` against pinned ScummVM. Use an original DOS/DREAMM observation only if the source-version implementation disagrees.
3. Check the entry-caller nested timing, `Var49!=19` bypass, missing actor-in-room case, and any actual actor movement triggering the denominator-zero/upper-bound edge.
4. Preserve colour transform separately from object-image state, masks, and background pixels; dynamic palette operations are P4 but not source-frame decoding themselves.
5. All game binaries stay under private `FIXTURE`; report contains **only** offsets, code facts and numerical derived values.

**Status:** fully aligned archive bytecode + primary implementation semantics. No observed runtime reachability or pixel parity.
