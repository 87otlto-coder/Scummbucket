# Optional BigR M1 export — implementation and acceptance

## Baseline and scope

ScummBucket base: research/p4-room24-event-replay at a267a34744f0e28b035482e8ceaa879a57b033cd (PR #22). It contains the Room 7 navigation exporter and later independent Z-plane/event replay work. main is documentation-only at 4d4aa25c3e259299743d1bd8b7d85f9889d302f3. Do not merge the stacked drafts. The observed-event-replay branch and MI2SE music PR #24 remain separate.

BigR target: draft PR #5, feat/m1-shared-export-contract at 4748826f922a335999651b14951ed2584f6f4ded. Its documented CLI and package implementation were inspected. BigR reported 21 Windows tests passed on that revision. This is not evidence of ScummBucket integration acceptance.

Existing reusable capabilities: archive reader/inventory/extraction; indexed SMAP background and CLUT, OBIM states, native PNG, COST/cel rendering, viewport/camera and independent Z-plane composition; observed palette cycling and bounded object/event reconstruction. The Room 7 native navigation audit compared 1,149 indexed 320x144 exports and 768-byte palettes to the recorded engine, 52,945,920 index positions with zero differences. Independent Z-plane comparison across Room 7/24/35 covered 215 frames and 2,476,800 packed mask bytes with zero differences. The later Room 24 RNG replay independently predicted 64 frames from explicit entry seed and observed events. These are historical, bounded acceptance records, not new tests or arbitrary script execution.

## Adapter

Run python -m scummbucket.bigr_export with an already-decoded, explicit RGBA8 PNG or an existing Room 7 indexed native viewport plus its animation.json. Pillow is imported only on demand (existing [gif] optional extra). No changes to existing CLI, archive, palette, mask, native export or rendering code; no unconditional Node/BigR dependency.

Room 7 path checks the existing schema, edition, geometry, exact-comparison marker, palette source, unique frame row and exact PNG/index/768-byte palette hashes; the composed viewport is opaque, index zero remains a color. This is manifest-attested evidence, not a new capture comparison. Original source stays untouched. Generic RGBA is caller-supplied, not claimed game-verified. Other indexed PNGs, RGB-only inputs, animation, and unspecified masks are refused rather than guessed.

Adapter writes the existing BigR binary package schema, asks the configured Node+CLI for capabilities and validation, invokes render into a private staging directory, checks the output manifest against stdout, expected source digest, render settings, dimensions and PNG SHA-256, and independently compares all RGBA values against Pillow nearest-neighbor. The retained package contains the actual handed-off raster. No BigR scaling code is copied. Output directory must be new; input and existing exports remain unchanged.

Success: image.png, result.json (BigR), adapter.json (ScummBucket), package/ (reproducible input). Explicit --fallback-native preserves the original PNG byte-for-byte in a new destination with adapter.json, status fallback-native, actualScale=1 and exit 2; no BigR result is invented. Without fallback, backend failure exits 1. Source-evidence failures and destination conflicts never trigger fallback.

## Windows reproduction, synthetic and real

Use a built checkout of the exact BigR target (Node 22+, npm ci, npm run build). Do not switch a dirty existing checkout; use a separate worktree or existing correct build. No workspace-root folders or original archives are changed.

    Set-Location 'F:\Dev\SCUMMBUCKET\SOURCE\ScummBucket'
    git status --short
    git fetch origin feature/bigr-optional-export
    # If the worktree is clean and you intend to switch:
    git switch --track origin/feature/bigr-optional-export
    python -m pip install -e '.[gif]'
    $bigr = 'F:\Dev\BigR\SOURCE\BigR\bin\bigr-export.mjs' # adjust to actual built CLI
    $env:BIGR_TEST_CLI = $bigr
    python -m unittest discover -s tests -p test_bigr_export.py -v

For real acceptance use the private native navigation export audited in docs/research/P4_ROOM7_NATIVE_EXPORT_ACCEPTANCE_20261114.md (original export ZIP SHA-256 8ba6957f77f2ff274218e8066fe4c1a8f27c991922e38d31ac6b7efc9e0757f6; animation.json SHA-256 2c9606a85358da9cf254d7de9c35dbedf8f4a509449099a8188a0ba058ee1974). Confirm the archive identity and choose a previously audited frame. No game assets or captures in CI.

    $manifest = 'ABSOLUTE_PATH_TO_AUDITED_EXPORT\animation.json'
    $frame = 'ABSOLUTE_PATH_TO_AUDITED_EXPORT\frame-0001.png'
    $out = 'F:\Dev\SCUMMBUCKET\FIXTURE\OUTPUT'
    # Parent must already exist; each child is a new directory.
    $id = [guid]::NewGuid().ToString()
    foreach ($scale in @(1,4)) {
        python -m scummbucket.bigr_export $frame "$out\Room7-BigR-$id-$scale" --asset-id room7-frame-0001 --room7-manifest $manifest --bigr-cli $bigr --scale $scale
        if ($LASTEXITCODE -ne 0) { throw "BigR acceptance failed at scale $scale" }
    }

Expected 320x144 and 1280x576, 46,080 and 737,280 RGBA pixels, zero differences to independent reference. Actual hashes and result files must be produced locally. Verify against the audited original manifest and preserve the outputs privately. The source ZIP was not recovered in the chat session; do not mark real asset acceptance passed until it is executed. The original DOS archives alone are not the verified runtime frame.

Existing Windows regression job builds the exact BigR revision and sets BIGR_TEST_CLI for the original-free unit suite. Without that environment variable the real-sidecar test skips; fake process tests are not BigR verification. No CI artifact uploads.

## Future animation

Reuse room7_navigation_export.make_segments/make_manifest and native_animation_common: ordered indexed frame PNGs, source hashes, engine ticks, observed SDL present_ms, camera-associated source reconstruction, separate segments and an explicit gap. Actors, COST draw records, placement, scaling, foreground masks, palette state and world/viewport geometry stay in ScummBucket. Panorama exporter provides world geometry and individual object states/masks, not a verified animated composite. Static opaque composited viewport is already resolved; do not hand Z-planes to BigR as alpha.

BigR P1 animation package already has ordered frames, durationMs, canvas/sourceCanvas and placement/sourcePlacement; M1 CLI does not render them. Next smallest useful step is a single continuously observed segment with each palette-resolved RGBA viewport, repeated frames retained and timing derived from adjacent present_ms. Keep zero-duration timestamps and unknown final-frame hold explicit: do not manufacture a positive duration to satisfy the package. Agree timing policy or future schema before representing such sequences. Preserve original ticks, segment breaks, frame/asset hashes and capture confidence as metadata/provenance. No 30/60 FPS normalization. For source layers, define anchor/placement units, alpha/mask semantics and order before enabling composition. Runtime camera/actor timing cannot be independently inferred from this export.

## Future audio

ScummBucket owns cue selection, SCUMM/iMUSE, sound-driver/instrument interpretation, trigger/loop semantics, native timing and evidence confidence. BigR consumes decoded PCM or file reference only. Proposed game-independent properties (not a new schema or implemented support): asset ID; decoded source + hash; sample rate, channel layout, sample format, exact sample count; start on rational timeline or sample offset tied to a declared clock; source trim [start,end) in samples; loop range/count, explicit gain and fade lengths/curve; track role music/effect/ambience; synchronization origin and provenance/confidence. BigR eventually handles placement, mix, resampling policy, explicit fades/loops, encoding and muxing. No iMUSE in BigR. Unknown loop boundaries or triggers remain unknown, not defaulted.

Separate MI2SE PR #24 has named XWB cue export prototypes, six prior identified WAVs (101/103/162 in Original/New banks), non-overwrite checks and two creative crossfades. These are Special Edition recorded tracks, not verified original DOS iMUSE sequencing. The existing WAVs/JSON can supply measured sample rate, channels, format, sample count and hash when available; the creative timeline is not original gameplay synchronization. No WAV bytes inspected during this integration and no new MIDI/synthesis work. Keep that branch separate.
