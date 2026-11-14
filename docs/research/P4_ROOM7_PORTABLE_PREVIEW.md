# Room 7 — portable HTML preview packaging

**Status (updated 12 November 2026):** Standalone packaging passed synthetic tests **and an automated Chromium playback check of user-supplied real Room 7 preview HTML**. Browser testing on the user's own Firefox installation is not independently observed. The 87-frame indexed reconstruction remains separately verified in its pinned capture context. See [uploaded-preview acceptance evidence](P4_ROOM7_BROWSER_ACCEPTANCE_20261112.md).

## Why the downloaded HTML was blank

The originally uploaded preview.html refers to 87 separate relative filenames, frame-001.png through frame-087.png. It contains no images. Its JavaScript waits until all 87 references decode successfully before showing frame 1. A download of preview.html and manifest.json alone therefore cannot play. The earlier sweep-20261110-a.zip contains viewport-*.png background-only previews, not the full-scene frame-*.png images.

**This is a packaging defect, not evidence of an indexed renderer mismatch.**

## Code changes

- scummbucket/standalone_preview.py validates every PNG against manifest indexed SHA-256, checks strict filenames, timestamps, 320×144 P-mode indexed geometry and PNG format, then embeds each PNG as a base64 data URL in the HTML.
- tools/verify_room7_scene.py now produces self-contained preview.html when run against a new output directory. The original 87 frame PNGs remain available separately.
- tools/package_room7_preview.py reuses an existing output folder (manifest.json + all 87 frame-*.png) to create preview-standalone.html without rerunning ScummVM or reading game archives. It never replaces the original preview.html, manifest or frames.
- tests/test_room7_standalone_preview.py covers embedded content, ordered timing, missing/corrupted frames, wrong indexed SHA-256, unsafe filenames and exclusive-create output.

## Repackage existing output on Windows PowerShell

Safely update the clean canonical repository first:

~~~powershell
$repo = 'F:\Dev\SCUMMBUCKET\SOURCE\ScummBucket'
git -C $repo status --short --branch
git -C $repo fetch origin
git -C $repo merge --ff-only origin/research/p4-engine-palette-trace
~~~

If the local working tree is dirty or diverged, stop; do not force-reset or overwrite it. Locate the actual existing output directory containing all 87 full-scene frame-*.png files and manifest.json. The Work session reported the originals under C:\Users\87otl\Documents\ChatGPT\ScummBucket\FIXTURE, not necessarily the F-drive fixture tree.

~~~powershell
Push-Location 'F:\Dev\SCUMMBUCKET\SOURCE\ScummBucket'
python -B -m tools.package_room7_preview 'ABSOLUTE_PATH_TO_EXISTING_ROOM7_OUTPUT_DIRECTORY'
Pop-Location
~~~

The script prints the new preview-standalone.html path. Open or download **that file alone**; it contains all frames and may be several megabytes. It refuses to overwrite an existing preview-standalone.html. Original archives and captures remain unchanged.

## Diagnostic limits

- Missing source images cannot be recovered from manifest.json alone, as it only stores hashes and filenames; use the original Work output directory.
- The packager validates decoded **indexed** frame bytes, not a browser's GPU output or ScummVM RGB readback.
- New standalone HTML uses browser data:image/png;base64 URLs and has no local-file dependency. If it still fails, capture browser version, developer console error, HTML file size, and whether data:image/png;base64 appears inside the file.
- Exported HTML contains copyrighted game imagery and belongs in FIXTURE, never Git.
