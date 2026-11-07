# P1 — SCUMM v5 archive inventory and raw chunk export prototype

**Status:** Implemented as a bounded P1 prototype; the overall P1 milestone is **not complete**.

## Run

Python 3.10+ is sufficient for the source-tree CLI (no third-party runtime packages):

```bash
python -m scummbucket inspect /path/to/mi2.zip
python -m scummbucket inspect /path/to/mi2/ --json
python -m scummbucket inspect /path/to/MONKEY2.000 --output /new/path/report.json

# Choose one room, and optionally one chunk type.
python -m scummbucket extract /path/to/mi2.zip --room 4 --tag CYCL --output-dir /new/path/cycles
python -m scummbucket extract /path/to/mi2.zip --room 4 --output-dir /new/path/room-4 --representation stored

python -m unittest discover -s tests -v
```

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

## Not yet supported / limitations

- Exact retail edition identification by trusted fingerprint; structural compatibility is not conclusive.
- Automatic archive-wide or arbitrary byte-range extraction. Export selection deliberately requires a room, and may optionally specify a chunk tag.
- Complete directory-resource ID links into scripts, costumes and sounds.
- Recovery of individual malformed resource chunks when the outer room structure fails validation: the current inspector stops safely for that input.
- Image, sprite/costume, palette pixel, animation, script or audio decoding.
- Monkey Island 1 or other editions/SCUMM versions.
- Playback/reference comparison against ScummVM or verified original gameplay.

## Verification

- **26 synthetic unit tests passed** on the prototype (15 inventory tests + 11 export tests).
- User-supplied MI2 ZIP passed structural inventory: 110 rooms, 127 palette-cycle records in 21 rooms and 158 multi-state object images.
- Room 4 `CYCL` chunk exports in both `decoded` and `stored` modes were verified byte-for-byte against the original `MONKEY2.001` source slices.
- Four warnings concerning unverified palette-cycle flags are intentionally preserved; they are not parse failures.
- A ZIP labeled `mi1.zip` did not contain The Secret of Monkey Island and was rejected as unsupported (`GAME_PAIR_NOT_FOUND`).

## Privacy and project discipline

Do not commit game archives, extracted graphics, audio, ROMs or other commercial assets. All committed unit-test fixtures are synthetic. The private MI2 integration archive stays outside GitHub. The original input files are opened read-only; exports require user-selected destination paths.

## Next P1 acceptance work

1. Validate and link index directory resource IDs to underlying chunks and container offsets.
2. Expand structured resource-level recovery diagnostics where an isolated malformed chunk can be safely skipped.
3. Add archive/version identification and signature regression fixtures.
4. Verify reproducible extraction across more resource classes and strengthen source provenance fields.
5. Match the P0 acceptance criteria before declaring P1 complete.
