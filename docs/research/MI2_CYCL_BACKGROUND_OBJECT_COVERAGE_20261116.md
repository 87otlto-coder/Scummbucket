# MI2 CYCL source-pixel reachability — backgrounds vs object images (2026-11-16)

**Read-only original-archive research, not runtime animation verification.** Source member MONKEY2.001 stored-byte SHA-256 `ad045372e0d49626503bb50fca29a687ec8e01ef75d9b8bca702a366d143819e`. A private standard-library/Python strip decoder using the documented v5 SMAP codec families walked all **21 rooms** with CYCL chunks, their `RMIM/IM00/SMAP` native source pixels and every stored `OBIM/IMxx/SMAP` image state. Transparent index was excluded where a transparency-aware codec declares it. No compressed strip decode failed in this narrow 21-room exercise; **independent indexed output comparison to ScummVM has NOT been run**. No source art or decoded pixel data is committed.

A CYCL range may exist in metadata but affect neither static background nor image states, or may affect object pixels absent from the background. Never conflate these with proof that palette changes are executed in gameplay.

## Full 127-record classification by decoded source index overlap

These counts are **per cycle record** (not distinct visible pixels), and `object` means at least one pixel in **any stored object-image state** of that room, not an object that was actually displayed.

| CYCL coverage class | Records | Meaning |
| --- | ---: | --- |
| Background only | **88** | Source background uses >=1 index in CYCL range; no stored object-image state uses it |
| Background **and** object image | **29** | Both source graphics families use the cycle range |
| **Object image only** | **3** | No source background pixel uses cycle range, but stored object image does |
| Neither background nor object images | **7** | No overlap in those sources; could still affect costumes, scripts, external assets or be ineffective |
| **Total** | **127** | Every CYCL record classified once |

This is significant for P4: a background-only palette coverage map can miss animation affecting overlaid objects even if the palette entries rotate correctly.

## Object-only palette-cycle records

All **three** are in **Room 22**, specifically CYCL IDs **6,7,8** covering index ranges **186–187,188–189,190–191**. They are absent from the decoded source background but appear in object **240 / IM01**: respectively **15,24,5** nontransparent source pixel occurrences. Its room contains a ship-interior scene in a *private unverified native image preview*. The picture's storage in an OBIM is proven; script-controlled visibility and active runtime cycling are not.

**Practical consequence:** validating Room 22's background in isolation can report no change for those three cycles while the room's composited graphical appearance may still depend on them. Later verification must compare palette index effects on every visible layer, not only `RMIM`.

## Mixed background/object palette candidates

| Room | CYCL records | BG source index occurrences in all cycle ranges* | Object source index occurrences across stored states* | Object states using >=1 range | Main object IDs | Research target |
| ---: | ---: | ---: | ---: | ---: | --- | --- |
| **24** | 8 | 1,690 | 1,698 | 3 | 246 | Three stored water/foam states plus CYCL |
| **28** | 9 | 4,918 | 4,826 | 11 | 266,269,272,273 | Pier water/ripple, multiple objects and CYCL |
| **35** | 2 | 4,794 | 2,553 | 8 | 364 | Waterfall/running water object and two anomalous flag-4 CYCL ranges |
| **51** | 12 | 1,641 | 239 | 3 | 589 | Largest cycle-record count and object overlap |
| **81** | 7 | 522 | 228 | 3 | 780 | Smaller mixed image/palette target |

*These are sums of source occurrences over each cycle range; overlapping ranges, if present, can double-count. Object totals aggregate *alternative image states* and must not be treated as simultaneously rendered pixel counts. Exact final frame coverage requires selecting an actual object state and applying layering/occlusion.

**Room 35 specifically:** source CYCL1 colors 176–191, raw rate 3072, flags **0x0004**; CYCL2 colors 160–175, rate 2688, flags **0x0004**. Both color ranges have source pixels in background and object 364. The source-native preview depicts a waterfall, with object 364's eight states containing water fragments. The known `CYCLE_FLAGS_UNVERIFIED` warnings stay open: ScummVM v5 `cyclePalette()` uses flag bit 1 (`flags & 2`) for direction and does not use flag bit 2 in the examined code path. That does not resolve original DOS meaning. The numerical availability of source pixels is **not an executed cycle trace**.

**Room 24:** object 246 contains three stored states with 566/566/566 palette-range pixel occurrences, while the background also uses relevant cycling indices. The private source-native visual appears to be a waterline/foam component alongside a ship. An object-state loop cannot be inferred from three frames alone; it is a promising cross-mechanism candidate.

**Room 28:** nine cycles cover many background indices and 11 object states across IDs 266,269,272,273. A private source image shows pier-side ocean imagery and ripple-like graphics. Source palette ranges can affect both the static water and overlaid image components. Actual component order, cadence, and visibility remain unknown.

## Seven cycles with no static background/OBIM coverage

| Room | CYCL records | Ranges | Comment |
| ---: | ---: | --- | --- |
| **53** | 4 | 178–181,182–185,186–189,190–191 | No source overlap in background or object images |
| **64** | 2 | 189–191, 97–98 | No overlap; second record retains abnormal raw flags **0xD906** and rate **65494** (zero engine delay) |
| **89** | 1 | 130–131 | No overlap; earlier simple-cycle candidate has no source background/object coverage |

For these three rooms, the **COST resources stored in the same bundle** were also checked by reading their source palette-index tables (format 0x58/0x59 only): Room 53's six linked COST resources (11,15,18,64,66,117) have **no palette-index overlap**; Room 64's linked COST 42 also has none; Room 89 has no COST bundled. This is a **storage-only** control, not an exhaustive actor costume investigation: actors can use costumes stored elsewhere, scripts can remap palette entries, and runtime state can differ.

Do **not** label the seven cycles broken/dead based on these three static source channels. Preserve diagnostic status `NO_STATIC_BG_OBIM_BUNDLED_COST_COVERAGE` as a *candidate* with explicit provenance. In particular, do not suppress the two existing Room 64 warnings for high flags/delay zero.

## Follow-up priority / verification ladder

1. **Room 22**: record and verify source index coverage for object 240; compare actual Room 22 palette changes on the composited object layer while background-only predictions are held fixed.
2. **Room 24**: disassemble image-state callers for object 246 and capture a real three-state sequence alongside actual engine palette RGB and timers. Confirm palette applied to current object state, then test exact indexed compositing.
3. **Room 35**: verify active runtime palette cycles with raw flag 0x0004 and object 364's possible state changes. This is a priority compound animated-waterfall case.
4. **Room 28**: after isolated cases, study multiple object IDs, nine CYCL ranges and layered water effects.
5. **Rooms 53,64,89**: trace external costumes and global script palette effects. No decoded source-use does **not** prove the cycles never run.
6. **Room 36**: background contains nine transparency-aware SMAP strips. Source index overlap was measured but the final background under those strips may depend on prior compositing; retain that limitation.

What completion would require: source hashes; exact per-cycle pixel masks at each active object state; script and global palette dependencies; real engine palette/timer trace; independent per-update indexed/RGB framebuffer match; documented phase/limitations. No such live tests were run in this session.

Reference:
- https://github.com/scummvm/scummvm/blob/v2026.4.0/engines/scumm/palette.cpp
- https://github.com/87otlto-coder/Scummbucket/blob/research/p4-engine-palette-trace/scummbucket/palette_coverage.py
- https://github.com/87otlto-coder/Scummbucket/blob/research/p4-engine-palette-trace/scummbucket/object_images.py
