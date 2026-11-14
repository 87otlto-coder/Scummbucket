# P4 Room 7 — direct saved-game ColorCycle counters (13 November 2026)

**Evidence class: directly decoded, user-provided private ScummVM v124 save
bytes, checked against independently decoded Room 7 archive CYCL definitions.**

## Upstream serialization

ScummVM `engines/scumm/saveload.cpp` serializes
`_colorCycle[16]`, each through `syncWithSerializer(ColorCycle &)`:

`delay:uint16LE, counter:uint16LE, flags:uint16LE, start:byte, end:byte`.

This is an exact, version-aware **8-byte structure**, not a heuristic
interpretation of arbitrary game payloads. See:
https://github.com/scummvm/scummvm/blob/master/engines/scumm/saveload.cpp

## Direct evidence from uploaded monkey2-1.s01

The user-supplied gzip-wrapped `SCVM` version 124 save, SHA-256
`39035338ed89bdfe754f31e390f247c83095f1938aeae6877c0373ad7f72aa0d`,
has Room 7 serialized as both current room and room resource.

A full scan found exactly one **128-byte 16-slot ColorCycle block** whose
six populated slots match the *independent archive* Room 7 cycle
delays, flags and color ranges. The remaining ten serialized slots
are entirely zero. The decoded block begins at **decompressed offset
80203**, which is retained as provenance only—not hardcoded in the
parser (offsets can change with other save data).

| Cycle | Palette color range | Delay | **Saved counter** |
| --- | --- | ---: | ---: |
| 1 | 16–18 | 42 | **12** |
| 2 | 176–177 | 42 | **12** |
| 3 | 178–179 | 35 | **26** |
| 4 | 180–181 | 53 | **35** |
| 5 | 182–183 | 71 | **13** |
| 6 | 184–185 | 107 | **80** |

All flags are zero. All six counter values are in the expected normalized
range. This is **direct save data**, not fitted from the 87 saved-entry
runtime frames. No private save contents are committed.

## New safe decoding implementation

`scummbucket/scummvm_color_cycles.py` uses the existing bounded v124
save inspection and independently decoded archive cycle definitions to
locate/validate exactly **one** complete 16-slot block. It checks every
active delay/flag/range and all inactive slots, and fails if the block
is absent, duplicated or inconsistent.

**Crucial limitation:** serialized save counters can differ from counter
state at the first observed post-load cyclePalette call. Normal load logic
may run one or more timer updates before the first captured frame, or
otherwise change palette state. No such adjustment is assumed here.

This opens a stronger follow-up test: initialize the cycle scheduler
with these **saved counters without any phase fitting**, using the first
observed pre-cycle palette and per-frame timer increments, and compare
all 87 post-cycle palettes. Preserve any mismatch, first mismatch frame,
affected color ranges, archive hashes and counter provenance.

The prior calibration experiments remain separately documented:
24/63 = 52 exact, 11 ambiguous; 36/51 = 43 exact, 8 ambiguous;
48/39 = 35 exact, 4 ambiguous; all had zero **determinate**
mismatches. They are overlapping experimental windows from the same run,
not three independent captures.
