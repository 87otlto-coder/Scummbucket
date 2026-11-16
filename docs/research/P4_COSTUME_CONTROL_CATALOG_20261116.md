# P4 — Reusable selector control reference inventory

16 November 2026, research branch `research/p4-observed-event-replay`.

The COST source-only corpus audit now counts selector initialization controls
and sound/animation-counter opcodes *within declared selected command ranges*.
The CLI aggregates seven metadata fields per costume, with zero-footprint
format changes to original data:

- `limb_clear_entries` for `0xFFFF` cursor clears.
- `initial_stop_entries` and `initial_resume_entries` for initial
  `0x79` / `0x7A` state controls, with ignored extents.
- `initialized_limb_ranges` and `one_shot_flags`.
- `sound_command_references` for `0x78`, and
  `counter_command_references` for `0x7C` in recorded ranges.

These are occurrence counts in stored data; shared selector ranges can
double-count an underlying command. Counts observed before a later pixel
decode failure are still retained, while selector failures remain visible
separately. The native engine's actual control-event execution, nonzero
cadence and timing are **not** validated by this report.

Independent archive scan of the original MI2 DOS VGA source (the separately
committed source hashes apply) observed 1,702 clear records, 469 stop,
314 resume, 4,472 normal initialization ranges, 1,535 one-shot high bits,
83 sound command range references and no `0x7C` command references.
The reusable committed CLI must independently reproduce these numbers
when run against the original private archive; synthetic CI alone does not
establish its source corpus acceptance.

Synthetic tests cover distinct control categories, non-drawable stop/resume
extents, zero-area movement and partial-failure diagnostics. No binaries,
game pixels, gameplay captures or original resource bytes committed.
