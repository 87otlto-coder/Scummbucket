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

## Current status

P0 (format research and validation) is next. No complete archive reader or verified original-game extraction implementation has been established in this repository.

Commercial game files and extracted copyrighted game assets must not be committed to this repository. Use authorized local copies for integration testing; favor synthetic fixtures in version control.

Repository: https://github.com/87otlto-coder/Scummbucket
