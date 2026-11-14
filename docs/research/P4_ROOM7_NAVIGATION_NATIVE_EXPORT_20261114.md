# P4 — Room 7 native navigation animation export

Date: 14 November 2026. **Scope:** Monkey Island 2 original DOS VGA,
Room 7 **exterior only**, from a previously independently verified,
ordinary-controls Room 7 navigation capture. No new ScummVM recording,
room interpreter or BigR scaling.

## Why this is a separate acceptance step

The existing 1,149-frame Room 7 exterior navigation analyser established an
exact indexed-pixel comparison against real engine front buffers with
archive-decoded Room 7 SMAP, ZP01, COST 1 (Guybrush) and COST 142
(script-positioned scenery actor 11). The analyser originally emitted
navigation.json, mask overlays and the route image, **not complete portable
independently rendered scene frames**. The new optional --export-native
mode emits a native 320x144 P-mode PNG for each independently rendered and
zero-mismatch verified exterior frame.

The original recorded sequence has 1,149 Room 7 engine/presentation pairs.
Exterior frames 961 and 962 came from engine ticks 961 and 1113 respectively.
**151 interior ticks were absent from that capture**. This export splits
playback at this boundary. It does **not** fill Room 12 with duplicated exterior
frames, interpolate a teleport or claim a continuous two-room video.
A separate successful Room 7 -> 12 -> 7 script-traced capture exists; see
P4_ROOM7_DOORWAY.md. It is a distinct run, not spliced into this export.

## Composition and provenance

For every capture pair the pre-existing analyser independently reconstructs:
- the original 320x144 viewport crop of the archived 784x144 Room 7 background;
- scenery actor 11's archive COST 142 cel, positioned from engine-observed
  actor coordinates and camera X;
- scaled Guybrush from archive COST 1 using engine-observed draw pose and
  scale, retaining draw state on unsampled ticks only inside its continuous
  segment;
- foreground occlusion from original ZP01 applied according to the engine
  trace's draw plane.

The composited image is compared to the independent raw *indexed* ScummVM
front buffer. Only an exact comparison is accepted for export. The PNG's
256-color palette is the actual recorded fourth/final engine palette stage:
**it is engine-observed, not independently derived from counters in this mode**.
Presentation timestamps likewise come from the paired raw SDL capture.
This work exports real observed timing without creating a new script interpreter.

Each PNG, its 46,080 source index bytes and its palette are individually
SHA-256 recorded in animation.json. The report also distinguishes source
archive hashes, capture path, scene geometry, native-image data sources and
the limitations. animation.json is written **last**, as an acceptance marker.
A partial directory without it is a failed or incomplete attempt.

## Operator command (Windows PowerShell)

This reads the pinned original game archives, existing accepted navigation
capture and pinned native panorama; it never launches ScummVM or overwrites
old reports. Run from a clean research branch checkout:

~~~powershell
$ErrorActionPreference = 'Stop'
Set-Location -LiteralPath 'F:\Dev\SCUMMBUCKET\SOURCE\ScummBucket'

$branch = 'research/p4-engine-palette-trace'
if ((git branch --show-current).Trim() -ne $branch) {
    throw 'Unexpected branch; do not reset or switch the checkout'
}
if (git status --porcelain) {
    throw 'Working tree is dirty; inspect changes before updating'
}
git fetch origin $branch
if ($LASTEXITCODE -ne 0) { throw 'Fetch failed' }
git merge --ff-only "origin/$branch"
if ($LASTEXITCODE -ne 0) { throw 'Fast-forward failed' }

$fx = 'F:\Dev\SCUMMBUCKET\FIXTURE'
$cap = Join-Path $fx 'CAPTURES\Room7\navigation-b9d905869e894798b5d7744caaf66a5a'
if (!(Test-Path -LiteralPath (Join-Path $cap 'engine-001.bin'))) {
    throw 'Original 1,149-frame capture unavailable; do not substitute doorway capture'
}
$out = Join-Path $fx ('OUTPUT\Room7\navigation-native-' + [guid]::NewGuid().ToString('N'))

python -B -m tools.analyze_room7_navigation $fx $cap $out --export-native
if ($LASTEXITCODE -ne 0) {
    throw "Native export failed; preserve partial evidence in $out"
}
if (!(Test-Path -LiteralPath (Join-Path $out 'animation.json'))) {
    throw "No completion manifest; preserve partial evidence in $out"
}
Write-Host "Verified native export: $out"
Write-Host "Open: $(Join-Path $out 'play.html')"
~~~

Outputs under FIXTURE/OUTPUT/Room7/navigation-native-NEW-GUID:
- 1,149 frame-0001.png through frame-1149.png native indexed PNGs
  (only if every frame passes its comparison);
- animation.json final completion manifest and per-frame indexed,
  palette and encoded PNG SHA-256 values;
- play.html two-segment playback, which uses relative PNG files;
- original navigation.json, route.png, and masking overlays from the
  same unchanged analyser for audit.

Opening **only play.html without its sibling PNGs will be blank**.
Keep the output folder intact. Its images include copyrighted game
resources and belong only in FIXTURE; do not put them in Git or public CI
artifacts. No video encoding or upscaling is done by this mode.

## Acceptance and limitations

Synthetic Windows CI covers segment boundaries, skipped ticks,
corrupted/missing hash metadata, nonzero compositor mismatches, timestamp
regressions, path traversal filenames and manifest provenance. These are
fixture-free code tests, **not a private 1,149-frame export run**. The Windows
operator must run the above command to establish an actual complete export,
and report its final output directory and any error.

The existing indexed reconstruction's acceptance applies to the original
1,149 captured exterior frames only. Runtime palette samples, pose/draw
states and timestamps remain observed inputs. The browser player does not
simulate script-controlled events, rerender actors, independently model the
Room 12 interior, handle audio or claim arbitrary route compatibility.

**Next P4 gate after the Windows export:** verify the complete set of
rendered indexed PNG and palette hashes against animation.json, inspect
both exterior segments in browser playback and compare an independently
selected set of native frames with the stored raw reference. Never silently
declare this achieved from fixture-free CI.
