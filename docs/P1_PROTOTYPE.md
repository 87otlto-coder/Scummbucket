# P1 — Read-only archive inventory prototype

**Status:** Small, testable prototype; P1 milestone **not** complete.

## Run

Python 3.10+ is sufficient for the source-tree CLI (no third-party runtime modules):

```bash
python -m scummbucket inspect /path/to/mi2.zip
python -m scummbucket inspect /path/to/mi2/ --json
python -m scummbucket inspect /path/to/MONKEY2.000 --output /new/path/report.json
python -m unittest discover -s tests -v
```

`--output` uses exclusive file creation: it refuses to overwrite any existing file, including an original game archive.

## Currently supported

- Read-only inspection of paired `MONKEY2.000`/`MONKEY2.001` files, from a ZIP or directory, with an explicit XOR `0x69` signature check.
- Validation of top-level SCUMM v5 index chunk directories (`DROO`, `DSCR`, `DSOU`, `DCOS`, `DCHR`) and presence of `DOBJ`, `RNAM` and `MAXS`.
- Validating `LECF`, `LOFF`, `LFLF`, `ROOM` boundaries, room ID references and nested room chunks.
- Resource-inventory output with byte offsets, chunk lengths, tag, room identity and source-file SHA-256.
- Palette-cycle (`CYCL`) metadata and multi-image `OBIM` state **candidates**; neither is proof of active animation.
- Structured error/warning diagnostics and explicit failed status for input failures.

## Not yet supported

- Exact game edition identification by trusted fingerprint.
- Raw resource export, manifest with file outputs or independent extraction checksums.
- Image, costume, palette graphics, animation, script or audio decoding.
- Full linking of resource IDs with image/object/script contents.
- Monkey Island 1 and other SCUMM versions.
- Recoverable per-resource errors and partial-success reporting (currently a structural error fails the inspection).
- Reference rendering validation against ScummVM.

## Privacy and project discipline

Do not commit game archives, extracted images, ROMs, MIDI dumps or other copyrighted game data. The committed tests build synthetic chunks in memory.

**Source processing is read-only**, and output files cannot overwrite existing paths.

## Error-reporting approach

Each failure is represented as an explicit diagnostic with severity, code, message and optional source path, byte offset and resource type. Warnings are retained in the JSON report even when the overall structural inspection succeeds. Unusual palette-cycle flags are reported rather than discarded or reinterpreted. Known harmless all-zero alignment bytes are not misreported as failures.

Future iterations should add recoverable failure states, complete provenance, stable resource identity, source hashes in each diagnostic, and machine-readable per-resource statuses.
