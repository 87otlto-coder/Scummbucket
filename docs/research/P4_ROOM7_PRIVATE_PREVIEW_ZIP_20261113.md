# P4 Room 7 — uploaded private preview archive check, 13 November 2026

**Evidence class:** independent inspection of a user-supplied ZIP containing generated PNGs, a manifest and a self-contained HTML player. Unlike the separate Windows private acceptance, **this check does not reread the original MONKEY2 archives or 87 engine-capture binaries**. No copyrighted image bytes are committed here.

## Supplied archive identity and structure

- Uploaded name: `frame-001.zip` (this is a complete exported sequence despite its name).
- ZIP SHA-256: `aa20a8107ee458a27089c733beab72e670dd185a94ef9ae18e5be288bb7d99e9`.
- ZIP file size: **4,568,416 bytes**.
- Members: **89**; **87** sequential `frame-001.png` through `frame-087.png`, plus `manifest.json` and `preview.html`.
- No missing numbered frames. All PNGs: indexed `P` mode, exactly **320 × 144** pixels.
- Manifest SHA-256: `d8c13b5789cbc2e3ee31e899e2e6f0086c271566c04d7e076e1c3b236cf22373`.
- HTML SHA-256: `cf3051f9b2e4c5981c4db3af8b4e290a46c4e6d4e880398e269c625882873bd9`.
- HTML size: **3,018,192 bytes**, containing **87 embedded PNG data URLs**; no external scripts or remote URLs found.

## Independent content checks

- Decoded each PNG and hashed its exact indexed byte buffer; **87/87** matched their per-frame `indexed_sha256` fields in `manifest.json`.
- Unique indexed images: **65**; unique palette byte arrays: **35**.
- Exactly **64** of the 86 adjacent indexed-frame pairs differ. Static-index intervals may still contain real palette changes: independently found **7 palette-only transitions** ending at frames **65, 70, 71, 72, 76, 77 and 80**. Do not treat repeated indexed frames as lost animation.
- Manifest contains sequential frame IDs **1–87**, non-decreasing `time_ms`, and viewport camera X spanning **0–464** (59 distinct camera positions). All manifest `mismatches` values are **0**, summing to zero; all manifest `unmasked` values sum to **778**. These per-frame comparison counts are *manifest assertions*, not independent engine-buffer comparisons from the ZIP itself.
- Nine representative frames (1, 6, 15, 30, 45, 63, 70, 81 and 87) were visually reviewed as a contact sheet; the harbour pans to the bridge with no obvious blank/corrupted images in those samples. This is not an exhaustive human pixel-quality assessment.

## Browser playback check

The exact embedded `preview.html` contents were loaded through Playwright `page.set_content` in **headless Chromium** with no network dependencies. The browser environment blocks `file://` navigation by policy, so this check **does not verify local file-URL launch**.

Observed:

1. 87 embedded images decoded and the Play button became enabled; first image natural width 320.
2. Clicking Play disabled the button while animation progressed.
3. The player finished at the last (87th) image, with its image loaded, and re-enabled the button.
4. No JavaScript page errors were raised during this check.

**Result:** self-contained HTML playback passed in headless Chromium; PNG and manifest internal integrity passed.

## Scope and follow-up

The separate [13 November Windows private acceptance](P4_PRIVATE_ACCEPTANCE_20261113.md) checked the original local engine buffers at research commit `4ffac2a2bcba6e19508bb4098d34da8ee57fab7b` and reported **87 × 320 × 144 indexed comparisons, 0 mismatches**. The ZIP inspection independently corroborates *exported-file integrity and playback*, not those source-buffer comparisons.

Still open: local Windows Firefox `file://` playback if required, *natural gameplay entry* rather than debugger-equivalent Room 23→7 jump, generalized room/edition coverage, remaining optional private checks, and owner-approved license/source-lineage decision for draft PR #8. The report and ZIP remain private; only aggregate data/hashes are tracked in Git.
