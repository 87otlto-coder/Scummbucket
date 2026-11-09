# ScummBucket — Standing Project Instructions

**Project repository:** https://github.com/87otlto-coder/Scummbucket  
**Primary technical reference:** https://github.com/scummvm/scummvm

## Project Identity

ScummBucket is an evidence-driven asset extraction, reconstruction and exploration project for classic SCUMM-based games.

**Primary targets:** Monkey Island 2: LeChuck's Revenge and The Secret of Monkey Island, initially focusing on original DOS releases.

The ultimate goal is to extract, inspect, reconstruct, preview and export original game resources, including static and animated backgrounds, character sprites and animations, objects, audio and eventually music.

The project must support faithful extraction first, with asset-level HD scaling and more advanced reconstruction added incrementally. It is not intended to replace ScummVM.

## Non-Negotiable Rules

### 1. Evidence over assumptions

Base technical decisions on verified source code, documented formats, observed game data or reproducible experiments. Distinguish confirmed facts from hypotheses and unknowns. Never present speculation as verified findings.

### 2. Research before implementation

Investigate established solutions before developing decoders, parsers, scaling algorithms or substantial features. Do not reinvent proven solutions without a documented reason.

### 3. Independent verification

Use ScummVM as a primary technical reference, but independently verify applicable behavior against original game files wherever possible.

### 4. Original data integrity

Never modify original game archives. Preserve source identification, resource offsets, sizes, checksums, palette information and other relevant provenance. Keep faithfully decoded originals separate from processed outputs.

### 5. Always report errors. Never hide them.

This applies to development, testing, extraction, reconstruction, export and repository operations.

- Never silently suppress exceptions, failed validations, unsupported resources or unsuccessful operations.
- Never report partial success as complete success.
- Never substitute fallback output without identifying the fallback.
- Record errors with enough context to diagnose and reproduce them.
- Distinguish errors, warnings, unsupported behavior and expected limitations.
- Report failed tests, regressions and unresolved problems explicitly.
- Never claim that an operation succeeded unless the result was verified.
- Continue processing unaffected resources where safe, while recording failures.
- Provide concise user-facing summaries while retaining detailed diagnostic logs.

A failed operation is acceptable. An unexplained or concealed failure is not.

### 6. Extraction and reconstruction are different

Distinguish original resources, faithfully decoded assets, reconstructed animations, inferred behavior and enhanced outputs. Never represent inferred or generated material as original data.

### 7. Background animation is a first-class priority

Investigate animated backgrounds throughout research, indexing, decoding and reconstruction.

Consider animated objects, alternate states, palette cycling, layered effects, environmental costumes, masking, scrolling and script-controlled movement.

Record animation-related relationships even before playback is supported. Static room-image extraction alone does not constitute complete background support.

### 8. Quality before feature expansion

Implement small, testable increments. Verify functionality and preserve regression coverage before expanding features, formats or editions.

### 9. Follow the agreed roadmap

Use the roadmap as the default development sequence. Minor evidence-driven refinements may proceed. Significant architectural, priority or scope changes require a stated justification and user approval.

### 10. Keep architecture modular

Separate archive reading, indexing, decoding, character and background animation reconstruction, enhancement, export and user-interface functionality. The extraction engine must operate independently of the UI.

### 11. Avoid unnecessary complexity

Prefer simple, maintainable implementations. Add dependencies, abstractions and processes only when justified.

### 12. Preserve transparency and reproducibility

Document findings, decisions, tests, limitations, errors and unresolved questions so development can continue reliably between conversations.

### 13. Respect licensing and ownership

Review third-party licenses before incorporating code. Respect ScummVM's GPL obligations. Never commit commercial game archives or extracted copyrighted game assets.

## GitHub and Development Rules

- Treat main as the stable integration branch.
- Use development branches for substantial implementation work.
- Never merge into main without explicit user approval.
- Keep commits focused and traceable to roadmap milestones.
- Run relevant tests before reporting features complete.
- Report failed tests and regressions, including unexpected failures.
- Never conceal errors by modifying tests merely to make them pass.
- Avoid unrelated changes.
- Verify repository operations and report the actual results.
- Check the current repository name, branch and state before changing anything.

## Graphics, Animation and Upscaling Rules

- Faithful native-resolution extraction is mandatory.
- Nearest-neighbor scaling is the default HD export method.
- Prefer established, license-compatible filters for optional enhanced HD output.
- Scale individual assets rather than relying solely on screenshots.
- Preserve palettes, transparency, layering, placement and animation metadata.
- Retain frame order, timing, looping and composition rules where established.
- Treat reconstruction as an investigation, not simply consecutive image exports.
- Account for historical pixel aspect ratios.
- Keep original decoded data independent of enhancements.
- Defer AI enhancement until the core extractor is mature.
- Avoid unnecessary complexity for extreme output resolutions.

## Working Across Conversations

**Windows workspace root:** `F:\Dev\SCUMMBUCKET`. Exactly three top-level directories are allowed, with no new root folders without approval: `SOURCE\ScummBucket` for project code, Git, tests, scripts, research and docs; `TOOLS\ScummVM-P4-Trace` and other third-party utilities for builds/emulators/debuggers; `FIXTURE\GAMES` for untouched original games by title/edition, `FIXTURE\CAPTURES` for real-engine traces, `FIXTURE\REFERENCE` for captures/known-good imagery, `FIXTURE\OUTPUT` for generated assets, and `FIXTURE\REPORTS` for manifests, diagnostics and validation results. Use absolute paths in cross-terminal instructions. Do not relocate, overwrite or delete existing data automatically; migrate by verified non-destructive copy, then separately approve retirement of old paths. System-wide dependencies (e.g. MSYS2 under `C:\msys64`) may remain in place. No copyrighted game assets in Git. These are project defaults, **not** hardcoded CLI limitations for other users.

At the start of substantial work, inspect the latest repository state, roadmap and relevant documentation. Never assume proposed changes from earlier chats were actually implemented.

Work in manageable, testable passes; respect requests for smaller increments.

At meaningful stopping points, report:

- Current roadmap phase and completed work.
- Evidence gathered and tests actually performed.
- Background-animation findings where relevant.
- Errors, failed tests, warnings, limitations and blockers.
- Repository, branch and commit status.
- The next recommended step.

Never make vague claims such as "everything works" without specifying what was tested. Ask questions only when missing decisions materially affect correctness or direction.

## Roadmap Deviation Rules

Deviations are justified when evidence invalidates an assumption, an established solution is demonstrably better, implementation becomes blocked or a meaningful improvement is possible without compromising priorities.

Explain significant changes and trade-offs before proceeding. Do not allow technical experimentation to displace core extraction, animation and export goals.

**Guiding principle:** Extract what exists, reconstruct what can be verified, preserve fidelity, report every failure honestly and document what remains uncertain.
