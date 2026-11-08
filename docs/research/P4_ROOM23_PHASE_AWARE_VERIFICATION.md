# P4 — Phase-aware Room 23 engine palette research path

**Research date:** 2026-11-08. **Status:** Implementation committed; local pure comparator was exercised against the user's uploaded original DOS VGA `MONKEY2.001` and 180-sample live log, plus synthetic corruption tests. The integration CLI and Windows PowerShell runner have **not yet been executed on the user's machine** after this commit.

The original strict `import-scummvm-palette-log` and `verify-palette-trace` remain **unchanged**. They are deliberately fail-closed for incomplete logs and CLUT-baseline differences. Phase-aware research is explicitly a **separate** command, not a bypass of strict evidence requirements.

## Use existing first live capture (Windows PowerShell)

The first capture was `room23-normal-20261108-215059-863.raw.log` from Room 23, original DOS VGA MI2. It is incomplete: there are 180 valid SAMPLE records but no END. The phase-aware command reads this raw log **without modifying or sealing it** and writes a separate report with exclusive creation.

~~~powershell
cd "C:\Users\87otl\ScummBucket"
git pull --ff-only origin research/p4-engine-palette-trace

python -m unittest discover -s tests -p "test_room23_capture_research.py" -v

python -m scummbucket analyze-room23-palette-log "D:\old\mi2" `
    --raw-log "C:\Users\87otl\ScummBucket\exports\room23-normal-20261108-215059-863.raw.log" `
    --output "C:\Users\87otl\ScummBucket\reports\room23-first-live-phase-analysis.json" `
    --json
~~~

If the file is in a different directory, supply its actual path. **An incomplete but exactly modeled capture returns exit code 2 by design** and outputs `status: incomplete`, `model_comparison_status: matched`. This is not a failure to parse the 180 samples; it prevents falsely claiming the recording completed. Do not run into an already existing `--output` filename.

Expected on the user's supplied original log (SHA-256 `ac8163b6305a35680764fd157694ea85a10de63949be20349dae7cbc943100ee`) and pinned `MONKEY2.001` resource (SHA-256 `ad045372e0d49626503bb50fca29a687ec8e01ef75d9b8bca702a366d143819e`):

| Evidence | Result |
|---|---|
| Capture completeness | Incomplete, no END |
| Actual samples | 180, all timer pairs 6/6 |
| Cycling indices | 176–191 (16 entries) |
| Observed non-cycle overrides vs source CLUT | 1, 2, 3, 6 |
| Clock discontinuity | 27,086 ms between samples 80 and 81 |
| Segment 1 | first model position 60; calibrate 3, held out 77/77 |
| Segment 2 | first model position 1; calibrate 5, held out 95/95 |
| Model agreement | 180/180 cycled palettes and 180/180 complete RGB palettes *with measured non-cycle baseline retained* |
| Total held-out matched | 172/172 |

The updated `run_scummvm_palette_capture.ps1` attempts this forensic report automatically on all new captures **before** the ordinary strict importer checks. If a log lacks END, the PowerShell helper still exits nonzero and preserves the raw evidence. The phase-aware report uses a separate `*.phase-research.json` filename.

## Method and safeguards

1. Require the exact pinned original DOS VGA `MONKEY2.001` SHA-256. Archive inventory, room indexing and CLUT decoding use the existing extraction engine.
2. Parse raw BEGIN/SAMPLE/optional END records with original syntax, contiguous numbering, monotonic millisecond timestamps, 768-byte lower-case RGB hex, maximum 256 samples and 1-MB file size limit. **A missing END stays missing**.
3. Detect clock discontinuities based on jumps larger than max(1000 ms, 5× median sample interval); this identifies candidate segment boundaries, **not** a proven cycle-counter reset.
4. Within each segment, search a bounded range of model-equivalent initial positions. Select a phase *only* if a unique candidate is identified using a short calibration prefix (three to eight samples). Never tune a phase using held-out samples.
5. Replay every later actual timer pair via `max(VAR_TIMER, VAR_TIMER_NEXT)` and the existing `advance_palette()` model. Report the first mismatching palette indices and their sample sequence.
6. For full 256-entry palette comparison, keep **noncycling** entries from the observed BEGIN palette and model **cycling** entries from the original CLUT. This exposes noncycle changes later in the log, but does not explain the four original runtime overrides.
7. Keep independent status fields for raw capture completeness, model agreement, first mismatch, calibration count, held-out count, clock gaps and provenance limitations. Raw execution/binary authenticity is not claimed.

The 27-second gap correlates with all 16 cycling entries changing and the sample immediately afterward matching the source CLUT's cycling region. This supports a **possible palette reset**, but its mechanism (room reentry, explicit palette initialization or something else) remains unknown.

## Acceptance and outstanding work

- **Achieved:** Pure source-cycle model matches 180 user-captured palette states after short phase calibration across the clock gap, including 172 held-out states. Standalone local regression tests deliberately corrupt one cycled and one noncycled color, which both trigger a mismatch.
- **Not achieved:** An END-complete authenticatable capture, an upstream runtime source attestation, final display-frame/presentation timing, actors, masked objects or comprehensive room animation.
- **Next:** Obtain an uninterrupted normal room capture with `SBP4|END|256|limit`; compare it using both paths, with the strict baseline mismatch reported explicitly. Then capture the 60-unit scheduler stress scenario and inspect true missed-rotation behavior.

**Source files:** [phase analyzer](../../scummbucket/room23_capture_research.py), [synthetic regression tests](../../tests/test_room23_capture_research.py), [normal live evidence report](P4_ROOM23_FIRST_LIVE_PALETTE_TRACE.md), [Windows capture runbook](P4_WINDOWS_TRACE_RUNBOOK.md).
