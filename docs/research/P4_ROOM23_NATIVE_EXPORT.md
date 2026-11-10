# Room 23 native background export

The command exports one indexed PNG per post-cyclePalette callback and a local HTML player. It accepts the fingerprinted DOS VGA edition and an SBP4 Room 23 log with a uniquely resolved first-segment phase, a matching held-out sample set, and an exact full-palette match at every sample. An incomplete trace remains incomplete. PNG generation and playback need no optional Python packages. Open play.html and press Play. The player preloads the frames, starts at sample 1, follows their recorded offsets on the browser clock and stops on the last image. Browser refresh can skip short or coincident states. The PNGs and manifest preserve every callback.

## Reproduce on Windows

From F:\Dev\SCUMMBUCKET\SOURCE\ScummBucket with the private fixtures available:

```powershell
$root = 'F:\Dev\SCUMMBUCKET'
$game = "$root\FIXTURE\GAMES\MonkeyIsland2_DOS_VGA"
$log = "$root\FIXTURE\CAPTURES\Room23\room23-normal-20261110-081315-043.raw.log"
$stamp = Get-Date -Format yyyyMMdd-HHmmss-fff
$out = "$root\FIXTURE\OUTPUT\Room23\native-$stamp"
python -m scummbucket export-room23-capture $game --raw-log $log --output-dir $out
```

The destination must be new. The manifest is written last. A directory left without it after an I/O failure is incomplete. Re-run in a fresh directory. Manifest paths identify the local input files. Reusing the same input paths on this machine produced 89 byte-identical files, including the player and manifest. Moving the inputs changes their path strings.

## Evidence from the mixed capture

| Item | Verified value |
| --- | --- |
| Resource and index-plane fingerprints | See [archive and plane evidence](P4_ROOM23_VGA_SPATIAL_VALIDATION.md). Both are checked before export. |
| Raw log SHA-256 | 591c06aa6f518e48ef6e8da1b45f4bc357179640ac8c1fb506d6a1f9488a5e73 |
| Sequence | 87 callbacks, 13,590–88,008 ms. Sample 27 holds 12,828 ms until sample 28. Final hold unknown. No END. |
| Phase | Equivalent source-model update 331 in a search of 1–500. Samples 1–3 selected the phase. Absolute room-entry phase is unknown. |
| Palette | Eight archive CYCL ranges supply 16 colors. BEGIN supplies the remaining 240 entries, including overrides at 1, 2, 3 and 6. |
| Prediction | One max(timer, timer_next) update per sample across the gap. The private regression read back every PNG palette against the raw trace. All 87 matched, including all 84 held out. |
| Spatial data | All 87 PNGs retain the same 320 × 144 index plane. Only 480 of 46,080 positions use cycled indices. |
| Manifest SHA-256 in the sample export | cc0caecd93c1ea6c975432701977ed393f19c1bef1f9a3929c0d86ba7ea897c2 |

The manifest records archive member labels and hashes, room chunk offsets, CLUT and index hashes, raw capture identity, original timer pairs, capture clocks, per-frame intervals, predicted rotations and file hashes. The trace samples before palManipulate. Its header does not identify the executing binary.

## Comparison with independently recorded ScummVM video

Run the comparison with Pillow available and an FFmpeg executable under TOOLS. The example uses imageio-ffmpeg 0.6.0 for its bundled executable. To reproduce all rows, substitute the recording, seed, scale and times in the table below. Choose a fresh report directory for each call.

```powershell
$ff = (Get-ChildItem "$root\TOOLS\room23-video-0.6.0" -Recurse -Filter 'ffmpeg*.exe')[0].FullName
$ref = "$root\FIXTURE\REFERENCE\Room23-native-20261110"
python tools/compare_room23_video.py --export $out --ffmpeg $ff --video "$ref\Recording 2026-11-08 114050.mp4" --output "$root\FIXTURE\REPORTS\Room23\vga-$stamp" --origin 3 4 --scale 1 --seconds 1 10 19
```

The tool checks every PNG and index hash, fixes registration on upper-sky scanlines in the first selected video frame, and averages each 2 × 2 block for the doubled capture. For each timestamp it picks the earliest exported frame with minimum summed RGB error over the 480 cycle positions. That selection gives an optimistic appearance comparison. It cannot verify callback timing across runs. JSON includes the video hash and FFmpeg version. The comparison sheet shows the export, the aligned video and a 4× amplified absolute difference.

| Nov 8 recording | Crop origin, scale | Seconds | Selected export samples | Median max-channel error on 480 cycle pixels | Median on 41,069 other pixels* |
| --- | --- | --- | --- | --- | --- |
| 114050, 324 × 208 VGA | (3,4), 1× | 1, 10, 19 | 24, 15, 32 | 12, 9, 9 | 8, 6, 6 |
| 120927, 650 × 308, visibly dithered | (4,11), 2× | 1, 8, 16 | 9, 9, 9 | 27, 27, 27 | 22, 23, 22 |
| 164044, 1886 × 988, native room inside window | (780,403), 1× | 28, 32, 36 | 27, 1, 28 | 10, 10, 11 | 7, 7, 7 |

*The other-pixel group excludes the cycle indices and fixed cabin and actor study rectangles; the actor moves outside the latter in the other recordings. Channel errors are on a 0–255 scale.

- **Spatial image and palette.** The sky, wrecks, jetty, cabin and foreground post register in the native VGA comparison. At 10 s, 37/480 cycle pixels and 3,207/41,069 other pixels still differ by at least 20 in one channel. The separate trace establishes exact palette agreement at the hook. The compressed RGB videos cannot reveal the displayed index values or separate all palette and pixel errors.
- **Actors and objects.** Guybrush is visibly absent from the export. At 10 s the VGA actor rectangle contains 893/2,491 noncycle pixels over the same threshold. This is a rectangle count, not a silhouette count. The inventory pairs room objects 241, 242 and 243 with OBIM/OBCD headers. All three OBIMs declare and contain zero image states. No object sprite was inferred from the cabin residual.
- **Masking.** RMIM includes ZP01 and ZP02. The exporter draws the opaque background without actors or depth compositing. These captures do not isolate an occlusion error from the missing actor layer. Runtime depth selection, object state and exact mask behavior remain unverified.
- **Rendering.** The dithered recording's residual covers the sky and land as well as the water. No cycling phase can change those fixed sky indices. Lossy video, color conversion, display mode and scaling affect the comparison. Their individual contributions are unmeasured. The UI below the room is excluded by the crop. Scripts, subsequent palette effects, camera motion, actor animation and display presentation are outside the export.

A lossless room framebuffer and final palette captured on the same callback, together with actor/object and depth state, would permit a frame-synchronous scene test. This milestone verifies the recorded background palette sequence and its native geometry.
