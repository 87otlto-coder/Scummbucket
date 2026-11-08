# P1 — SCUMM v5 archive inventory and raw chunk export prototype

**Status:** Implemented as a bounded P1 prototype; the overall P1 milestone is **not complete**.

## Run

Python 3.10+ is sufficient for the source-tree CLI (no third-party runtime packages).

**Standard Windows checkout:** `C:\Users\87otl\ScummBucket`

Open PowerShell and run:

```powershell
cd "C:\Users\87otl\ScummBucket"
python -m scummbucket inspect "C:\path\to\mi2.zip"
python -m scummbucket inspect "C:\path\to\mi2.zip" --json
New-Item -ItemType Directory -Force "C:\Users\87otl\ScummBucket\reports" | Out-Null
python -m scummbucket inspect "C:\path\to\MONKEY2.000" --output "C:\Users\87otl\ScummBucket\reports\mi2-inventory.json"

# Export room 4 palette-cycle chunks, removing the file-level XOR encoding:
python -m scummbucket extract "C:\path\to\mi2.zip" --room 4 --tag CYCL --output-dir "C:\Users\87otl\ScummBucket\exports\room-004-cycl"

# Export room 4 chunks as bytes stored in the original SCUMM container:
python -m scummbucket extract "C:\path\to\mi2.zip" --room 4 --output-dir "C:\Users\87otl\ScummBucket\exports\room-004-stored" --representation stored

# Extract exactly one indexed global script, by ID (not all scripts in room 4):
python -m scummbucket extract-id "C:\path\to\mi2.zip" --directory DSCR --id 12 --output-dir "C:\Users\87otl\ScummBucket\exports\script-012"

python -m unittest discover -s tests -v
```

Replace `C:\path\to\mi2.zip` with the location of your own archive. **Keep original game archives outside the repository**; the checkout root is for source, documentation and generated results under ignored `exports` and `reports` subfolders. Every extraction output directory must be a new destination because the command refuses to overwrite an existing manifest. The project path is a local documentation default, not a hard-coded application requirement.

`inspect --output` and `extract` use **exclusive file creation**: neither overwrites existing files. `extract` refuses an existing `manifest.json` to avoid unlabeled outputs and rejects a symlink output directory.

## What gets exported

The `extract` command exports **uninterpreted SCUMM chunks**, with their complete eight-byte chunk headers. `decoded` (the default) means **file-level XOR `0x69` removed only**, not decoded graphics, audio, scripts or animation. `stored` exports exact slices of `MONKEY2.001` in their original on-disk XOR representation.

The `manifest.json` records each output's room, tag, byte length, file-relative offset in the original `MONKEY2.001`, source filename and SHA-256, and hashes of the original stored slice, XOR-decoded chunk and exported file. The hashes are independently verified after write. Output filenames are generated from the selected room/tag/offset, not user-supplied filenames from inside the archive.

Operations are `success`, `partial`, or `failed`, with per-item success/failure and an explicit summary counting successes, failures, skips and unsupported items. One failed item does not prevent safe export of unaffected items. Known errors are included as structured diagnostic records; partial operations return a nonzero CLI exit code.

## Currently supported

- Read-only inspection and selective raw export of paired original DOS `MONKEY2.000` / `MONKEY2.001` files, inside a ZIP or directory.
- Version-specific XOR `0x69` signature check, source-file SHA-256, and bounded chunk/directory validation.
- Inventory of `LECF`, `LOFF`, `LFLF`, `ROOM` and direct room/bundle chunks, including source offsets.
- Palette-cycle (`CYCL`) metadata and multi-state `OBIM` image-state **candidates** (not proven active animations).
- JSON inventory and selected-chunk export with integrity hashes and manifest.
- Explicit failed/partial diagnostics and warnings, including output collisions and malformed input.
- Synthetic-only unit tests. Private integration checks against the supplied Monkey Island 2 archive.

## Directory resource-ID linking (P1 follow-up)

The inspector now adds `directory_links` to its JSON report. Each slot in `DROO` (rooms), `DSCR` (global scripts), `DSOU` (sounds), `DCOS` (costumes) and `DCHR` (character fonts) is reported as `linked`, `unused` or `failed`. Populated entries resolve through the room table and `LOFF` source position; the target must be an independently parsed chunk of the expected tag in the correct room.

The original DOS v5 room entries use the `DROO` slot ID as the room ID, with file number 1 and offset zero (the room's location comes from `LOFF`). For other resource types, the directory's room number identifies the `LOFF` room and the offset is relative to that room's `ROOM` chunk. This is derived from ScummVM's `getResourceRoomNr()`, `getResourceRoomOffset()` and `loadResource()` logic and verified against the supplied sample. It is **not** asserted for unrelated SCUMM versions or editions.

For the supplied MI2 resource fingerprints, **646 resource slots resolve correctly and 142 slots are unused; no populated references fail.** Unused slots are normal, not errors. The breakdown is 110 rooms, 167 scripts, 199 sounds, 162 costumes and 8 fonts. Source byte offsets and lengths are retained for each matched chunk. These are **resource references**, not decoded script or costume content.

Unexpected disk numbers, missing room targets, incorrect byte offsets, wrong chunk tags, repeated locations and inconsistent directory counts produce named diagnostics. Report status becomes `partial` when any of those represent an error; raw extraction refuses an incompletely validated inspection.

Ten additional synthetic-only linker tests cover valid linking, empty slots and deliberate failures. A GitHub Actions workflow runs the full Python synthetic test suite on pull requests.

## Targeted resource-ID extraction

A second command, `extract-id`, selects **one validated directory record**, avoiding the ambiguity of selecting a tag shared by many resources in a room:

```powershell
cd "C:\Users\87otl\ScummBucket"
python -m scummbucket extract-id "C:\path\to\mi2.zip" --directory DSCR --id 12 --output-dir "C:\Users\87otl\ScummBucket\exports\script-012"
```

Directory types: `DROO` (room), `DSCR` (global script), `DSOU` (sound), `DCOS` (costume) and `DCHR` (character font). IDs refer to index-directory **slots**, not room-local `LSCR` bytecode IDs. An empty slot gives `RESOURCE_SLOT_UNUSED` (failed request; skipped count 1); an out-of-range ID gives `RESOURCE_ID_OUT_OF_RANGE`. Any invalid source directory link blocks extraction rather than guessing a target.

The output is still a raw SCUMM chunk, including its eight-byte header. The manifest includes the exact directory type, resource ID, room, source offset, byte length and hashes. As for room exports, `decoded` means file XOR removed, not an interpreted costume, script, sound or image.

For the fingerprinted MI2 sample, the source index's `DSCR[12]` resolves to room 4, absolute source offset 228,779, `SCRP` chunk size 94 bytes. Its XOR-decoded chunk SHA-256 is `58bcbcff5f2bf5d60e4a66e1a2ea5cdf95ffa82566e982527ec7de6868abae12`. This is reproducible byte provenance, **not** evidence that script 12 runs a particular background animation.

### Optional private integration regression

The standard GitHub Actions workflow uses **only synthetic fixtures**. An authorized user with the exact fingerprinted MI2 sample can enable additional integration checks without copying commercial game files into GitHub:

```powershell
cd "C:\Users\87otl\ScummBucket"
$env:SCUMMBUCKET_MI2_ARCHIVE = "C:\path\to\mi2.zip"
python -m unittest discover -s tests -v
Remove-Item Env:\SCUMMBUCKET_MI2_ARCHIVE
```

When the variable is absent, the private test reports `skipped` explicitly. When present, it checks both file fingerprints, room/cycle/link counts, `DSCR[12]` provenance, one byte-exact raw script export and source archive immutability. If the files represent a different edition, the test **fails with an edition mismatch** rather than treating it as a successful regression.


## Scene relationships and background-animation candidates (P1 follow-up)

**New command:** `scenes` inspects the selected room's palette-cycle records, object identity/state pairs, room-local script chunks and global script/costume resources **stored** in the same room bundle.

From the standard Windows checkout, use PowerShell:

```powershell
cd "C:\Users\87otl\ScummBucket"
python -m scummbucket scenes "C:\path\to\mi2.zip" --room 34
python -m scummbucket scenes "C:\path\to\mi2.zip" --room 34 --json
```

Replace the example input with the actual authorized archive location. `--room` is optional (it otherwise shows all 110 rooms). Use `--output "C:\Users\87otl\ScummBucket\reports\room-034.json"` to write a new report; the parent directory must already exist, and existing files are never overwritten.

### Object-ID pairing and evidence semantics

SCUMM v5 `OBIM` image containers hold an `IMHD` object ID and declared image count; corresponding `OBCD` code containers hold a `CDHD` object ID. The new `scene_inventory` report matches **IDs, not chunk order**, and records both source locations and the number/tags of visual states.

Against the independently inspected MI2 sample, **1,145 object-image containers pair with 1,145 object-code containers by ID**. The image-state counts match the `IMHD` declarations; **158 paired objects have two or more visual states**. Palette cycling remains represented as **127 cycle records in 21 rooms**.

**Critical distinction:** "multistate object" is an **animation candidate**, not evidence of active movement. States may be interactive, scripted, or unused. `animation_observed` and `script_control_verified` remain false. Same-room `LSCR`, `ENCD` and `EXCD` chunks are listed by storage location only. Global `DSCR` and `DCOS` IDs mapped to that bundle are also **storage associations, not proven script calls or costume use**.

Malformed nested `IMHD`/`CDHD` structure, duplicate IDs and other resource-local anomalies produce named diagnostics. Structural object corruption results in a **partial** inspection, rather than disappearing from the inventory. Mismatched object IDs or image counts stay visible as warnings.

This inventory is a P1 prerequisite for P4 background-animation reconstruction, **not** a script interpreter or a rendered scene.

## SCUMM v5 object-state byte-pattern survey (P1 follow-up)

The `scenes` command now includes `script_state_candidates`, recorded with exact script IDs, source-file byte offsets, raw byte patterns, decoded candidate operands, and evidence qualifiers. It searches room-local `LSCR`, `ENCD`, and `EXCD` script payloads for known direct-object forms of `drawObject` and `setState`.

**Crucial limitation:** This is a **byte-wise pattern scanner**, not an instruction-aligned SCUMM decompiler. A matching byte sequence can occur inside another instruction's operands or text, and matching a code pattern does not establish that the engine executes that instruction. Each candidate explicitly sets `instruction_alignment_verified: false`, `runtime_execution_verified: false` and `script_control_verified: false`. This is *triage evidence* for subsequent instruction-boundary-aware decoding, not proof of background animation.

### Example: room 34, object 358

On the specifically fingerprinted private DOS MI2 sample, object **358** has **16 image states**, and a separate read-only scan of its room-local scripts found:

- **17 candidate opcode patterns**: **11** resembling `drawObject`, **6** resembling `setState`.
- The patterns occur in local **script 201** (7 draw, 4 set) and **script 202** (4 draw, 2 set).
- Four `drawObject` patterns use a variable state operand with raw reference **100**. The remaining draw patterns explicitly contain state **1**; the `setState` patterns contain state **0**.
- Other room objects may have candidate state patterns too; the example count above is **only for object 358**.

Examples of exact, reproducible offsets in XOR-decoded `MONKEY2.001`:

| Source byte offset (decimal) | Script | Bytes (hex) | Candidate reading |
| ---: | ---: | --- | --- |
| 2,742,765 | 201 | `05 66 01 02 01 00` | `drawObject(358, state=1)` |
| 2,742,844 | 201 | `05 66 01 82 64 00` | `drawObject(358, state=variable-reference 100)` |
| 2,744,442 | 201 | `07 66 01 00` | `setState(358, 0)` |
| 2,746,412 | 202 | `05 66 01 02 01 00` | `drawObject(358, state=1)` |

**Interpretation:** The table originated as unaligned raw matches. The user subsequently verified **all 17 object 358 opcode starts** with external `descumm`. That corroborates instruction starts for this specific object; **it still does not verify actual branch execution, image rendering or elapsed animation timing**. Other raw pattern matches remain unverified until individually checked.

References: [ScummVM `script_v5.cpp`](https://github.com/scummvm/scummvm/blob/master/engines/scumm/script_v5.cpp) (`setupOpcodes`, `o5_drawObject`, `o5_setState`, `getVarOrDirectWord`).

PowerShell from the standard project directory:

```powershell
cd "C:\Users\87otl\ScummBucket"
python -m scummbucket scenes "C:\path\to\mi2.zip" --room 34
python -m scummbucket scenes "C:\path\to\mi2.zip" --room 34 --json
```

Replace the example ZIP path with your authorized local archive. The human-readable output summarizes candidate counts by object; the JSON retains individual offsets for reproducible review.

## Independent v5 script-boundary verification (optional external tool)

ScummBucket can now compare an existing script-state byte-pattern candidate to a real instruction boundary emitted by the separately installed **ScummVM Tools** `descumm`. This avoids embedding its GPL implementation in ScummBucket.

**Installation:** Obtain the Windows ScummVM Tools package at https://www.scummvm.org/en/downloads/ and extract it outside the source checkout (for example `C:\Users\87otl\Tools\scummvm-tools`). Locate `descumm.exe` there. The CLI also supports an executable already on `PATH`.

```powershell
cd "C:\Users\87otl\ScummBucket"
$descumm = (Get-ChildItem "C:\Users\87otl\Tools\scummvm-tools" -Recurse -Filter descumm.exe -File | Select-Object -First 1).FullName

python -m scummbucket verify-descumm "D:\old" --room 34 --script 201 --object 358 --descumm "$descumm"
python -m scummbucket verify-descumm "D:\old" --room 34 --script 202 --object 358 --descumm "$descumm"
```

For machine-readable evidence, append `--json` or `--output "C:\Users\87otl\ScummBucket\reports\descumm-script-201.json"` (the reports folder must exist and the file must not already exist). No commercial script data or disassembler binary is written to GitHub.

The adapter validates the source archive SHA-256 against the in-memory inspection before extracting a temporary `LSCR`, runs `descumm -5 -o -h` with a timeout, parses only explicit emitted offset/opcode lines, and compares them with the candidate raw bytes. It returns:

- `confirmed_opcode_start` only when the external disassembler emits the expected opcode at that script body offset;
- `not_emitted` for unmatched byte-pattern candidates (inconclusive, **not** automatically rejected);
- `opcode_conflict` plus a diagnostic for an inconsistent emitted opcode;
- an explicit failure if the tool is missing, times out, crashes, produces incomplete output, or reports inconsistent instruction offsets.

**This is verification of instruction start positions only**, not executable reachability, actual object-state transitions, or animation timing.

**Verification status:** On 2026-11-07, the user supplied Windows output from real `descumm` runs: all **11** object 358 candidates in script 201 and all **6** in script 202 matched expected instruction starts, with no unmatched candidates or opcode conflicts. The research environment itself has not executed the external tool. GitHub Actions uses **mocked** external disassembler output; its passing tests are not the source of the real-script result. A separate opt-in `tests/test_private_descumm.py` test now reproduces the real comparison when both local inputs are explicitly provided.

Reference: [Object 358 script evidence register](research/P1_OBJECT_358_SCRIPT_SURVEY.md).

## Verified room 34 script behavior: number selection, not autonomous looping

The user supplied complete external `descumm` reports for local scripts **201** and **202**. Their original UTF-16LE report hashes and source-provenance details are recorded in the [behavior analysis](research/P1_ROOM34_OBJECT_BEHAVIOR.md).

Both scripts contain branch-dependent instructions to display object **358** in state **1**, select a randomized number image via `Var[100]`, and reset its state to **0** on specified paths. Engine semantics establish that `getRandomNr(2)` returns 0, 1 or 2, so the selection expression for `n=1..5` is `min(15, 3*n-1+r)` with `r=0..2`.

The complete analysis records:

- The two demonstration scripts, their conditional/dialogue paths and instruction offsets.
- `breakHere()`, `WaitForMessage()`, and `delay` as **script timing constructs**, not measured seconds or playback frames.
- Object **357** as an actor-position anchor and reset target, without assuming synchronized animation with 358.
- The distinction between **script-driven interaction**, **autonomously repeating scenery**, and **observed runtime effects**.
- All four unresolved `CYCLE_FLAGS_UNVERIFIED` warnings; successful disassembly does not remove them.

The [17-event machine-readable evidence register](research/P1_ROOM34_OBJECT_EVENTS.json) stores derived offsets and operand classifications only; it does not contain commercial game bytes. Five tests guard its internal consistency, but those tests do not independently prove gameplay behavior.

**P4 consequence:** A fixed 16-frame looping export would *not* faithfully reconstruct this interactive object. A conditional, parameterized state sequence is a better candidate once asset rendering, branching and timing are independently verified.

## Early P2 image-state decoding experiment

A **separate experimental** `images` command has been added while the P1 inventory work remains open. It selects one validated `OBIM` object, decodes supported SCUMM v5 `SMAP` strip compression into native-size RGBA PNGs, and exports separate grayscale `ZPxx` depth-mask PNGs. It uses the room's 256-entry `CLUT` and `TRNS` transparent color, without Pillow or other runtime graphics dependencies.

For the fingerprinted room 34 object 358, independent read-only testing decoded all **16 image states at 56 × 40 pixels** and **48 mask planes**. A user-side private integration test is included but skipped in public CI. The pixel output has **not** yet been validated against ScummVM's actual runtime rendering or dynamic palette behavior.

```powershell
cd "C:\Users\87otl\ScummBucket"
$stamp = Get-Date -Format "yyyyMMdd-HHmmss"
$out = "C:\Users\87otl\ScummBucket\exports\room34-object358-$stamp"
python -m scummbucket images "D:\old" --room 34 --object 358 --output-dir "$out"
```

For complete limitations, implementation details and confidence levels, see [P2 experimental image-state decoder](research/P2_MI2_OBIM_STATE_DECODING.md). Do **not** treat this as completion of P2, or mistake the puzzle object's conditional state changes for an autonomous background loop.

The separate [autonomous palette-animation candidate survey](research/P4_PALETTE_CYCLE_CANDIDATES.md) identifies rooms 23 and 109 as good research controls, while explicitly retaining the four unresolved cycle-flag warnings.

## Early P4 palette-cycle research probe

The optional palette-probe command builds **hypothetical** palette snapshots from a native indexed room background and the room's original CYCL data. It reuses the existing limited strip decoder, independently preserving source palette indices rather than baking the static palette into the pixel buffer.

Source observations from the fingerprinted original DOS MI2 archive:
- **Room 23:** 320 x 144 indexed background, eight cycle records, **480 pixels using cycled palette indices**; simulated 35 and 71 counter-unit updates change 65 and 373 RGB pixel positions relative to the initial palette.
- **Room 109:** 320 x 200 indexed background, five cycle records, **65 pixels using cycled indices**; the same hypothetical updates change 50 and 30 positions.
- ScummVM's cycle setup derives an internal threshold as integer **16384 / raw rate**; its runtime cycle update adds `max(VAR_TIMER, VAR_TIMER_NEXT)` counter units. The probe defaults to **one synthetic counter unit per update**, with `--counter-increment` available for explicitly hypothetical alternatives. Neither setting assigns real milliseconds or establishes the engine's actual update cadence.

```powershell
cd "C:\Users\87otl\ScummBucket"
$stamp = Get-Date -Format "yyyyMMdd-HHmmss"
$out = "C:\Users\87otl\ScummBucket\exports\room23-palette-$stamp"
python -m scummbucket palette-probe "D:\old" --room 23 --ticks 0 35 71 107 --output-dir "$out"
```

It exports PNG snapshots at the original room dimensions plus a manifest containing source hashes, exact cycle records, synthetic counter units, palette hashes, changed-pixel counts and diagnostics. There is **no claim of real game animation playback**. Actors, objects, room depth masks, script-side cycle changes, game scheduler timing and independent pixel comparison against ScummVM remain unverified.

A separate **`verify-palette-trace`** command can compare a strict, externally recorded ScummVM palette trace against the decoded source palette and actual captured timer variable values, reporting the first mismatch and affected palette indices. The trace file must include full RGB palette bytes, game fingerprint, engine revision and an exact `cyclePalette` capture point. Only **synthetic trace comparisons** have been tested to date. No real engine palette-state trace or exact playback timing has been verified. See [runtime verification procedure](research/P4_RUNTIME_PALETTE_VERIFICATION.md).

See the [palette-cycle candidate register and exact observations](research/P4_PALETTE_CYCLE_CANDIDATES.md). The four existing CYCLE_FLAGS_UNVERIFIED warnings remain present.

## Not yet supported / limitations

- Exact retail edition identification by trusted fingerprint; structural compatibility is not conclusive.
- Automatic archive-wide or arbitrary byte-range extraction. Export selection deliberately requires a room, and may optionally specify a chunk tag.
- Directory IDs now locate global scripts, costumes and sounds; scene inventory pairs object IDs and records nearby resources by storage. **Full bytecode interpretation, instruction-aligned script-to-object dependencies, and verified animation playback remain unimplemented.**
- Recovery of individual malformed resource chunks when the outer room structure fails validation: the current inspector stops safely for that input.
- Complete room/background, character costume, animation playback, script interpreter, or audio decoding. The limited P2 `OBIM` image-state decoder and the P4 research-only indexed-background/palette probe remain **experimental**.
- Monkey Island 1 or other editions/SCUMM versions.
- Playback/reference comparison against ScummVM or verified original gameplay.

## Verification

- **GitHub Actions: 127 tests discovered, 124 passed, 3 optional private-integration tests skipped, 0 failures** ([verified workflow run](https://github.com/87otlto-coder/Scummbucket/actions/runs/42464447892)). The new delta-model and external palette-trace comparisons use **synthetic fixtures**, not gameplay data. Private-archive validation remains opt-in, and the user previously completed real `descumm` instruction checks for scripts 201 and 202.
- User-supplied MI2 ZIP passed structural inventory: 110 rooms, 127 palette-cycle records in 21 rooms and 158 multi-state object images.
- New resource-ID extraction tests cover two distinct scripts sharing a room, exact byte matches in both representations, empty and invalid slots, corrupt links, overwrite refusal and the new CLI.
- Room 4 `CYCL` chunk exports in both `decoded` and `stored` modes were verified byte-for-byte against the original `MONKEY2.001` source slices.
- Four warnings concerning unverified palette-cycle flags are intentionally preserved; they are not parse failures.
- A ZIP labeled `mi1.zip` did not contain The Secret of Monkey Island and was rejected as unsupported (`GAME_PAIR_NOT_FOUND`).

## Optional local original-game validation

The repo includes an integration test for the fingerprinted MI2 sample, but the test is **skipped in GitHub Actions** because proprietary game archives are never committed.

To run it privately on your own Windows machine, set the environment variable to your authorized game archive path, then run the tests:

```powershell
cd "C:\Users\87otl\ScummBucket"
$env:SCUMMBUCKET_MI2_ARCHIVE = "C:\path\to\mi2.zip"
python -m unittest discover -s tests -v
Remove-Item Env:\SCUMMBUCKET_MI2_ARCHIVE
```

To also repeat the **real `descumm` instruction-alignment regression**, use both environment variables:

```powershell
$env:SCUMMBUCKET_MI2_ARCHIVE = "D:\old"
$env:SCUMMBUCKET_DESCUMM = "C:\Users\87otl\Tools\scummvm-tools\descumm.exe"
python -m unittest discover -s tests -v
Remove-Item Env:\SCUMMBUCKET_MI2_ARCHIVE
Remove-Item Env:\SCUMMBUCKET_DESCUMM
```

The separate private disassembly test expects 11 verified starts in local script 201 and 6 in script 202, with no unmatched candidate or opcode conflicts. Source fingerprints prevent silently accepting another edition. The tests still do not prove gameplay execution or animation timing.

The integration test expects the **specific SHA-256 fingerprints** recorded in the P0 research documents. A different, legitimate MI2 edition may fail this exact fixture; that is an edition-mismatch signal and must not be presented as proof the game archive is corrupted.

## Privacy and project discipline

Do not commit game archives, extracted graphics, audio, ROMs or other commercial assets. All committed unit-test fixtures are synthetic. The private MI2 integration archive stays outside GitHub. The original input files are opened read-only; exports require user-selected destination paths.

## Next P1 acceptance work

1. **Completed for object 358:** Independently confirmed all 17 opcode starts; examined the two real script reports and documented state selection. An experimental pixel and depth-mask decoder is now available. **Next:** run the private integration test and compare visual output against ScummVM before claiming pixel fidelity, executed gameplay behavior or duration.
2. Expand structured resource-level recovery diagnostics where an isolated malformed chunk can be safely skipped.
3. Add archive/version identification and signature regression fixtures.
4. Verify reproducible extraction across more resource classes and strengthen source provenance fields.
5. Match the P0 acceptance criteria before declaring P1 complete.
