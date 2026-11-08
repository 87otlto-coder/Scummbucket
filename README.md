# ScummBucket

**Status:** Planning and research | **Roadmap:** v0.3

ScummBucket is an evidence-driven toolkit for investigating, extracting, reconstructing, previewing and exporting assets from classic LucasArts SCUMM games.

The initial targets are **Monkey Island 2: LeChuck's Revenge (original DOS VGA)**, followed by **The Secret of Monkey Island (original DOS editions)**. The Curse of Monkey Island is a future candidate.

ScummBucket is intended as an asset-extraction and reconstruction toolkit, **not** a replacement for ScummVM or a general-purpose game interpreter.

## Project foundations

- [Standing Project Instructions](docs/PROJECT_INSTRUCTIONS.md) — non-negotiable research, development, verification, error-reporting and GitHub rules.
- [Project Charter & Roadmap (v0.3)](docs/PROJECT_CHARTER_ROADMAP.md) — objectives, initial game coverage, phases P0–P8 and acceptance criteria.

## Core priorities

- Faithful decoding with reproducible source provenance.
- **Background animation as a first-class objective**, including objects, layers, palette effects, costumes and scripted motion.
- Character animation, backgrounds, objects and audio extraction.
- Asset-level scaling: nearest-neighbor by default, established optional pixel-art filters later.
- Explicit diagnostics: **always report errors; never hide them**.
- Honest coverage reporting: distinguish originals, decoded assets, reconstructions, enhancements, partial successes and unsupported mechanisms.

## Technical references

- [ScummVM](https://github.com/scummvm/scummvm) — primary engine and format research reference.
- [ScummVM Tools](https://github.com/scummvm/scummvm-tools) — complementary tool reference.

Reference implementations require independent validation against relevant game editions. Third-party licensing must be respected.

## Experimental archive inspector (P1 prototype)

A limited, read-only command-line prototype is available on the P1 feature branch. It currently supports the original DOS Monkey Island 2 `MONKEY2.000` / `MONKEY2.001` pair only. This includes P1 inventory, diagnostics and selective raw-chunk export tools, plus an **experimental P2 image-state decoder** for supported DOS v5 OBIM strips and masks. Full room, animation and audio decoding remain unimplemented.

On Windows, the standard local project directory is `C:\Users\87otl\ScummBucket`. From PowerShell, run:

```powershell
cd "C:\Users\87otl\ScummBucket"
python -m scummbucket inspect "C:\path\to\mi2.zip" --json
python -m scummbucket extract "C:\path\to\mi2.zip" --room 4 --tag CYCL --output-dir "C:\Users\87otl\ScummBucket\exports\room-004-cycl"
python -m scummbucket extract-id "C:\path\to\mi2.zip" --directory DSCR --id 12 --output-dir "C:\Users\87otl\ScummBucket\exports\script-012"
python -m scummbucket scenes "C:\path\to\mi2.zip" --room 34
python -m scummbucket images "C:\path\to\mi2.zip" --room 34 --object 358 --output-dir "C:\Users\87otl\ScummBucket\exports\object358-new-output"
python -m scummbucket palette-probe "C:\path\to\mi2.zip" --room 23 --ticks 0 35 71 107 --output-dir "C:\Users\87otl\ScummBucket\exports\room23-palette-new-output"
python -m scummbucket palette-map "C:\path\to\mi2.zip" --room 23 --output-dir "C:\Users\87otl\ScummBucket\exports\room23-palette-map-new-output"
python -m scummbucket palette-sequence "C:\path\to\mi2.zip" --room 23 --fps 30 --duration-seconds 4 --counter-rate 60 --output-dir "C:\Users\87otl\ScummBucket\exports\room23-sequence-new-output"
python -m pip install -e ".[gif]"  # Once, for optional GIF encoding
python -m scummbucket palette-gif "C:\path\to\mi2.zip" --room 23 --fps 30 --duration-seconds 4 --counter-rate 60 --output "C:\Users\87otl\ScummBucket\exports\room23-preview-new.gif"
python -m scummbucket palette-events "C:\path\to\mi2.zip" --room 23 --duration-seconds 4 --counter-rate 60 --output-dir "C:\Users\87otl\ScummBucket\exports\room23-events-new-output"
python -m scummbucket render-events "C:\Users\87otl\ScummBucket\exports\room23-events-new-output" --fps 60 --output-dir "C:\Users\87otl\ScummBucket\exports\room23-render60-new-output"
python -m scummbucket palette-probe "C:\path\to\mi2.zip" --room 23 --ticks 0 1 4 9 --counter-increment 4 --output-dir "C:\Users\87otl\ScummBucket\exports\room23-delta4-new-output"
python -m scummbucket verify-descumm "C:\path\to\mi2.zip" --room 34 --script 201 --object 358 --descumm "C:\path\to\descumm.exe"
python -m unittest discover -s tests -v
```

Replace `C:\path\to\mi2.zip` with the location of your own game archive. Export files go under `exports\` rather than the project root. The source archive should remain outside the repository; the project path is a documentation convention, **not hard-coded into the tool**.

The `extract-id` command exports one validated resource by directory type and ID, with byte-exact source provenance. Global script 12 in the supplied MI2 sample, for example, is a 94-byte `SCRP` chunk. This does **not** interpret the script instructions.

The `scenes` command pairs `OBIM` and `OBCD` by their actual object IDs, reports multi-state image candidates, lists room palette cycles and nearby script/costume storage context, and records **raw opcode-pattern candidates** from room-local scripts with exact offsets. The raw scanner itself cannot confirm instruction alignment; that requires separate disassembly verification. In the private sample, **all 1,145 object-image chunks match object-code chunks by ID**, and **158 paired objects contain multiple visual states**. This is not evidence that the states animate during gameplay.

The inspector now resolves index directory IDs to individual room, script, sound, costume and font chunks. The supplied MI2 sample resolves **646 populated references**, with **142 unused slots** and zero reference mismatches. This does not mean scripts or assets have been decoded.

The optional `verify-descumm` command can check candidate instruction boundaries against the separately installed ScummVM Tools disassembler. The tool is available from [official ScummVM downloads](https://www.scummvm.org/en/downloads/). **The user completed the external verification on Windows:** all 17 candidate instruction starts in local scripts 201 (11) and 202 (6) matched, with zero conflicts or missing starts. This is evidence of instruction alignment, **not** runtime execution or animation timing. The CI tests still use mocked disassembler output; the new optional private integration test can reproduce the real check on a local machine.

For object **358**, the fingerprinted MI2 sample contains **17 independently confirmed opcode starts** across room 34 scripts 201 and 202 (**11 drawObject / 6 setState**). The user-supplied disassembly also establishes **interaction-driven state selection**: `min(15, 3*n-1+r)` for number `n=1..5` and random `r=0..2`. That does **not** establish gameplay execution, rendered appearance or fixed animation timing. See the [original evidence register](docs/research/P1_OBJECT_358_SCRIPT_SURVEY.md), [behavior analysis](docs/research/P1_ROOM34_OBJECT_BEHAVIOR.md) and [machine-readable event metadata](docs/research/P1_ROOM34_OBJECT_EVENTS.json).

### Experimental P2 image export

The `images` command can now decode native-resolution **RGBA PNG object states**, plus separately preserved **Z-plane mask PNGs**, from the subset of original DOS MI2 strip codecs implemented so far. It uses the room's original `CLUT` palette and `TRNS` transparency index without external graphics dependencies. Initial decoding of object 358 yields **16 states (56 × 40 pixels)** and **three mask planes per state**. This is a **research-stage pixel decoder**: output has not yet been compared pixel-for-pixel against a ScummVM reference rendering, masks are not composited into the room, and no animation timing is inferred. See the [P2 image-state research note](docs/research/P2_MI2_OBIM_STATE_DECODING.md).

For our separate **autonomous background-animation investigation**, the [palette-cycle candidate survey](docs/research/P4_PALETTE_CYCLE_CANDIDATES.md) now includes direct source evidence: **all eight palette-cycle ranges in room 23 and all five in room 109 occur in their decoded native background pixel buffers** (480 and 65 pixel positions, respectively). The experimental `palette-probe` command reuses the limited background strip decoder, rotates copied palette entries using **explicitly hypothetical counter increments** (default one per simulated update), and exports labeled PNG snapshots plus a provenance manifest. Source inspection confirms that ScummVM advances palette-cycle counters by `max(VAR_TIMER,VAR_TIMER_NEXT)` per actual cycle update. The new `--counter-increment` option permits controlled timing scenarios. **It does not establish that any hypothetical increments match real gameplay.** The four `CYCLE_FLAGS_UNVERIFIED` warnings remain visible.

**Observed room-23 VGA gameplay evidence (2026-11-08):** A user-supplied 30-fps recording was aligned to the original 320×144 background. Of **480 source CYCL pixel positions**, **457 (95.2%)** exhibited strong color changes across 19 sampled frames, versus **1.43%** of comparison-region non-cycle pixels. All eight color pairs alternated with observed median swap intervals closely matching a **hypothetical ~60 counter-units/second** interpretation of their SCUMM rates. This is **strong visual/spatial and cadence corroboration** of water shimmer, **not** an authenticated runtime palette trace or frame-perfect animation reconstruction. New `palette-map` exports native-coordinate source pixel overlays, individual masks and provenance. See [room-23 VGA video spatial and cadence validation](docs/research/P4_ROOM23_VGA_SPATIAL_VALIDATION.md).

### Experimental P4 palette animation frame sequence

The new `palette-sequence` command exports a room's **native 8-bit indexed PNG frame sequence** while retaining the **same source pixel indices** in every frame. Frame-specific `PLTE` chunks represent modeled palette rotations; separate outputs preserve the initial source-indexed background, original `CLUT` RGB bytes and a detailed SHA-256 manifest.

For the fingerprinted room 23, a **four-second, 30 fps, 60-counter-unit/sec** configuration requests 120 PNG frames. The 60-unit model comes from the supplied VGA gameplay video and is **video-calibrated, not independently engine-timer verified**. The exporter models one palette update per output frame, doesn't assert seamless looping and does **not** composite actors, objects, depth masks or script-driven lighting. No animated WebP/APNG container is generated in this first pass. No extra graphics dependency is required.

Read [the P4 PNG sequence-export scope and acceptance criteria](docs/research/P4_PALETTE_SEQUENCE_EXPORT.md). Public CI tests the encoder, synthetic timing, manifest and failure paths; the optional original-archive regression has not yet been executed locally in this review.

### GIF preview and palette-event timeline

The optional **`palette-gif`** command exports a playable-once native-resolution GIF and an adjacent JSON manifest (install once with `python -m pip install -e ".[gif]"`). It reuses the indexed-background model from the PNG exporter. Consecutive sampled frames rendering identically are merged into one GIF segment with the correct accumulated duration; **nonadjacent recurrences remain separate**. The JSON manifest preserves every modeled palette rotation, including visually ineffective rotations, together with exact sample timing fractions, resource hashes, original indexed-pixel and CLUT fingerprints, warnings and limits.

The GIF writer is Pillow's maintained LZW encoder; after encoding, ScummBucket reopens the GIF and compares **every RGB frame and GIF duration** to the indexed-color source model. An encoder mismatch or missing library is an explicit failure. GIF playback timing has **10 ms resolution** and may be clamped by some viewers. **The GIF is a nonlooping convenience preview, not an authoritative indexed resource or a verified engine-timer capture.** The prior 120 PNG frames included 16 unique full-palette states; that does not imply the GIF will have exactly 16 frame segments, because states can recur later.

See [P4 GIF preview implementation and verification status](docs/research/P4_PALETTE_GIF_PREVIEW.md). The original archive is not modified and no game-derived image files are committed to the repository.

### Experimental FPS-independent source palette timeline

The new **`palette-events`** command exports a portable bundle containing one original indexed PNG, the exact original 768-byte `CLUT`, and `timeline.json` with source hashes, indexed-pixel fingerprint, original `CYCL` metadata, ordered model-event ticks and RGB palette changes. It independently verifies replay at **15, 30 and 60 fps** without rerunning the cycle algorithm. Palette rotations that are invisible on this background remain in the event log rather than being discarded.

**Its model is intentionally different from the earlier GIF/PNG exports.** It assumes a palette update once per *counter unit* instead of once per output frame. The approximately 60 counter units/sec rate is video-inferred for fingerprinted room 23, but the **engine scheduler has not been measured**. This is a transparent experiment, not a silent replacement or a verified ScummVM runtime trace. The existing `palette-sequence` and `palette-gif` outputs are unchanged.

See [P4 experimental counter-unit palette timeline](docs/research/P4_PALETTE_EVENT_TIMELINE.md). It needs no optional Pillow dependency.

### Render original indexed PNG frames from a saved event bundle

Use **`render-events`** to select a playback FPS **after** exporting a `palette-events` bundle. This command verifies the saved event timeline, exact indexed PNG source, original CLUT, file SHA-256 values, and every palette RGB patch. It **does not need the original game archive**, reinterpret `CYCL`, or rerun the palette model. Result frames are lossless native indexed PNGs plus a `render-manifest.json`, created without overwriting existing files.

The renderer explicitly warns when a selected FPS skips intermediate states that still exist in the source event log. For the verified uploaded four-second room-23 bundle, **15 fps samples 60 frames but misses 5 event states; 30 fps samples 120 frames but misses 2; and 60 fps samples 240 frames and misses none** under the *synthetic* update schedule. At 60 fps, the current 240-frame limit is reached.

The uploaded source bundle was independently checked: the 320×144 indexed background and 768-byte CLUT match their manifest fingerprints, and all **19 recorded event timestamps / 32 modeled rotations** replay with exact before/after palette SHA-256. This establishes **bundle consistency**, not actual ScummVM engine timing. Old GIF and PNG commands use a different hypothetical update-call cadence and have not been silently altered.

See [saved event-bundle renderer and actual room-23 verification](docs/research/P4_EVENT_BUNDLE_RENDER.md). No Pillow dependency is required.

The [Room 23 5/10/60-Hz scheduler sweep](docs/research/P4_ROOM23_SCHEDULER_SWEEP.md) adds independently verified 5-Hz synthetic timing against both prior GIFs and a source-derived 1-Hz stress-test prediction: 28 instead of 32 rotations after four full 60-unit callbacks. A subsequent user-run 1-Hz stress experiment confirmed the live 60/60 timer override with fast mode off and visibly abrupt background changes; exact RGB palettes remain unrecorded. The [Room 23 six-unit cadence comparison](docs/research/P4_ROOM23_SIX_UNIT_COMPARISON.md) independently confirms that the user-generated 10-fps, six-counter-unit GIF shares identical RGB pixels with the prior event GIF at all 40 corresponding 100-ms points: 14 vs 20 GIF segments, 13 vs 17 unique states, no changes outside the 480 water-cycle pixels. Those GIFs remain synthetic previews; the later [first real Room 23 palette trace](docs/research/P4_ROOM23_FIRST_LIVE_PALETTE_TRACE.md) independently records **180 actual SCUMM callback palettes**, though the recording has no closing `END` marker. The [P4 Windows engine-capture runbook](docs/research/P4_WINDOWS_TRACE_RUNBOOK.md) now supplies checked PowerShell source setup, an MSYS2 UCRT64 SCUMM-only build helper, and a fail-closed runner for real Room 23 captures at the 6- and 60-unit regimes. The initial Windows MSYS2 compile correctly exposed that V1 used C stdio functions forbidden in engine code. The corrected **V2 hook uses ScummVM-native `Common::DumpFile`** and includes a guarded in-place upgrade; the user subsequently confirmed a successful V2 Windows build and supplied 180 live palette samples. Formal complete-trace import and independent binary attestation remain outstanding. A guarded source-hook generator for pinned ScummVM `v2026.4.0` and a strict `import-scummvm-palette-log` converter form the optional [P4 real-engine capture bridge](docs/research/P4_SCUMMVM_ENGINE_TRACE_CAPTURE.md). Synthetic bridge tests passed, V1 compilation failures were diagnosed, and the user confirmed the full corrected V2 build. **The supplied 180-sample live capture is incomplete (no END)** and remains outside the strict importer acceptance path. For exact verification against a developer-captured ScummVM palette trace, `verify-palette-trace` compares per-update timer variables and 768-byte RGB palette samples with the source-based model. It reports the first mismatch and differing palette indices; the input must identify its archive fingerprint, engine build and exact capture point. The first live Room 23 capture matches the original source CYCL model in **180/180** recorded palettes across two explicitly phase-aligned segments, including 172 held-out exact sample predictions. However, the current strict verifier also expects the captured initial palette to equal the source CLUT, which is not true for this run (four stable non-cycle runtime overrides and an active cycle phase); an explicit phase-aware comparison mode is still required rather than silently relaxing its existing contract. See [P4 runtime trace contract and visual-check instructions](docs/research/P4_RUNTIME_PALETTE_VERIFICATION.md). The four `CYCLE_FLAGS_UNVERIFIED` warnings remain visible.

See [P1 prototype documentation](docs/P1_PROTOTYPE.md) for supported behavior, failure reporting and remaining limitations. The sample game files must remain outside the repository.

## Current status

P0 format research is documented in [PR #2](https://github.com/87otlto-coder/Scummbucket/pull/2) and remains open. This branch introduces the first **P1 inspection and raw extraction prototype** in [PR #3](https://github.com/87otlto-coder/Scummbucket/pull/3). It has been tested against one user-supplied MI2 archive and synthetic fixtures, but **P1 is not complete**: script dependency interpretation, resilient per-resource recovery, advanced provenance verification and cross-edition support are still outstanding.

Commercial game files and extracted copyrighted game assets must not be committed to this repository. Use authorized local copies for integration testing; favor synthetic fixtures in version control.

Repository: https://github.com/87otlto-coder/Scummbucket
