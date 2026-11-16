# P4 — original MI2 COST control target selection (16 November 2026)

**Purpose:** maximize information returned by a future native Windows
capture. This is a source-only ranking, *not* a claim that the listed
costumes execute in their archive storage rooms.

## Archive method

Read-only scan of the original DOS VGA MI2 index DCOS entries and indexed
COST selector records, validated against source fingerprints in
`docs/validation/P4_COSTUME_SELECTOR_INITIALIZATION_20261116.json`.

Each record count is a **reference occurrence in stored data**. Different
selectors can share an underlying command, and no scripted runtime usage
or timing has been observed from these counts.

| COST ID | Storage room (not execution site) | Format | Selectors | Stop | Resume | One-shot | Sound opcodes in ranges | Why inspect |
|---|---:|---|---:|---:|---:|---:|---:|---|
| 1 | 4 | 16 colors | 122 | 34 | 5 | 56 | 2 | Existing Room 7 actor 1 capture provenance; good starting continuity |
| 8 | 30 | 32 colors | 86 | 18 | 24 | 12 | 30 | High control variety and largest stored sound-reference count |
| 24 | 50 | 16 colors | 59 | 38 | 16 | 14 | 0 | Highest stored stop count |
| 158 | 39 | 16 colors | 92 | 0 | 0 | 94 | 0 | One-shot-heavy holdout |
| 142 | 7 | 32 colors | 15 | 0 | 0 | 0 | 0 | Previously observed scenery actor 11; low-control contrast |

The source audit found 83 sound-command range references across eight
COST resources. These references are not observed sound events and are
not unique command bytes. The 32-color COST 8 is an attractive control
case but no runtime fixture is established here.

## Minimum native evidence gate

1. Before running ScummVM, independently identify *actual runtime*
   actor/costume mapping and script-triggered selectors for the candidate.
   The DCOS storage-room number alone is insufficient.
2. Retain exact game pair/source hashes, ScummVM source/binary digest,
   savegame digest, config, engine tick and raw capture-record hashes.
   Use a new non-overwriting fixture destination.
3. Instrument the existing selector initialization method at entry and
   exit without modifying state, extra animation ticks or forcing redraw.
   Record frame, facing, computed animation index, usemask, all 16
   cursor/start/end/frame fields and stopped mask before/after. Keep
   draw-operation and pre-redraw-state channels separate.
4. Compare observed state to `classic_animation.initialize` for each
   actual call, preserving every mismatch and every absent channel.
   Counter/audio/speed events require independent capture, not inference.
5. A new room accepted for source/pixel fidelity requires independent
   original native indexed fronts and masks; selector-state comparison
   alone is *not* full scene acceptance.

Original MI2 resources, saves, source snapshots, instrumented binaries
and rendered pixels remain outside Git. Windows-only CI and no uploaded
workflow artifacts. Do not merge PR #18 automatically. Room 12 residuals
and Room 34 runtime remain deferred.
