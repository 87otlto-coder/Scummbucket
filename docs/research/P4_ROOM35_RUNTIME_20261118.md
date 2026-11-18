# Room 35 debugger-equivalent runtime validation

## Provenance

ScummVM 2026.4.0, SDL 2.32.10. Both controlled runs loaded the same private Room 23 save (SHA-256 `968bbdfaa855f35e0e89c271172d3d185448f256213f87d527cfa2b18ccea8ad`) and entered logical/resource Room 35 through the equivalent of the installed debugger's `room 35` handler. The automation runs after the source-room loop completes, sets the two bits, assigns Ego's room, stops sounds, calls the normal scene transition and requests a full redraw. It does not run the debugger UI. Both runs inherited Bit92=0 and Bit567=0 before injection.

| Input | SHA-256 |
|---|---|
| MONKEY2.000 | cde7aa8980317e3a750fbb3b49884cdddaf1ff3d4231a0c840b22cceed9033f1 |
| MONKEY2.001 | ad045372e0d49626503bb50fca29a687ec8e01ef75d9b8bca702a366d143819e |
| Parent cross-room executable | 9f958b151bd4cfde56bf744e867fb37b9907a7ebef8263a2e1047ec9a171d9db |
| Parent scumm.cpp | f601515a37a249b91eec9419ec0617f53a9a82d749aa464c829c4ccca6d1dd6 |
| Patched scumm.cpp | 30262f42387b3e5c0027b4f18d53f2e6d8aa9ffb5135f4a0a974cfd9e08b3ec4 |
| Room 35 executable | e79dc4c70e1f29b95a77097b0d4010027fed93ed88b8b66162e82b2657a62786 |

The installed source snapshot includes the parent build manifest and source hashes. Its exact upstream Git commit could not be authenticated from that installation. The two controlled runs each produced 33 engine frames. The comparison uses the first 32 complete engine/display pairs for each branch. Full binary captures, saves and per-frame metadata stay under private FIXTURE.

## Observed behavior and independent comparisons

| Measure | Effective Bit92 clear | Effective Bit92 set |
|---|---:|---:|
| Post-entry Bit92 / Bit567 | 0 / 0 | 1 / 0 |
| Frames showing active script 202 | 32 / 32 | 0 / 32 |
| Object 364 sampled states | 2–8, then 1, repeated four times | 0 throughout |
| Waterfall-only back-buffer indexed mismatches | 0 | 161,664 |
| Waterfall-only front-buffer indexed mismatches | 3,776 | 161,664 |
| Added archive-derived room objects and replayed first actor draw, before idle retention | 0 front mismatches | 3,658 front mismatches |
| Extended replay after idle retention, back buffer | 0 / 1,474,560 | 0 / 1,474,560 |
| Extended replay after idle retention, front buffer | 0 / 1,474,560 | 0 / 1,474,560 |
| RGB entry mismatches, literal archive CLUT start to presented CLUT | 128 / 8,192 | 128 / 8,192 |
| RGB entry mismatches, observed initial palette to presented CLUT | 0 / 8,192 | 0 / 8,192 |
| Cycle counter mismatches | 0 / 64 | 0 / 64 |

The clear branch verifies all eight authored waterfall images as composited, including placement (128,96) and opacity, against complete native back buffers. First sampled frame is state 2 with script 202 in slot 2, where 3, status 2, offset 46686. State 1 was observed on frames 8, 16, 24 and 32. Set-branch objects 361, 362 and 365 were state 1. Decoding and compositing those archive layers in engine slot order removed the set-branch back-buffer differences. The first original set-branch difference was at (158,11), expected index 35, baseline index 51.

The extended front-buffer replay uses observed Ego placement, scale, facing, costume limbs and packed Z-plane bytes with existing ScummBucket costume and masking functions. It uses no observed front-buffer pixels in predictions. A missing draw after the actor and background stabilized leaves the prior reconstructed pixels in place. Without that retention, set-branch frame 2 first differs at (162,91), expected index 198, calculated index 144. The first clear-branch baseline front difference is also at (162,91), expected 198, calculated 188. The comparison uses runtime Z planes for masking. Independent authored-to-runtime mask reconstruction and a complete draw-queue trace remain open.

Both cycles were active with raw flag 0x0004, delays 5 and 6, ranges 176–191 and 160–175. No flag-specific correction was required for the observed counter and RGB replay. The literal archive palette already differs from the very first pre-cycle engine palette at indices 1, 2, 3 and 6. At index 1 the archive has (0,0,171) and the engine (23,0,23). The origin of those four pre-cycle differences is open. The exact RGB result uses the observed first pre-cycle palette and then advances it independently using observed timer deltas. It does not establish a complete archive-only initialization model.

A third run injected Bit92=0 and Bit567=1. The transition call did not return before timeout and no Room 35 frame was captured. The pre-entry injection is confirmed by the log. Its effective outcome remains static script-aligned only. Natural gameplay entry and arbitrary inherited saves remain unverified.

Private comparison report SHA-256 values:
- Clear: 3a4c10cbe3d80ffa1ed72bbee6186dfb10c009e94e855596e95e2490ae9153e3
- Set: c378872cac9daf3c56785c58a7a0ccd3b7c57c2b83c05d98392e2e046c561290

## Repeat on Windows

Use the pinned cross-room build tree under TOOLS as a read-only input and choose a fresh TOOLS build directory. Run these from the ScummBucket checkout.

```powershell
$root = 'F:\Dev\SCUMMBUCKET'
Set-Location "$root\SOURCE\ScummBucket"
$parent = "$root\TOOLS\ScummVM-P4-CrossRoom-767b677319ce4691953ca06dcf67811c"
$build = (New-Item -ItemType Directory "$root\TOOLS\Room35-$([guid]::NewGuid())").FullName
$env:PATH = 'C:\msys64\ucrt64\bin;' + $env:PATH
python -B -m tools.instrument_room35 "$parent\engines\scumm\scumm.cpp" "$build\scumm.cpp"
if ($LASTEXITCODE) { throw 'Overlay failed' }
g++.exe -w -std=gnu++11 -fno-operator-names -DHAVE_CONFIG_H -DWIN32 -DSDL_BACKEND -DUSE_SDL2 -DUNICODE -D_UNICODE -DENABLE_SCUMM=STATIC_PLUGIN "-I$parent" "-I$parent/engines" -IC:/msys64/ucrt64/include/SDL2 -c "$build/scumm.cpp" -o "$build/scumm.o"
if ($LASTEXITCODE) { throw 'Compile failed' }
$libs = @(Get-ChildItem $parent -Recurse -Filter '*.a' | ForEach-Object FullName)
$platform = @(Get-ChildItem "$parent/backends/platform/sdl" -Recurse -Filter '*.o' | ForEach-Object FullName)
g++.exe -static-libgcc -static-libstdc++ -o "$build/scummvm.exe" "$build/scumm.o" "$parent/engines/scumm/detection.o" "$parent/dists/scummvm.o" @platform '-Wl,--start-group' @libs '-Wl,--end-group' -lmingw32 -lwinmm -lgdi32 -lSDL2main -lSDL2 -lm -lz -lole32 -luuid -lwinspool -lsapi
if ($LASTEXITCODE) { throw 'Link failed' }
$game = "$root\FIXTURE\GAMES\MonkeyIsland2_DOS_VGA"
$save = "$root\FIXTURE\CAPTURES\Room23\walk-20261110-a-normal\saves\monkey2.s01"
$export = "$root\FIXTURE\OUTPUT\Room35-source-$([guid]::NewGuid())"
python -B -m scummbucket.room35_waterfall $game $export --effective-bit92-clear --synthetic-delta 1
if ($LASTEXITCODE) { throw 'Source export failed' }
foreach ($scenario in 'clear','set') {
    $capture = "$root\FIXTURE\CAPTURES\Room35-$scenario-$([guid]::NewGuid())"
    python -B -m tools.run_room35_capture "$build\scummvm.exe" $game $save $capture $scenario
    if ($LASTEXITCODE) { throw 'Capture failed' }
    python -B -m tools.compare_room35_capture $game $export $capture "$capture\comparison.json"
    if ($LASTEXITCODE) { throw 'Comparison failed' }
}
```

The production waterfall exporter remains archive-derived. The separate comparator owns the runtime inputs and reports the waterfall-only baseline alongside the layered replay. No shared decoder changes were needed. The private Windows Room 7 replay was rerun from an isolated working snapshot because Git access to the canonical checkout remained blocked. It matched all 87 indexed frames and final palettes, with 778 mismatches in the ZP01 negative control. The private-enabled pre-addition suite was 400 passed and 7 skipped, plus three targeted retention tests passed after the addition. See PR #19 for the branch's Windows Actions result.
