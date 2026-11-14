# P4 Room 7 — native exterior animation export acceptance

**Date:** 14 November 2026  
**Scope:** Monkey Island 2: LeChuck's Revenge, original DOS VGA, Room 7 exterior  
**Status:** **Passed for the recorded 1,149-frame exterior route; not generalized.**

## Evidence received and provenance

The operator submitted the private export ZIP
navigation-native-698a906f40ab43039ebe0bd75af24fab.zip.
It was audited directly against the previously supplied raw
navigation-01f10e8856574e3a8af15fcf1624e890.zip, containing the original
engine-*.bin and present-*.bin records under
navigation-b9d905869e894798b5d7744caaf66a5a.

| Evidence | SHA-256 |
| --- | --- |
| Native export ZIP | 8ba6957f77f2ff274218e8066fe4c1a8f27c991922e38d31ac6b7efc9e0757f6 |
| Raw navigation capture ZIP | 5da87d59018f2bcdbd907e51dfa3666f2dc1d98dfc8d30e65d8e42d975ac024d |
| Export animation.json | 2c9606a85358da9cf254d7de9c35dbedf8f4a509449099a8188a0ba058ee1974 |
| Export navigation.json | 772fe65fa8edbda456973de6bc31f400a6fda2b3a1843e9f13d2069a55866826 |
| Original archive MONKEY2.000 | cde7aa8980317e3a750fbb3b49884cdddaf1ff3d4231a0c840b22cceed9033f1 |
| Original archive MONKEY2.001 | ad045372e0d49626503bb50fca29a687ec8e01ef75d9b8bca702a366d143819e |

Both ZIP archives passed CRC checks. The export ZIP has 1,757 entries:
1,149 native frame PNGs, 603 ZP01 mask overlays, one route PNG,
animation.json, navigation.json, play.html and one folder entry.

## Independent raw-engine verification

The audit reopened both ZIPs and independently decoded **all 1,149**
captured engine and presentation binary records, cross-checking each against
the hashes and metadata in navigation.json. For every frame:

1. Recovered the captured engine indexed front buffer (320 x 144, 46,080
   positions), final 768-byte palette, and full 320 x 200 indexed backend.
2. Checked backend's displayed room crop against the indexed front.
3. Decoded the exported indexed PNG and compared **every index byte** to the
   captured engine front. Did not use reported mismatch counts as proof.
4. Matched the complete PNG palette to the **actual captured final engine
   palette** and checked PNG/pixel/palette SHA-256 values in animation.json.
5. Reopened the paired present-*.bin file and cross-checked frame ID, raw
   file hash, SDL timestamp, and 320 x 200 RGB byte length.

| Check | Result |
| --- | ---: |
| Reopened engine/present pairs with matching SHA-256 | 1,149 / 1,149 |
| Exact indexed front buffers versus independently exported PNGs | 1,149 / 1,149 |
| Indexed-pixel observations | 52,945,920 |
| Indexed-pixel differences | **0** |
| Exact final palette from original engine binary | 1,149 / 1,149 |
| Exact SDL presentation timestamps | 1,149 / 1,149 |
| Distinct indexed rasters | 265 |
| Distinct final palettes | 163 |
| Original navigation-report mask-off control errors | 81,234 (reported, not recomputed in this audit) |

The raw capture manifest's game archive hashes match the animation export's
archive hashes. Every navigation row reports zero masked reconstruction
errors. This stronger cross-check **does not simply accept those claimed
errors**: it independently compares the resulting PNG index bytes to the
raw engine front for every frame.

## Continuous playback segments

| Segment | Export frames | Engine ticks | Presentation milliseconds |
| --- | --- | --- | --- |
| Before ship interior | 1–961 (961 frames) | 1–961 | 1,432–97,433 |
| After return | 962–1149 (188 frames) | 1113–1300 | 112,635–131,334 |

The gap of **151 unrecorded ticks** is preserved. The player's separate
segment selection does not fabricate Room 12 images or interpolate these
ticks. A separate continuous Room 7–12–7 capture verifies the doorway
mechanism; it must not be spliced into this different run without explicit
provenance and synchronization.

The contact sheet sampled export frames 1, 448, 470, 961, 962, 972, 987
and 1149 at twofold nearest-neighbor display. It shows the right cliff,
the ship threshold, and exterior return at the correct respective camera
views and Guybrush coordinates. This is a qualitative visual inspection,
not a separate computer-vision assertion of costume pose.

## Evidence boundaries and open work

- The source index-plane reconstruction is validated **only** for this
  captured route and edition; it does not demonstrate arbitrary navigation.
- The export palettes and presentation times are **engine-observed inputs**,
  not autonomously predicted by a new SCUMM script interpreter.
- All final PNG pixels reproduce the **engine indexed front**. This audit
  does not assert RGB equivalence after SDL RGB565/display processing.
- The 151-tick interior interval and **Room 12 scene rendering** are not
  included in this exterior export.
- The 81,234 mask-off differences are inherited from the accepted navigation
  report; this audit separately verified all mask-on indexed pixels, not
  the mask-off compositor.
- Playback source and segment manifest were inspected, but an automated
  browser run on this particular uploaded package was **not** performed.
- Archive game bytes, costume images, frame PNGs, engine captures, ZIPs and
  operator video remain under private FIXTURE/attachments, **never Git**.

**P4 milestone accepted:** Segment-aware native Room 7 animation export
with preserved camera, archive COST scenery and Guybrush, ZP01 clipping,
recorded palette evolution and timing. Do not merge draft PR #8 to main
without explicit owner approval. Next work should generalize this bounded
mechanism to a second representative animated room or add an independently
verified Room 12 compositor, with separate validation per input edition.
