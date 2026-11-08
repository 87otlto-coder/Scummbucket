# P2 experimental — Monkey Island 2 v5 object-image states

**Status:** First experimental native-resolution PNG and separate depth-mask decoder; *not* a verified, complete P2 renderer.  
**Sample:** The fingerprinted original DOS Monkey Island 2 resource pair, room 34, object 358.  
**No copyrighted assets** are stored in this repository.

## Source and format evidence

- Object ID **358** is paired by its `IMHD`/`CDHD` identity; its `IMHD` declares **16** state chunks `IM01` through `IM10` (hex).
- Native state geometry is **56 × 40 pixels**, or **seven 8-pixel strips**. The `IMHD` also contains additional geometry/header fields that must not be substituted for image width.
- Each state uses a `SMAP` strip-offset table. The seven 32-bit little-endian strip offsets are **relative to the start of the SMAP chunk including its eight-byte header**.
- Each state contains three separate `ZP01`, `ZP02`, and `ZP03` mask chunks. Their 16-bit little-endian strip-offset tables and RLE scanline data are **not** the same as alpha transparency. Preserve them as separately exportable layers.
- Room 34's `CLUT` contains 256 RGB entries. Its `TRNS` chunk gives transparent **palette index 5** for transparent-compression strips. This was checked against ScummVM's `setTransparentColor` handling.
- Transparent strips omit color index 5 when composing RGBA. **Nontransparent** strip modes still draw that palette index as an opaque color; do not blindly erase color 5 from every state.
- Room 34's sample uses strip modes **18, 37, 38, 68, 87, and 88**, including basic zigzag and major/minor compressed layouts. Mode **68** and **18** occur in state `IM10` and are not transparency-aware.
- A separate, read-only research prototype decoded all **16** image states into native-resolution RGBA, using room 34's palette and transparency index, and decoded all **48** Z-plane masks. This is a *structural and visual sanity check*, not a pixel-by-pixel rendering match against ScummVM.

**Visual observation:** The first 15 states show varying hand/finger-number configurations. The sixteenth image appears visually distinct and uses opaque strip modes. The earlier verified scripts 201/202 select states 1–15 or reset to 0, but no conclusion should be drawn about state 16's **global** reachability from only those two scripts.

## Implemented experimental CLI

Run the new command on the **local authorized game archive**, without downloading anything additional:

```powershell
cd "C:\Users\87otl\ScummBucket"
git pull --ff-only origin feature/p1-scumm-v5-inventory

$stamp = Get-Date -Format "yyyyMMdd-HHmmss"
$out = "C:\Users\87otl\ScummBucket\exports\room34-object358-$stamp"
python -m scummbucket images "D:\old" --room 34 --object 358 --output-dir "$out"
```

With the supported sample, the intended outputs are **16 RGBA PNG images**, **48 separate grayscale mask PNGs**, and **one manifest.json** with source offsets, original source hash, pixel-buffer SHA-256, per-strip compression codes, output hashes, and item/diagnostic statuses.

Use `--no-masks` to export image states only. The original ZIP or resource directory remains read-only. Existing files are never overwritten; an existing manifest blocks the operation. Per-state decode errors must appear as explicit failures, with a `partial` operation status if other states succeeded.

This command does **not** generate an animation, run scripts, assign frame timing, scale images, or composite depth masks against the room's background. It requires no Pillow or graphics-library runtime dependency; PNG encoding uses Python's standard library.

## Verification gates

1. **Synthetic unit tests:** Verify constant-color zigzag and major/minor strips, transparent vs opaque handling, RLE depth masks, PNG headers, malformed strips, unsupported codecs, missing palette, file overwrites and unchanged source archive.
2. **Private integration test:** `tests/test_private_mi2.py` optionally checks all 16 states and 48 masks against the fingerprinted archive, plus two expected RGBA pixel SHA-256 values. This is skipped in public CI because the original archives are not stored there.
3. **Pending:** Independent pixel-for-pixel comparison against ScummVM reference rendering (including palette modifications at runtime and masked background compositing).
4. **Pending:** Verify state-0 behavior, state-16 use in other scripts, original pixel aspect ratio on screen and room-level object placement.
5. **Pending:** Test codec coverage and safe diagnostics across a representative range of other MI2 room objects and editions.

Do not promote this experimental decoder to **fully faithful P2 coverage** until the last three gates have evidence.

## Architectural notes

- Use resource IDs and chunk source offsets, not guesswork from sequential image filenames.
- Native indexed source colors and the active room palette are separate concepts. The current exporter writes room-initial RGBA colors; script-driven palette changes may alter actual appearance during play.
- **Z-plane bitmaps govern occlusion/layering, not object transparency.** Keep mask filenames and tags distinct from the RGBA PNG alpha channel.
- Nearest-neighbor asset-level scaling and high-quality pixel-art enhancements remain future export options; avoid rescaling within the low-level decoder.
- No GPL source code has been copied. This is a small independently written parser based on documented v5 file structures and algorithm behavior, cross-checked against [ScummVM's gfx.cpp](https://github.com/scummvm/scummvm/blob/master/engines/scumm/gfx.cpp), [gfx.h](https://github.com/scummvm/scummvm/blob/master/engines/scumm/gfx.h), [object.h](https://github.com/scummvm/scummvm/blob/master/engines/scumm/object.h) and [room.cpp](https://github.com/scummvm/scummvm/blob/master/engines/scumm/room.cpp).

## Current evidence classification

| Capability | State |
| --- | --- |
| OBIM state identity and geometry | Directly parsed from original archive |
| Seven-strip SMAP offsets and codec types | Directly parsed |
| RGBA reconstruction of 16 sample states | Experimental decoder and separate reference prototype agree visually; **not independently pixel-verified** |
| Three mask planes per sample state | Directly decoded into separate buffers; **compositing not yet verified** |
| Script 201/202 state selection formula | Independently disassembled; not observed in live rendering |
| Automatic room background animation | **Not established by object 358** |
