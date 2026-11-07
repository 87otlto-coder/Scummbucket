# ScummBucket — Project Charter & Roadmap

**Status:** Planning and research  
**Version:** 0.3  
**Repository:** https://github.com/87otlto-coder/Scummbucket

## Vision

Create a reliable, extensible toolkit for investigating, extracting, reconstructing and exporting assets from classic LucasArts SCUMM games.

ScummBucket should allow users to explore original resources, view animated characters and backgrounds, reconstruct supported scene elements, and export assets at original or enhanced resolutions.

**Background animation is a core project objective, not an optional extension.**

The project is not intended to replace ScummVM or become a general-purpose game interpreter.

## Primary Objectives

1. Identify and inspect supported original game archives.
2. Extract resources with complete, reproducible provenance.
3. Decode static backgrounds, objects, sprites and animation resources.
4. Investigate and reconstruct background animations, including scripted and layered effects where feasible.
5. Reconstruct character animation sequences.
6. Extract and classify audio resources.
7. Export resources into practical, widely supported formats.
8. Provide asset-level HD scaling and enhanced pixel-art export options.
9. Create an interactive resource exploration interface.
10. Extend compatibility to other SCUMM games and editions incrementally.
11. Maintain transparent error reporting and diagnostic records throughout the extraction process.

## Initial Game Coverage

**First target:** Monkey Island 2: LeChuck's Revenge — original DOS VGA release.

**Second target:** The Secret of Monkey Island — original DOS editions.

**Future candidate:** The Curse of Monkey Island, including its more advanced animated scenes and video-related formats.

Additional SCUMM versions, platforms and games remain future possibilities. Compatibility must be demonstrated for individual game editions.

## Development Roadmap

### P0 — Format Research and Validation

Investigate ScummVM, existing tools and relevant original resource formats. Pay particular attention to the distinction between static room graphics and components responsible for background animation.

**Deliverables:**
- Reference source map.
- Preliminary resource-format documentation.
- Game-edition identification strategy.
- Evidence and uncertainty register.
- Background-animation mechanism survey.
- Initial testing and acceptance criteria.

**Exit criterion:** Sufficient verified understanding to implement an archive reader and identify promising examples for animation research.

### P1 — Archive Reader and Resource Inventory

Implement game identification, archive parsing, resource indexing and raw extraction.

**Deliverables:**
- Command-line inspection utility.
- Structured resource inventory.
- Resource IDs, sizes and source locations.
- Input validation and diagnostics.
- Reproducible extraction manifest.
- Identification of potentially animation-related resources and references.
- Structured errors and warnings for invalid, missing, unsupported or unreadable resources.

**Exit criterion:** Validated archive inventory and raw extraction, with unresolved or potentially animated resources recorded rather than discarded. Failed resource operations must be visible in the inventory or diagnostic report.

### P2 — Background and Image Extraction

Implement room image decoding, palette handling and image export. Begin identifying the resources and mechanisms associated with animated scenery.

**Deliverables:**
- Decoded static room images.
- PNG export.
- Faithful native-resolution images.
- Nearest-neighbor HD scaling.
- Palette handling and verification.
- Inventory of room objects, alternate visual states and potential animation components.
- Comparison tests against reference rendering.

**Exit criterion:** Representative static images decode accurately, and candidate background-animation resources are identified for subsequent reconstruction. Decode failures and unsupported image variants are recorded.

### P3 — Costumes, Sprites and Character Animation

Implement costume parsing, cel rendering and character animation reconstruction.

**Deliverables:**
- Individual sprite/cel extraction.
- Transparent images.
- Animation sequence metadata.
- Directional animation support.
- Frame sequences and sprite sheets.
- Native and scaled exports.

**Exit criterion:** Representative character animations reconstruct faithfully, with documented coverage of placement, palettes and timing. Failed or incomplete animation reconstructions must be identifiable.

### P4 — Background Animation and Scene Reconstruction

**Priority milestone.**

Investigate and reconstruct animated room elements rather than limiting the extractor to static backgrounds.

Relevant mechanisms may include:
- Animated room objects and alternate visual states.
- Palette cycling and palette-driven effects.
- Costumes or sprites used as environmental animations.
- Layered graphics and masking.
- Script-controlled animation sequences.
- Moving scene elements and scrolling where applicable.
- Other game-specific animation mechanisms identified through research.

**Deliverables:**
- Classification of background-animation mechanisms.
- Decoded object states and animation components.
- Supported animation sequences with frame/timing metadata.
- Layering and position information.
- Background-only and separated-layer exports where feasible.
- Animation preview and export formats, potentially including PNG sequences, animated WebP or other appropriate formats.
- Reconstructed scene previews where feasible.
- Clear distinction between observed, directly decoded and inferred animation behavior.
- Regression tests covering representative animated scenes.

**Exit criterion:** Representative background animations can be reconstructed and verified against ScummVM or observed gameplay, with unsupported mechanisms documented explicitly.

Partial support must never be reported as comprehensive background-animation coverage. Failed reconstructions must be reported.

### P5 — Audio Extraction

Investigate and implement supported sound-resource formats.

**Deliverables:**
- Audio resource inventory.
- Format classification.
- Raw sound-resource exports.
- Decoded audio export where supported.
- Playback and output verification.

**Exit criterion:** Known supported formats extract reliably and unsupported formats or failed conversions are documented.

### P6 — Visual Asset Explorer

Build the interface over the validated extraction engine.

**Deliverables:**
- Archive and resource browser.
- Resource categorization and search.
- Static background previews.
- Character animation playback.
- Background animation playback where supported.
- Layer and object inspection.
- Audio playback.
- Individual and batch exports.
- Export resolution controls.
- Clear status indicators and accessible diagnostic details for unsuccessful operations.

**Exit criterion:** The interface reliably exposes supported resource and animation capabilities without duplicating decoding logic or concealing failures.

### P7 — Advanced HD Rendering

Extend the original scaling functionality with established pixel-art enhancement algorithms.

**Deliverables:**
- License-compatible additional scaling filters.
- Resolution and aspect-ratio options.
- Transparent sprite enhancement.
- Consistent scaling across animation frames.
- Background and foreground layer alignment.
- Batch HD image and animation exports.
- Quality and fidelity comparisons.

**Exit criterion:** Enhanced output can be reproduced from original decoded assets without compromising alignment, transparency, timing or relevant scene relationships. Errors in scaling or batch exports must be reported.

### P8 — Extended Capabilities

Investigate additional capabilities according to evidence and project value.

**Potential extensions:**
- MIDI and iMUSE music extraction or reconstruction.
- Advanced script-controlled sequences.
- The Curse of Monkey Island and its relevant animation/video formats.
- Additional SCUMM games and platforms.
- More sophisticated scene reconstruction.
- Experimental AI-assisted HD enhancement.
- Additional export integrations.

Each extension requires its own technical investigation and acceptance criteria.

## Technical Approach

The architecture should contain independently testable layers:

1. Game identification and input handling.
2. Archive parsing and resource indexing.
3. Resource-specific decoding.
4. Character animation reconstruction.
5. Background animation and scene composition.
6. Rendering and enhancement.
7. Asset and metadata export.
8. User interface.

Structured error handling and diagnostics must be available across these layers.

Python is a provisional starting option, not a mandatory long-term choice. Dependencies and implementation approaches should be selected according to evidence, maintainability, performance and licensing.

## Export Principles

Always preserve original decoded resources before enhancement.

Candidate export formats include PNG, transparent PNG sequences, sprite sheets, suitable animated formats, WAV and JSON metadata.

Animation exports should retain established frame ordering, timing, positioning, transparency and relevant composition metadata.

Nearest-neighbor is the default scaling method. Additional established pixel-art filters are optional. AI enhancement is deferred.

## Error Reporting and Diagnostics

**Every error must remain observable and traceable.**

Errors should include enough context to identify which resource or operation failed, what happened and whether other operations were affected.

Batch operations must distinguish successful, failed, skipped and unsupported resource counts.

Recoverable errors may allow safe continuation, but remain visible. Fatal errors stop the affected operation safely and provide diagnostics. A fallback or partial result must never be represented as full success.

Detailed logs must remain available even if the interface provides a shorter summary.

## Testing and Evidence

Major decoders and reconstruction mechanisms should be tested using representative original assets.

Testing should cover:
- Valid resource parsing and offsets.
- Corrupt and unsupported input.
- Image dimensions, colors and palettes.
- Sprite transparency and animation.
- Background animation classification and reconstruction.
- Frame order, timing and looping.
- Object layering, positioning and masking.
- Export correctness.
- Error handling, recovery and diagnostic accuracy.
- Regression testing.
- Comparison with ScummVM and other suitable references.

Use synthetic, non-copyrighted fixtures for automated tests where practical. User-supplied commercial archives may be used for private integration testing but must not be committed.

Representative success is not proof of complete game coverage.

## Roadmap Change Policy

The roadmap provides a defined direction while allowing evidence-driven adjustments.

Changes may be justified by verified findings, technical obstacles, meaningful risk reduction or explicit changes in project priorities.

Material changes should document the reason, impact, trade-offs and verification requirements. Minor refinements can proceed without formal approval; major architectural or scope changes require approval.

Background animation must not be silently deprioritized merely because static extraction is easier.

## Definition of Done

A milestone is complete when:
- Agreed deliverables exist.
- Relevant tests have been performed.
- Acceptance criteria are satisfied.
- Failures, warnings and limitations are reported.
- No known error has been deliberately concealed or misrepresented.
- Partial successes are clearly distinguished from complete successes.
- Outputs are reproducible.
- Repository status is clear.

Static background extraction does not constitute completed background-animation support. A feature demonstrated on one example is not automatically complete across an entire game or format.

## Current Project State

- Project name finalized as ScummBucket.
- GitHub repository renamed and verified at 87otlto-coder/Scummbucket.
- ScummVM confirmed as the main technical reference.
- Preliminary feasibility research completed.
- Original-fidelity and HD export priorities established.
- Background animation elevated to a first-class development objective.
- Transparent error reporting established as a mandatory project requirement.
- No original-archive integration testing completed.
- Next milestone: P0 — format investigation, including a focused study of background-animation mechanisms.
