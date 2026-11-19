# Room 24 randomized water and VGA entry palette verification

## Source and runtime

This branch is stacked on PR #19 at `282ff62372e5f6d44119dcec3eea7a64afd9907e`. The Windows sandbox denied Git access to the canonical F-drive checkout. Tests and builds used the isolated source snapshot under SOURCE, with the canonical read-only game and reference fixtures. The mirrored local P4 checkout contained untracked Room 7 work and was left in place.

[Static Room 24 research](https://github.com/87otlto-coder/Scummbucket/blob/research/mi2-spelunk-20261116/docs/research/MI2_MIXED_WATER_EVENT_LOOPS_20261116.md) aligns ENCD and LSCR 200. Entry starts script 200. It selects a candidate in 1–3, retries equality with the last accepted state, draws object 246 and yields. The three OBIM states and eight CYCL records were decoded from the pinned DOS VGA archive. Counters use delays 19, 19, 30, 30, 13, 71, 9 and 10. Only cycle 1 carries reverse flag 2.

The debugger-equivalent ScummVM 2026.4.0 harness loaded the checksum-verified Room 23 save and used the installed `room 24` transition sequence. Logical and resource rooms both verified as 24. The automation injected no game variables. Bit92 and Bit567 were both zero in the sampled path. Object 246 placement matched archive CDHD at (0,120). Script 200 was present in slot 2, location 3, status 2, offset 44116 in the sampled frames.

| Evidence | Corrected probe run |
|---|---|
| Consecutive validated engine/display pairs | 64 |
| Sampled object states | 2312323123131323213132323212121232123212312123132123231212312323 |
| RNG calls aligned to those frames | 95, with 64 accepted and 31 rejected |
| Back / front indexed mismatches | 0 / 0, over 2,949,120 positions per buffer |
| Cycle counter mismatches | 0 / 512 |
| RGB-entry mismatches, literal archive CLUT | 256 / 16,384 |
| RGB-entry mismatches, archive CLUT plus source-mapped hook operands | 0 / 16,384 |
| RGB-entry mismatches, observed pre-cycle seed | 0 / 16,384 |

An initial 64-frame run without the RNG opcode probe and a second, scoped probe run produced different state sequences and exact indexed parity. Raw calls in the table are after the transition completion marker. The separate entry-time call is excluded from the 64 sampled decisions. Each sampled state was checked against the logged raw 0–2 RNG result plus one and its previous accepted state. Consecutive sampled transitions were non-repeating. The report retains raw RNG operands, frame IDs, script/actor state, cycle counters and per-frame hashes. It uses archive background/object/costume pixels plus observed state, actor geometry, packed runtime masks and timer inputs. Engine front-buffer pixels serve only as comparison targets.

- MONKEY2.000 SHA-256: `cde7aa8980317e3a750fbb3b49884cdddaf1ff3d4231a0c840b22cceed9033f1`
- MONKEY2.001 SHA-256: `ad045372e0d49626503bb50fca29a687ec8e01ef75d9b8bca702a366d143819e`
- Room 23 save SHA-256: `968bbdfaa855f35e0e89c271172d3d185448f256213f87d527cfa2b18ccea8ad`
- Room 24 instrumented executable SHA-256: `8f9cc494666007d6cde60b80980067c6dc01992df957e9bc927b86be8c363631`
- Private comparison JSON SHA-256: `2513cd463517ac54a1cd0398c7ed109cd91f65c1b9619839d71dac8970190e9f`
- Engine frame 1 SHA-256: `4d598a4ad8e4bc57dd01913c03c986edd9534a5cd3fdbb41910c184d69996729`
- Engine frame 64 SHA-256: `02f84017d1e83e21917af2e9cdcd34acd1803f46f224900c44a792f2a0e22c0e`

## Palette initialization

The room CLUT was observed intact at the four low indices before entry scripts, in both Rooms 24 and 35. The installed global entry hooks were 5 and 6. At the post-ENCD boundary, hook 6 ran in video mode 19. Its [source-aligned VGA branch](https://github.com/87otlto-coder/Scummbucket/blob/research/mi2-spelunk-20261116/docs/research/MI2_GLOBAL_SCENE_HOOKS_5_6_7_ENTRY_EXIT_20261118.md) uses variables 469–480 as RGB triples for indices 2, 3, 1 and 6, respectively. Runtime probe readings of those operands matched the palette after the hook. Applying the source mapping to the literal CLUT and advancing the captured timer deltas yielded zero discrepancies before and after cycling for 64 Room 24 frames and 32 new clear-branch Room 35 frames. The helper requires explicit hook/mode and operand values. Exporting an archive-derived preview can still start from the original CLUT. Earlier debugger-equivalent Room 35 runs also pass their original seeded palette and layered indexed regression.

## Reproduction

Use the pinned Windows build tree, object/library flags and linker order in [the Room 35 runtime report](P4_ROOM35_RUNTIME_20261118.md). Generate the Room 24 overlay using `python -B -m tools.instrument_room24 <parent>/engines/scumm/scumm.cpp <fresh-build>/scumm.cpp`. For the scoped RNG and entry probe, also run `python -B -m tools.instrument_room24_probe <parent> <fresh-build>`, compile `script.cpp` and `script_v5.cpp` with the same flags, and include their object files alongside the overlay's `scumm.o` before the parent library group at link time.

```powershell
$root = 'F:\Dev\SCUMMBUCKET'
Set-Location "$root\SOURCE\ScummBucket"
$game = "$root\FIXTURE\GAMES\MonkeyIsland2_DOS_VGA"
$save = "$root\FIXTURE\CAPTURES\Room23\walk-20261110-a-normal\saves\monkey2.s01"
$out = "$root\FIXTURE\CAPTURES\Room24-$([guid]::NewGuid())"
python -B -m tools.run_room35_capture "$build\scummvm.exe" $game $save $out --room24
if ($LASTEXITCODE) { throw 'Room 24 capture failed' }
python -B -m tools.compare_room24_capture $game $out "$out\comparison.json"
```

`python -B -m scummbucket.room24_water GAME FRESH_OUTPUT EVENTS_JSON` accepts a JSON object with `candidates` in 1–3 and one `deltas` entry per accepted draw. The source preview preserves rejected candidates, palette counters, masks, indexed rasters, separate RGB and evidence labels. It exports the water component, while the bounded runtime comparator replays the captured scene. Natural entry, original DOS executable parity, archive-only mask composition, and cross-room source-only game-variable initialization remain open.

## Separate technical review of PR #19

The Room 35 milestone is technically suitable for the P4 engineering branch on the evidence available. The existing Windows suite and the private isolated Room 7 and Room 35 reruns cover the supported scope. The additive event schema preserves existing fields and evidence labels, the original RGBA decoder routes through its indexed core, and the preview and capture paths use exclusive outputs. Provenance distinguishes synthetic, archive-derived and debugger-equivalent inputs. Room 35's report correctly limited the original palette result to a runtime seed. The follow-up source mapping lives on the Room 24 branch. Capture and report evidence remain private.

Keep PR #19 in draft until the owner resolves the [existing source-lineage and distribution review](P4_INTEGRATION_CODE_LICENSE_REVIEW_20261112.md), including attribution for the ScummVM-derived instrumentation and the repository licensing decision. No automatic merge was performed. The canonical wrapper checkout gate remained blocked. The underlying Room 7 replay verified 87/87 frames and final palettes, with 778 expected mismatches in the ZP01 negative control.
