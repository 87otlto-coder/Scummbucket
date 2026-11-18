# P4 scene events and Room 35 implementation checkpoint

- Engineering parent: `a536b8e976e8ed59903925774ff821776e7b45c7` on `research/p4-engine-palette-trace`.
- Source checkpoint: `3f0c4bf88a3c67e74bbd66b7a76105c6c8ca21ba` on `research/mi2-spelunk-20261116`. That branch is 112 commits ahead of the engineering parent. The implementation uses the linked findings directly and leaves the research history separate.
- Source references: [mixed water loops](https://github.com/87otlto-coder/Scummbucket/blob/3f0c4bf88a3c67e74bbd66b7a76105c6c8ca21ba/docs/research/MI2_MIXED_WATER_EVENT_LOOPS_20261116.md) and [cross-room Bit92 state](https://github.com/87otlto-coder/Scummbucket/blob/3f0c4bf88a3c67e74bbd66b7a76105c6c8ca21ba/docs/research/MI2_ROOMS35_36_37_CROSSROOM_CYCL_STATE_20261117.md).
- CI: see [draft PR #19](https://github.com/87otlto-coder/Scummbucket/pull/19) for the latest Windows regression result.

## Implemented

`p4-scene-events/1` validates source identity, logical and physical rooms, optional script provenance, event families and evidence labels. Event array order is authoritative. Optional monotonic ticks require a named clock. Unknown timing and conditional outcomes can be null. Canonical JSON provides stable bytes without requiring a renderer or executing bytecode.

Room 35 uses the existing scene inventory, indexed background decoder, OBIM strip and mask decoders, palette scheduler and indexed PNG encoder. The shared OBIM API now exposes native indices, per-pixel opacity and raw object Z planes. The existing RGBA export continues to use the same decoded pixels. Room 35 renders one traversal of authored object 364 states IM01–IM08 and the two CYCL ranges from the pinned resource archive. One state sample can consume zero or more explicitly provided engine-style counter updates. Counters start at zero against the source CLUT. The preview keeps raw flags and warns about unresolved flag 0x0004. It writes the RGB palette separately from the indexed raster and includes archive, chunk and output provenance.

The source entry branch requires effective Bit92 clear. That value is evaluated after the conditional Bit567 write. The preview defaults to the authored CDHD position in eight-pixel units. See ScummVM v2026.4.0 [object.cpp](https://github.com/scummvm/scummvm/blob/v2026.4.0/engines/scumm/object.cpp) and [object.h](https://github.com/scummvm/scummvm/blob/v2026.4.0/engines/scumm/object.h) for the v5 field layout. Optional coordinate overrides and palette deltas are caller assumptions. The output draws one waterfall layer over the archive background and preserves object Z planes separately. Background Z-plane interaction, other live objects and actors, runtime draw ordering and wall-clock cadence need reference evidence.

## Windows reproduction and next validation

Run the preview from the sprint branch. Supply `$delta` explicitly. Optional `--x` and `--y` coordinates override the authored position and are marked synthetic.

```powershell
Set-Location 'F:\Dev\SCUMMBUCKET\SOURCE\ScummBucket'
$root = 'F:\Dev\SCUMMBUCKET'
$out = Join-Path $root ('FIXTURE\OUTPUT\Room35\source-' + [guid]::NewGuid().ToString())
python -B -m scummbucket.room35_waterfall "$root\FIXTURE\GAMES\MonkeyIsland2_DOS_VGA" $out --effective-bit92-clear --synthetic-delta $delta
```

## Private Windows retry

The retry used an isolated materialization of the engineering snapshot plus the nine GitHub file deltas at `8727197b5b0b92c480f816fa44b224a9923289a0`. The canonical checkout is inaccessible to Git in the Windows sandbox, so the wrapper's checkout gate remained blocked. Its fixture integrity preflight verified both archive hashes and all 87 reference frame digests. The underlying tests and compositor were run directly against canonical read-only fixtures.

- Room 35 original DOS VGA export passed at 320 × 144. Eight source-ordered waterfall samples used authored placement (128, 96) and a synthetic delta of 1. All 48 exported file hashes matched the manifest.
- Room 7 independent replay matched 87/87 front buffers (4,008,960 indexed positions, zero mismatches). Final palettes matched throughout. Disabling ZP01 produced the expected 778 mismatches.
- Private-enabled unit suite: 407 discovered, 400 passed, 7 skipped, 0 failed.
- Room 35 runtime comparison remains blocked. No paired capture was found. Four unique ScummVM saves across canonical GAMES/CAPTURES resolved to Rooms 7, 12 and 23. The existing acceptance launcher supports Rooms 7 and 23. A Room 35 natural-entry trace still needs an appropriate saved starting point and capture path.


1. Rerun the Room 7 private acceptance on the sprint branch using `tools/p4_private_acceptance.ps1 -WorkspaceRoot F:\Dev\SCUMMBUCKET -Full`.
2. Inspect Room 35's decoded object geometry and independently capture natural entry with effective Bit92 clear and set. Record logical/resource room, Bit567 and Bit92, ENCD/LSCR PCs, draw queue and other visible layers, object placement and state, timers, cycle counters, back/front/RGB buffers and Z planes. Keep capture files outside Git.
3. Pair equivalent viewport and cycle stages. Use `python -B -m scummbucket.native_frame_compare actual.indices actual.rgb reference.indices reference.rgb --width 320 --height 144` to report exact mismatch totals, first differing index and RGB values, and both input digests. The comparator does not establish capture authenticity or frame alignment. Compare isolated waterfall composition where appropriate before comparing the full engine front buffer.
4. Move on to Room 24 with captured non-repeating RNG choices and yields, then Room 22 with separate enhancement configurations. No implementation for either room is included here.
