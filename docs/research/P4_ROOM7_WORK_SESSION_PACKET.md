# Room 7 — low-usage Work session packet (P3/P4)

**Status:** preparation plus a source-grounded 0x59 decoder extension and fixture-free tests. **No private Room 7 actor reconstruction has been verified.** Research-branch GitHub Actions now runs synthetic tests on each push; always inspect the latest CI result.  
**Research branch baseline at preparation:** `965424eaededc23b73b5447f55061ba2b70de48c` (verify current remote HEAD before work).  
**Owner-approved scope:** extract the maximum independently verified Room 7 reconstruction evidence in a **limited ChatGPT Work-usage allocation**. Budget is *usage*, not literal elapsed minutes. Prioritize validated, pushed increments. **Do not launch a broad, unbounded agent task.**

## Immediate startup — spend usage on engineering, not rediscovery

1. Verify branch HEAD and `git status --porcelain` in each checkout. Canonical local paths: `F:\Dev\SCUMMBUCKET\SOURCE\ScummBucket` (repository), `F:\Dev\SCUMMBUCKET\TOOLS` (ScummVM instruments/builds), `F:\Dev\SCUMMBUCKET\FIXTURE` (immutable archives, private captures and exports). No fourth top-level directory.
2. Previous Work used a separate checkout at `C:\Users\87otl\Documents\ChatGPT\ScummBucket\SOURCE\ScummBucket`. It reported the F: checkout at an older commit. **Only fast-forward** F: when reachable and the working tree is clean; otherwise report divergence and do not overwrite, reset, relocate or silently copy between trees.
3. Run `python -B tools/room7_work_preflight.py --root F:/Dev/SCUMMBUCKET` when available. It is read-only. If original capture files are unavailable, use the report and archive-only research; never invent frame-level validation.
4. Read this packet, [renderer source map](P4_ROOM7_RENDERER_SOURCE_MAP.md), [Room 7 integration](P4_ROOM7_INTEGRATION.md), [Room 23 walking and costume baseline](P4_ROOM23_WALK.md), `scummbucket/classic_costume.py`, `tools/compare_room7.py`, `tools/verify_room23_costume.py`, `tools/instrument_room7.py`, `tools/run_room23_frames.py`, `tests/test_classic_costume.py`.
5. **PUSH EARLY:** Every *independently useful, tested* milestone should be committed and pushed immediately to `research/p4-engine-palette-trace`. Check remote HEAD before subsequent pushes; use ordinary fast-forward behavior and stop on conflict. Do not leave all commits until the end. Tests/diagnostics can be partial, but label them clearly; never call failing verification a success.

### Known pinned fixtures and evidence

| Item | Verified previous finding / locator |
| --- | --- |
| Original game | Monkey Island 2 original DOS VGA, `FIXTURE/GAMES/MonkeyIsland2_DOS_VGA` |
| `MONKEY2.000` SHA-256 | `cde7aa8980317e3a750fbb3b49884cdddaf1ff3d4231a0c840b22cceed9033f1` |
| `MONKEY2.001` SHA-256 | `ad045372e0d49626503bb50fca29a687ec8e01ef75d9b8bca702a366d143819e` |
| Room 7 source | 784 × 144, 98 strips; 320 × 144 viewport; camera X 0–464 in eight-pixel steps |
| World background SHA-256 (indexed bytes) | `843f5d1d81ed8bb8f7353a0c5b3c52d2229505becbd47a411b3cd4314b5bccfc` |
| Palette cycling | Six `CYCL` records: 16–18, 176–177, 178–179, 180–181, 182–183, 184–185 |
| Depth | One room Z-plane, `ZP01`, native world width 784, 18,366 set pixels |
| Stored object images | IDs 41, 42, 45, 57, one state each; object-state changes not observed |
| Animated scenery | Script 207 places actor 11 (costume 142) relative to camera; archive-decoded/script-derived mechanism; execution observed only in debugger-equivalent room jump |
| Costume 142 independently checked against original uploaded ZIP | `DCOS[142]` points to room 7; decoded `MONKEY2.001` offset 584460, chunk length 1,509, format `0x59`, 14 as highest animation identifier; COST SHA-256 `7ef3e98fb9cd824782b0cf7e93d9e7f3c059354557ec7e08d714eda9425a7c5f` |
| Existing Room 7 panorama | `FIXTURE/OUTPUT/Room7/native-20261110-a` (`manifest.json`, `background.png`, `ZP01.png`, objects) |
| Existing private capture | `FIXTURE/CAPTURES/Room7/sweep-20261110-a` (`run.json`, engine and presentation binaries) |
| Existing comparison | `FIXTURE/REPORTS/Room7/sweep-20261110-a/report.json` (87 frame records) |
| Script research | `FIXTURE/REPORTS/Room7/scripts-20261110-a` (ENCD/LSCR disassembly) |
| Room 23 regression | `FIXTURE/REPORTS/Room23/walk-20261110-a.json` and paired `CAPTURES/Room23/walk-20261110-a-{normal,control}` |
| Previous suite | 256 tests passing, 4 skipped, on previous working environment; **not a test run for this packet** |

The uploaded `sweep-20261110-a.zip` shared in ChatGPT contains the comparison report, 87 `viewport-*.png` images, scene inventory and script snippets; **it does not contain the 87 original `engine-*.bin` / `present-*.bin` pairs**. Never mistake its PNG previews for independent front-buffer evidence. The original full captures reportedly remain on F:.

## Targeted experiments, ordered by value

### Checkpoint A — verify 32-color scenery COST against the original archive (first new Work push)

- Inspect `ClassicCostume` and pinned upstream `scummvm/scummvm` tag `v2026.4.0`, `engines/scumm/costume.cpp`, especially `ClassicCostumeLoader::loadCostume`, `paintCelByleRLECommon`, `ClassicCostumeRenderer::byleRLEDecode`.
- Preparation commits already extend `ClassicCostume` for `0x58` and `0x59` and add synthetic tests for 32-color palettes, RLE, transparency and malformed runs. **Review and run these first**; they have not yet been compared with private actor-11 frames. Fix any failures, verify pointer bases and bounds, and preserve Room 23 behavior. No copyrighted pixels were added to Git.
- Resolve `DCOS[142]` via `inspect(game)['directory_links']['entries']`; verify linked tag, byte length, source digest. Do not copy or commit the costume resource.
- Enumerate actor-11 cels/sequences/palette/transparent slot. If decoder data do not match source invariants, record a hard diagnostic, do not guess.

**Push A** after independent costume-142 decode smoke test and targeted tests (if private fixtures exist), even if actor placement still needs work.

### Checkpoint B — independent actor 11 against isolated reference (second code push)

- Treat frame-state data as **engine-observed**, not self-simulated. The original 87-frame report records actor 11's world position, costume, logical frame, and scale, but **only records limb cursors for actor 1** (`walk 1 ...`); it does **not** contain actor-11 limb positions. Do not hallucinate those missing fields. A guarded, source-only follow-up patcher is prepared at `tools/instrument_room7_actor11.py`, with synthetic tests; if exact actor pose cannot be determined from decoded scripts, copy the existing Room 7 ScummVM build to a **fresh** TOOLS path, apply that patch, compile and run a focused comparable sweep. Actor-11 cursor snapshots will be emitted as `costume11 ...`. Derived screen X is `world_x - viewport_x`. Do not assume `y=144` means outside the screen: cels can extend above actor foot origin.
- Frame candidates: ~47–74, where Guybrush is substantially off left side; confirm *costume pixel extent*, not just foot coordinates, before declaring isolation. In frame 63, camera X=464 and actor 11 world X=590, so screen origin X=126.
- Reconstruct one actor-11 indexed frame *from decoded archive COST*, not from ScummVM's front pixels. Then compare `320*144=46,080` indexed positions per frame; report mismatches, first differing coordinates, control data, palette mappings and visible bounds. Progress to all isolated frames if valid.
- If scenery uses camera-relative positioning `590 - ((camera_x - 624)/2)`, verify script/data consistency separately; do not fit position to each reference image.
- Keep source-decoded vs observed vs inferred fields explicit. Never replace an unverified component with a stolen ScummVM rendered layer.

**Push B** after at least one independently verified frame or a reproducible, localized blocker report.

### Checkpoint C — scaled Guybrush and depth (third push)

- Read the upstream `smallCostumeScaleTable`, scale-step, scale-index wrap and drawing order, *including* palette remap/actor scale. This is not generic image resampling. Observed Guybrush scale is around 150/155 (on a 0–255 engine scale), unlike Room 23's native scale.
- Generalize `compose` to world coordinates and separately project viewport; preserve exact pixel indices, transparency, cel offsets, pose draw-phase and negative coordinates. Test scaled movement over distinct camera positions, clipped and unmasked.
- Validate `ZP01` pixelwise against the archive mask and engine, accounting for camera crop and the selected plane; don't infer ZP01 actor clipping from the archive-mask-only agreement.
- Report per-actor/per-frame differences; prefer visible mismatches over fuzzy RGB comparison.

**Push C** once a reusable scale/mask component has independent tests or documented evidence.

### Checkpoint D — integrated export and final handoff (last push)

- Produce a **non-overwriting** native scene preview driven by archive-derived 784×144 background, verified palette schedule and recorded camera offsets, with independently decoded actor cels wherever supported. Mark unsupported layers as missing, not visually verified.
- Test Room 23 P3/P4 fixtures and Room 7 archive/camera/palette fixtures; run full suite if possible. Preserve partial findings and known mismatch cases, do not suppress errors.
- Write a manifest with game/resource IDs, offsets, SHA-256, ScummVM build identity, script-entry path and a per-frame provenance split. Document accurate CLI commands and report what was *not* validated.
- **Push D** before the Work session ends; output exact commit hashes and clean/dirty status.

## Important pitfalls already discovered

- Room 7 was entered using a debugger-equivalent jump from a Room 23 save, **not normal gameplay entry**. Normal entry, conditional object 57 state and music triggers are separate pending experiments.
- Actor 11 uses **costume 142 with 32 local palette slots**. Preparatory source changes now accept format `0x59`, with synthetic test coverage. **Real costume-142 decoding and frame fidelity remain unverified**; validate before building on this code.
- The Room 7 report says 87/87 archive background crops, masks and final palettes matched. **It does not say the composed front buffer was independently reconstructed**. It records **no actor-11 limb cursors**, so a new narrow instrumentation capture may be necessary before exact scenery composition can be tested.
- `ZP01` world mask byte agreement is not proof that scaled actor clipping or layered costume rendering works.
- Room 23 observed the limb cursor **after** drawing on the walking sequence. Corrected displayed positions used the previous step in the archive-defined gait cycle; test if/when Room 7 exhibits the same order, don't blindly subtract one from every cursor.
- Camera X stops at 464 after frame 63; actor 11 continues independent script-controlled motion by camera position and potentially costume animation.
- ScummVM's RGB readback may pass through RGB565 conversion, so use indexed front buffers for primary fidelity. 320×200 presentation can include UI pixels not in the 320×144 room.
- The 87-frame sweep is **not natural room-entry evidence**.
- Full iMUSE/audio research is explicitly deferred.

## Usage-saving execution contract

- **Do not spend scarce Work usage repeating the panorama extraction, 87-frame scrolling sweep or basic inventory.**
- Use the existing evidence and repo tools first; instrument ScummVM only if one narrowly specified missing field blocks an actual comparison.
- After a blocker: document precise failed condition and continue to the next independent task; don't spend most of the allocation debugging one uncertain aspect.
- Commit/push at every tested increment; keep branch history understandable (decoder → scenery validation → scaling → integrated export). Never `git reset --hard`, `git push --force`, delete/overwrite source fixtures, move the archive into Git or add top-level folders.
- End with a concise **verified / partially verified / unverified** capability table, exact test command/results, report paths and commit URLs. If the environment cannot access F:, disclose that rather than fabricate machine-local outputs.
