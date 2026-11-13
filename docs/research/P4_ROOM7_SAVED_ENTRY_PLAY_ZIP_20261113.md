# Room 7 saved-entry background preview ZIP — 13 November 2026

**Evidence class:** Direct inspection of user-supplied `play.zip` in the
conversation environment; the archive's embedded `report.json` quotes
results of a separate private Windows engine comparison. **Not a new
saved-counter-forecast result.**

## Input identity and inventory

Uploaded archive: `play.zip`, SHA-256
`0f0945f8bb9948a688d5b4d46cdd063c327a8c49a9a880da52c2b0d2c224863e`.
ZIP CRC validation succeeded; 89 entries: `play.html`, `report.json`,
and `viewport-001.png` through `viewport-087.png`. No other files.

The report uses schema `room7-sweep/1`. The `run` section records a
non-debugger, non-injected ScummVM Room 7 saved-entry capture; the save hash
is `39035338ed89bdfe754f31e390f247c83095f1938aeae6877c0373ad7f72aa0d`
and corresponds to the user-supplied `monkey2-1.s01`. The embedded
provenance correctly reports `natural_gameplay_entry_verified:false`.

## Independent consistency checks on the ZIP itself

- 87 numbered viewport PNGs, all indexed `P` mode at **320×144**.
- The actual underlying **indexed pixel buffer is identical across all
  87 PNGs**. This is a palette-animation/background-only export.
- **41 distinct palette buffers** across the 87 images; the PNG palette
  matches `frames[n].palette_stages_sha256[3]` for **87/87** frames.
- Exactly **582 of 46,080 viewport pixel locations** exhibit an RGB color
  change at some point. All are within image **Y=99..142**, consistent
  with the water region beneath the rope bridge. The palette-cycling
  color index groups are **16–18, 176–185**.
- The HTML references **all 87 existing PNG filenames exactly once**;
  frame times increase strictly, from 0 through **8599 ms**.
- The original frame files and ZIP have not been altered or committed
  into Git. A scaled single-frame visual inspection showed the rope-bridge
  and water backdrop but no actor sprites.

The accompanying report (which cannot be independently cross-checked
against raw engine binaries because they are **not inside this ZIP**)
records 0 background-index differences, 0 depth-mask differences, and
0 engine front-to-backend differences across 87 frames. It also records
`front_vs_background=2730` pixels per frame / `237510` total, i.e.,
drawn actor/object content **not reproduced in the background-only PNGs**.
The camera is fixed at X=464; the serialized actor/object state strings
are the same for all 87 report frames.

## Browser test status

All referenced images exist and the HTML timeline is structurally valid.
An attempted headless Chromium playback was blocked by the environment
(`ERR_BLOCKED_BY_ADMINISTRATOR` on both local file and loopback URLs),
so **actual browser playback remains unverified in this review**. This
restriction is not evidence of a defect in the package.

## Stronger portable cross-check — direct saved counters versus all 87 palettes

After the initial preview inspection, the **original private save**
`monkey2-1.s01` was confirmed to remain mounted in the conversation
sandbox. Its SHA-256 matched the embedded `report.json` save fingerprint.

A separate, read-only Python calculation independently:

1. Gzip-decompressed the v124 save without changing its bytes.
2. Scanned every possible offset for the 16 serialized ColorCycle records
   matching the six *previously archive-decoded* Room 7 cycle definitions.
   Exactly **one** matching 128-byte block was found, at decompressed
   offset **80203**, with saved counters **12, 12, 26, 35, 13, 80**.
3. Verified that **each of the 87 PNG palettes** is byte-identical by SHA-256
   to that frame's captured `palette_stages_sha256[1]` and
   `palette_stages_sha256[3]`. For frame 1, reported pre/post/final
   palette hashes were equal, permitting use of the first PNG palette as
   the initial pre-cycle buffer.
4. Started the six independently decoded CYCL schedulers with exactly the
   counters found in the **save**, then applied the reported per-frame
   `max(VAR_TIMER,VAR_TIMER_NEXT)` delta. It did not fit, reseed,
   reset or modify counters according to observed post-cycle palettes.
5. Compared **all 256 RGB triples (768 bytes)** at **every frame** to
   that frame's actual PNG palette.

**Result: 87/87 exact 768-byte palette predictions, zero mismatches**.
There were **45 palette-changing transitions** between consecutive
frames. The previously ambiguous 11 held-out predictions now have
deterministic exact matches using separately serialized counter values.

**Evidence qualification:** this comparison independently used the save
and preview PNG palette bytes against archive-defined cycle math, but
the raw `engine-NNN.bin` files were not included in `play.zip`.
The PNG palettes' hashes are bound to the captured engine palette hashes
recorded in the supplied `report.json`, and the operator's earlier
private capture validator checked 87 frame pairs. Thus the result
strongly corroborates correct saved-entry palette cycling for **this
specific captured save state**, but is not a new raw-engine-binary
validation or general support for all game states and editions.

The source-backed `tools.verify_room7_saved_palette_counters` still
provides the stronger local private-binary comparison and should be
executed when completing this integration checkpoint. Do not state that
its user-side run has already occurred merely because this ZIP cross-check
passed.

## Boundaries and next work

The bundle and separate save-counter cross-check support an accurate
**static indexed background with palette-cycling water** for this one
saved state. The archive is **not** the output of the source-backed
`tools.verify_room7_saved_palette_counters` command; it contains neither
that tool's JSON nor raw 87 engine frame binaries. The separate
save-plus-preview cross-check did yield **87/87 correct palettes**, but
the private engine-binary comparison remains an independent final gate.

The outstanding next report is the unique, non-overwriting private
`FIXTURE/REPORTS/Room7/native-save-72c00ab603b64f9597b10cf952c9662e-saved-counters-unfitted.json`.
Preserve and report any zero-counter versus restored-counter discrepancies,
rather than promoting the partial fitted-phase studies to full success.
