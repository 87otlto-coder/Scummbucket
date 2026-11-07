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

A limited, read-only command-line prototype is available on the P1 feature branch. It currently supports the original DOS Monkey Island 2 `MONKEY2.000` / `MONKEY2.001` pair only. This is an **inventory, diagnostics and selective raw-chunk export tool**, not yet an image, animation or audio decoder.

On Windows, the standard local project directory is `C:\Users\87otl\ScummBucket`. From PowerShell, run:

```powershell
cd "C:\Users\87otl\ScummBucket"
python -m scummbucket inspect "C:\path\to\mi2.zip" --json
python -m scummbucket extract "C:\path\to\mi2.zip" --room 4 --tag CYCL --output-dir "C:\Users\87otl\ScummBucket\exports\room-004-cycl"
python -m scummbucket extract-id "C:\path\to\mi2.zip" --directory DSCR --id 12 --output-dir "C:\Users\87otl\ScummBucket\exports\script-012"
python -m scummbucket scenes "C:\path\to\mi2.zip" --room 34
python -m scummbucket verify-descumm "C:\path\to\mi2.zip" --room 34 --script 201 --object 358 --descumm "C:\path\to\descumm.exe"
python -m unittest discover -s tests -v
```

Replace `C:\path\to\mi2.zip` with the location of your own game archive. Export files go under `exports\` rather than the project root. The source archive should remain outside the repository; the project path is a documentation convention, **not hard-coded into the tool**.

The `extract-id` command exports one validated resource by directory type and ID, with byte-exact source provenance. Global script 12 in the supplied MI2 sample, for example, is a 94-byte `SCRP` chunk. This does **not** interpret the script instructions.

The `scenes` command pairs `OBIM` and `OBCD` by their actual object IDs, reports multi-state image candidates, lists room palette cycles and nearby script/costume storage context, and records **raw opcode-pattern candidates** from room-local scripts with exact offsets. The raw scanner itself cannot confirm instruction alignment; that requires separate disassembly verification. In the private sample, **all 1,145 object-image chunks match object-code chunks by ID**, and **158 paired objects contain multiple visual states**. This is not evidence that the states animate during gameplay.

The inspector now resolves index directory IDs to individual room, script, sound, costume and font chunks. The supplied MI2 sample resolves **646 populated references**, with **142 unused slots** and zero reference mismatches. This does not mean scripts or assets have been decoded.

The optional `verify-descumm` command can check candidate instruction boundaries against the separately installed ScummVM Tools disassembler. The tool is available from [official ScummVM downloads](https://www.scummvm.org/en/downloads/). **The user completed the external verification on Windows:** all 17 candidate instruction starts in local scripts 201 (11) and 202 (6) matched, with zero conflicts or missing starts. This is evidence of instruction alignment, **not** runtime execution or animation timing. The CI tests still use mocked disassembler output; the new optional private integration test can reproduce the real check on a local machine.

For object **358**, the fingerprinted MI2 sample contains **17 independently confirmed opcode starts** across room 34 scripts 201 and 202 (**11 drawObject / 6 setState**). The user-supplied disassembly also establishes **interaction-driven state selection**: `min(15, 3*n-1+r)` for number `n=1..5` and random `r=0..2`. That does **not** establish gameplay execution, rendered appearance or fixed animation timing. See the [original evidence register](docs/research/P1_OBJECT_358_SCRIPT_SURVEY.md), [behavior analysis](docs/research/P1_ROOM34_OBJECT_BEHAVIOR.md) and [machine-readable event metadata](docs/research/P1_ROOM34_OBJECT_EVENTS.json).

See [P1 prototype documentation](docs/P1_PROTOTYPE.md) for supported behavior, failure reporting and remaining limitations. The sample game files must remain outside the repository.

## Current status

P0 format research is documented in [PR #2](https://github.com/87otlto-coder/Scummbucket/pull/2) and remains open. This branch introduces the first **P1 inspection and raw extraction prototype** in [PR #3](https://github.com/87otlto-coder/Scummbucket/pull/3). It has been tested against one user-supplied MI2 archive and synthetic fixtures, but **P1 is not complete**: script dependency interpretation, resilient per-resource recovery, advanced provenance verification and cross-edition support are still outstanding.

Commercial game files and extracted copyrighted game assets must not be committed to this repository. Use authorized local copies for integration testing; favor synthetic fixtures in version control.

Repository: https://github.com/87otlto-coder/Scummbucket
