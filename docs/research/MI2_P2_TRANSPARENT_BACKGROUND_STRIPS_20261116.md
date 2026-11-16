# MI2 P2 — 60 transparency-aware background SMAP strips (2026-11-16)

**Status: read-only structural archive survey + ScummVM v2026.4.0 source review, NOT a rendered scene comparison or implemented decoder enhancement.** All original inputs are unchanged; no copyrighted pixel data is committed.

Original MONKEY2.001 stored-byte SHA-256: `ad045372e0d49626503bb50fca29a687ec8e01ef75d9b8bca702a366d143819e`.

## Confirmed format-inventory gap

Across all **110** resource ROOM bundles, a direct read of `RMIM > IM00 > SMAP` offsets found **60 strips** whose compression code enables transparency in **10** rooms. It is invalid to treat these source pixels as fully opaque and equally invalid to fill transparency with an invented background color. ScummBucket's existing `palette_probe.decode_room_background_indexed` explicitly rejects such strips with diagnostic `BACKGROUND_TRANSPARENT_CODEC_UNSUPPORTED`. This is a correctly visible limitation of its existing P2 feature, not a newly established bug.

| Room | Native size | Transparent SMAP strips | Codec codes/counts | Source-offset examples | Related scene complexity |
| ---: | --- | ---: | --- | --- | --- |
| **20** | 792×144 | **9** | 88×9 | strip68 at 1,598,678; strip90 at 1,614,523 | Scrolling, ZP01, 18 LSCR |
| **32** | 352×144 | **4** | 38×4 | strips0–3, starting 2,496,244 | Scrolling, seven LSCR |
| **36** | 320×144 | **9** | 88×9 | strip12 at 2,861,913; strip37 at 2,879,560 | 5 CYCL, ZP01; zero stored OBIM images |
| **49** | 520×144 | **25** | 38×8, 48×2, 88×15 | strip6 at 4,212,628; strip10 at 4,215,234; strip15 at 4,218,905 | Scrolling, ZP01 and ZP02, 9 LSCR |
| **74** | 320×144 | **8** | 88×8 | strip24 at 6,270,729; strip37 at 6,281,304 | ZP01; 1 LSCR; zero stored OBIM images |
| **99** | 8×200 | 1 | 38×1 | strip0 at 8,222,165 | Tiny special/utility room candidate |
| **100** | 8×200 | 1 | 38×1 | strip0 at 8,261,623 | Tiny special/utility room candidate |
| **101** | 8×200 | 1 | 38×1 | strip0 at 8,300,095 | Tiny special/utility room candidate |
| **102** | 8×200 | 1 | 38×1 | strip0 at 8,324,034 | Tiny special/utility room candidate |
| **107** | 8×8 | 1 | 34×1 | strip0 at 8,759,501 | Tiny special/utility room candidate |
| **Total** | | **60** | **88×41, 38×16, 48×2, 34×1** | | |

These are background strips only, not object-image `IMxx` transparent-compression occurrences (which the experimental object decoder already treats differently).

## Rendering semantics and current limitation

At ScummVM pinned `engines/scumm/gfx.cpp`, `Gdi::decompressBitmap()` identifies transparent opcode variants such as `BMCOMP_ZIGZAG_VT4..VT8`, `BMCOMP_ZIGZAG_HT4..HT8`, `BMCOMP_MAJMIN_HT4..HT8`, `BMCOMP_RMAJMIN_HT4..HT8`; it sets a boolean `transpStrip` and passes a `true` transparency argument to the specific decompressor. The mask decoder also uses `transpStrip` to select OR-vs-replacement mask logic under `dbAllowMaskOr` flags.

Therefore **transparent background strips require context-sensitive composition** rather than a simple full-opacity source index array. Precisely what the destination contains before each strip write, the active transparent color, layer order and mask OR semantics must be checked on an actual engine rendering phase. Do not infer that the pixels are universally zero or always copied from the previous rendered frame.

The current ScummBucket `decode_room_background_indexed` first decodes a strip to indices and then rejects it if marked transparency-aware. That is deliberately protective. To expand P2:
1. Provide source-index data **plus a source transparency mask** for any SMAP using transparent compression, preserving the opaque indices rather than guessing what was underneath.
2. Keep a distinct compositing API to merge transparent pixel positions against a verified source/destination layer; report `unresolved_underlay` rather than fabricate it.
3. Keep ZP depth-mask semantics separate from color-key pixel transparency. ScummVM uses `transpStrip` as an input to Z-mask merge rules too.
4. Capture the actual backend/backbuffer state for a representative room, then verify a single strip and finally a full-scene indexed image pixel-by-pixel. Use Room 32 for a four-strip basic-vertical transparency case, Room 36 for nine major/minor transparent strips plus five CYCLs, and Room 49 for the full three-codec mixed, scrolling, two-Z-plane stress case.
5. Include small 8-pixel rooms as separate diagnostic/utility fixtures; do **not** infer gameplay geometry or visual purpose merely from their presence.

## Practical priority for P2/P4

1. **Room 32:** small bounded 4-strip transparency test (codec 38), 352-wide scrolling.
2. **Room 36:** nine code88 source transparency strips + five source CYCL records; useful palette/underlay mechanism probe.
3. **Room 49:** 25 mixed 38/48/88 strips, 520-wide room, ZP01/ZP02, script behaviour. This is the high-complexity regression target; not the first P2 implementation sample.
4. **Room 20 and 74:** transparency component + mask-specific comparisons, with distinct room widths/scripting.
5. **Rooms 99–102,107:** verify whether tiny 8-pixel RMIM payloads are actually displayed or are storage/utility structures; do not allocate full interactive-room goals prematurely.

Pinned sources:
- https://github.com/scummvm/scummvm/blob/v2026.4.0/engines/scumm/gfx.cpp
- https://github.com/87otlto-coder/Scummbucket/blob/research/p4-engine-palette-trace/scummbucket/palette_probe.py
- https://github.com/87otlto-coder/Scummbucket/blob/research/p4-engine-palette-trace/scummbucket/object_images.py

**Boundary:** decoded tag/offset/code counts are source structural observations; visual overlay meaning and actual framebuffer output still unverified.
