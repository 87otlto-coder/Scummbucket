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

Replace `C:\path\to\mi2.zip` with the location of your own archive. **Keep original game archives outside the repository**; the checkout root is for source, documentation and generated results under ignored `exports\` and `reports\` subfolders. Every extraction output directory must be a new destination because the command refuses to overwrite an existing manifest. The project path is a local documentation default, not a hard-coded application requirement.

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


## Not yet supported / limitations

- Exact retail edition identification by trusted fingerprint; structural compatibility is not conclusive.
- Automatic archive-wide or arbitrary byte-range extraction. Export selection deliberately requires a room, and may optionally specify a chunk tag.
- Directory IDs now locate global scripts, costumes and sounds; **script bytecode interpretation and cross-resource dependency graphs** remain unimplemented.
- Recovery of individual malformed resource chunks when the outer room structure fails validation: the current inspector stops safely for that input.
- Image, sprite/costume, palette pixel, animation, script or audio decoding.
- Monkey Island 1 or other editions/SCUMM versions.
- Playback/reference comparison against ScummVM or verified original gameplay.

## Verification

- **26 prior synthetic unit tests passed** on the prototype (15 inventory tests + 11 export tests).
- User-supplied MI2 ZIP passed structural inventory: 110 rooms, 127 palette-cycle records in 21 rooms and 158 multi-state object images.
- Ten new synthetic linker tests and one integrated failure-status test are included; the **full 37-test synthetic suite passed in GitHub Actions** on the current feature branch.
- Room 4 `CYCL` chunk exports in both `decoded` and `stored` modes were verified byte-for-byte against the original `MONKEY2.001` source slices.
- Four warnings concerning unverified palette-cycle flags are intentionally preserved; they are not parse failures.
- A ZIP labeled `mi1.zip` did not contain The Secret of Monkey Island and was rejected as unsupported (`GAME_PAIR_NOT_FOUND`).

## Privacy and project discipline

Do not commit game archives, extracted graphics, audio, ROMs or other commercial assets. All committed unit-test fixtures are synthetic. The private MI2 integration archive stays outside GitHub. The original input files are opened read-only; exports require user-selected destination paths.

## Next P1 acceptance work

1. Move from verified resource-ID export to a conservative script/animation candidate map, without claiming script execution or confirmed background playback.
2. Expand structured resource-level recovery diagnostics where an isolated malformed chunk can be safely skipped.
3. Add archive/version identification and signature regression fixtures.
4. Verify reproducible extraction across more resource classes and strengthen source provenance fields.
5. Match the P0 acceptance criteria before declaring P1 complete.
