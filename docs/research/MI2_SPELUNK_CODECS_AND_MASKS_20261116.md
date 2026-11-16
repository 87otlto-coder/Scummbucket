# MI2 spelunking — archive-wide strip-codec and depth-mask census (16 November 2026)

Research-only checkpoint, from a read-only independent exploration of the uploaded original-style DOS VGA MONKEY2.000 / MONKEY2.001 pair. This scan does NOT decode RGB artwork, inspect Windows runtime, run an independent renderer comparison, execute bytecode or establish gameplay reachability. Cross-check all numbers with the maintained ScummBucket inspector before making implementation claims.

Source SHA-256: MONKEY2.001 = ad045372e0d49626503bb50fca29a687ec8e01ef75d9b8bca702a366d143819e. Data was XOR-decoded with 0x69 in memory; no source file was modified. Each strip opcode was collected by following the width/8 little-endian SMAP strip-offset entries relative to the SMAP chunk and reading the first byte of the referenced strip. Parent chunk lengths and table bounds were checked. A populated strip code is NOT proof the entire compressed strip decodes accurately.

## Object census

- Total OBIM object records: 1,145.
- Zero-image objects (IMHD declares 0, no IMxx): 550.
- Single-image objects: 437.
- Multi-image objects (>=2 IMxx): 158.
- Total stored IMxx object-image states: 1,047.
- Total object SMAP strips identified: 7,505.
- Background IM00 SMAP strips identified across 110 rooms: 4,651.
- No invalid table/strip offsets were seen in this one-off scan. This is not an independently validated full input acceptance test.

### Per-image depth-mask distribution

| Image-state class | Stored IMxx states |
| --- | ---: |
| No ZP child | 448 |
| ZP01 only | 335 |
| ZP01 + ZP02 | 198 |
| ZP01 + ZP02 + ZP03 | 66 |
| Total | 1,047 |

Masks are distinct RLE-compressed depth-plane information, not generic image alpha. They must survive export as separate layers. The absence of a child mask must not be replaced with a fabricated mask.

### Controlled depth-plane ladder

| Target room | Stored images | Each image state's ZP set | Background RMIM ZP set |
| ---: | ---: | --- | --- |
| 44 | 40 | none | none |
| 72 | 36 | ZP01 | ZP01 |
| 55 | 72 | ZP01 + ZP02 | ZP01 + ZP02 |
| 48 | 9 | ZP01 + ZP02 + ZP03 | ZP01 + ZP02 + ZP03 |
| 79 | 25 | ZP01 + ZP02 + ZP03 | ZP01 + ZP02 + ZP03 |
| 103 | 36 | none | none |

These six rooms offer a naturally graduated 0→3-plane mask test set, independent of whether any particular state is reachable or animated in actual gameplay. All four object-image ZP configurations are represented by source data.

Room 48 is particularly instructive: 41 object records but only 9 stored images. Its 34 zero-image OBIM resources must not be synthesized into visible sprite frames. Several zero-image objects have nonzero geometry metadata; object 547–552 have 0x0 IMHD dimensions. A metadata-only object can still participate in script/interaction logic.

## Object SMAP code census

Every detected object strip code lies within the numeric decoder families currently recognized in ScummBucket's object_images.py (RAW256 1/149; basic vertical 14–18 and 34–38; basic horizontal 24–28 and 44–48; major/minor 64–68, 84–88, 104–108, 124–128). This supports *declared format repertoire coverage*, NOT actual full-game successful decompression or pixel-perfect correctness.

Observed object strip opcode counts (7,505 total):

| Code | Count | Code | Count | Code | Count |
| ---: | ---: | ---: | ---: | ---: | ---: |
| 1 | 16 | 14 | 138 | 17 | 26 |
| 18 | 631 | 24 | 13 | 27 | 10 |
| 28 | 182 | 34 | 295 | 35 | 9 |
| 36 | 8 | 37 | 94 | 38 | 1,175 |
| 45 | 48 | 46 | 5 | 47 | 11 |
| 48 | 397 | 64 | 6 | 66 | 1 |
| 67 | 47 | 68 | 1,982 | 84 | 80 |
| 85 | 2 | 86 | 2 | 87 | 98 |
| 88 | 2,229 | | | | |

Examples of rare but genuine source-byte codec targets:
- Object code 66: room 56, object 656, IM01 strip 2, file-decoded offset 4,862,373.
- Object code 85: room 39, object 419, IM01 strips 4–5, offsets 3,088,938 and 3,088,960.
- Object code 86: room 106, object 1145, IM03 strip 4, offset 8,754,864; room 107, object 1153, IM03 strip 3, offset 8,816,767.
- Object RAW256 code 1 appears 16 times, including room 103 object 1129 IM01 strip 0, offset 8,434,538.
- Object code 64: room 94 object 900 IM01 strip 3, offset 7,955,355 (among six uses).
- Object code 24: room 94 object 898 IM01 strip 1, offset 7,954,791 (among 13 uses).
- Rare codes 35 and 36 also occur in multiple objects. Preserve per-strip transparency semantics: codec family controls whether room TRNS is honored, not the palette index alone.

These exact strip targets are valuable future regression-fixture selectors, but the read-only structural scan alone has not proven their decoded pixels.

## Background SMAP code census

Total background strips: 4,651. Code counts:
- 14=46, 15=3, 16=3, 17=25, 18=379.
- 26=1, 27=24, 28=127.
- 34=1, 38=16, 48=2.
- 67=60, 68=3,923, 88=41.

Every background strip code is also in the numeric format repertoire above. This does not establish complete support across all room sizes or compressed payloads.

Unusual exact background targets:
- Code 26: room 62, IM00 strip 39, decoded resource offset 5,370,371.
- Code 34: room 107, IM00 strip 0, offset 8,759,501.
- Code 15: room 20 strip 42, offset 1,585,458 and room 62 strips 0–1.
- Code 16: room 62 strips 2–3 and room 70 strip 79.
- Code 48: room 49 strips 10 and 14.

Room 7 uses three code-28 and 95 code-68 background strips, confirming that the previously validated Room 7 benchmark exercises only a small subset of full-game decoder modes. Room 23 uses 40 code-68 background strips. Thus 87-frame exact matches there cannot be generalized to all SCUMM strip types.

## Implementation implications / acceptance targets

1. Construct a corpus *index* (code, room, object/state or background, strip number, source offset, file SHA-256) from original bytes outside Git; Git should contain only the derived, non-reconstructive metadata.
2. Expand optional private integration tests to exercise at least one authentic strip from EACH observed codec, especially one-count code 66 object and code 26 background. Never store copyrighted image bytes in Git.
3. Retain the property distinction: recognized codec ≠ successfully decompressed payload ≠ correct indexed pixel output ≠ correct object compositing ≠ observed runtime animation.
4. Independently test per-image ZP masks, position, transparency/opaque handling, and front-buffer composition on the 0/1/2/3-plane ladder; include null image state behavior and zero dimensions.
5. Keep native indexed pixels and masks as source of truth; all enhanced-resolution exports must be downstream, preserving alignment, order and depth.

Source implementation reference: https://github.com/87otlto-coder/Scummbucket/blob/research/p4-engine-palette-trace/scummbucket/object_images.py; ScummVM engine drawing behavior: https://github.com/scummvm/scummvm/blob/v2026.4.0/engines/scumm/object.cpp. Current branch development and private original-archive tests have NOT been run during this expedition.
