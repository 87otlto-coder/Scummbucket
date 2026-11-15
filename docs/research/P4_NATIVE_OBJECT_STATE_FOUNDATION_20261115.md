# P4 — Native indexed object-state foundation and mechanism boundaries

**15 November 2026.** Research branch:
research/p5-cross-room-reconstruction (P4 background animation work,
not the roadmap's P5 audio phase).

## Decision

Room12's original-source reconstruction is **232/244 exact indexed
frames**, with **12 deferred missing-draw-record frames** accounting
for 6,184 original indexed-pixel differences. Original recorded
frontbuffers and last observed Guybrush pose support a stable
foreground-persistence hypothesis; no script cause was verified.
Do not suppress errors or retrofit the known capture with a silent
last-pose workaround. The copy-protection/save-session issue is also
deferred. No new Room12 or Room34 ScummVM captures are required for
the next cross-mechanism engineering increment.

## Generic object-state path, now source-only tested

Prior P2 scummbucket/object_images.py decoded OBIM IMxx image states
straight to RGBA PNG plus separate ZP masks. That was useful for still
extraction, but it did not expose original index values or separate
transparency to the P4 native compositor.

Added scummbucket/native_object_state.py:

- decode_indexed_object_state accepts already decoded SCUMM v5
  OBIM resource bytes and explicitly named IMxx state. Preserves
  **original index for every pixel**, including transparent pixels,
  and separately generates binary 0/255 opacity. Transparency depends
  on **strip codec flags plus room TRNS index**. A color equal to TRNS
  remains opaque in a nontransparent strip codec. Reads each state's
  ZPxx planes as independent source masks without inferring how to
  apply them in the game.
- Records original source offsets, decoded pixel SHA-256, opacity
  SHA-256, source strip codecs and mask provenance, with bounded
  structural, dimension, mask and bitstream checks.
- compose_indexed_object draws an explicitly supplied state at a
  caller-provided room-coordinate origin, clipped to an optionally
  supplied viewport. Supports an **explicit caller-provided** full
  room occlusion mask. It never guesses original object location,
  script-selected state, draw order or timing; its output is native
  palette indices, not RGB derived from a screenshot.
- Code is independent of the UI and requires no ScummVM runtime.
  No synthetic state progression is called gameplay-observed.

Added tools/probe_native_object_state.py for read-only, source-hashed
inventory of a chosen object in the original archive. The probe
reports per-state index and opacity hashes, transparent pixel counts,
strip codecs, ZP plane hashes and source offsets, with individual
decode failures preserved. It emits only JSON to stdout. It does not
write game data, PNGs, game archives, local captures or reports.

Synthetic tests:
- tests/test_native_object_state.py checks index/opacity separation,
  opaque pixels using the nominal TRNS index, consistency with the
  existing synthetic RGBA decoder, source clipping, manual occlusion,
  mask decoding, unsupported codecs, malformed state data and
  non-mutating inputs.
- tests/test_probe_native_object_state.py checks complete synthetic
  object-state inventory, preserving successful states beside one
  unsupported state, wrong-room failure, altered re-opened archive
  fingerprint, and invalid selection without opening input.
- Windows source-only CI on the research branch is mandatory. **This
  is NOT private game source smoke validation or runtime fidelity.**

## Optional private original-archive smoke (no debugger needed)

Only after fast-forwarding a clean checkout:

~~~powershell
Set-Location -LiteralPath 'F:\Dev\SCUMMBUCKET\SOURCE\ScummBucket'
$game='F:\Dev\SCUMMBUCKET\FIXTURE\GAMES\MonkeyIsland2_DOS_VGA'
python -B -m tools.probe_native_object_state --game $game --room 7 --object 57
if ($LASTEXITCODE -ne 0) { throw 'Room7 object index probe failed' }
~~~

Room 7 object 57 is a one-state reference with a previously decoded
conditional script-state context. A second exploratory smoke can use
--room 34 --object 358 for 16 archived states, **but no completion
claim is warranted even if all sixteen states decode**. Room34 remains
an explicitly deferred runtime holdout, not the main P4 blocker.

This report-only probe does not need game execution or copy-protection
changes. All original game files stay under FIXTURE, outside Git.

## Mechanism-level acceptance matrix

| Mechanism | Existing evidence | P4 acceptance still missing |
| --- | --- | --- |
| Palette cycling | Room7 archive CYCL; 87-frame private indexed/palette comparison | Generalized observed counter/timing and layer interactions in new rooms |
| Scenery COST actor | Room7 COST142, camera-derived script and original indexed capture | General actor runtime state acquisition beyond instrumented rooms |
| Source object images | Native indexed object-state decoder + synthetic CI; stored multi-state inventories | Real-object original asset smoke, runtime-selected state, location, visibility/order and mask behavior |
| Room occlusion | Room7 ZP01 and Room12 multi-actor partial comparison | Cross-mechanism object/actor interactions and per-scene state |
| Script control | Room34 object358 aligned source opcode starts, 16 stored states | Actual execution/trigger/timing and visual verification; autonomous looping NOT established |
| Scene playback / export | Source package and palette events already modular | Observed state-event schema and synchronized native-indexed composition, then fidelity check |

The next general architecture increment should consume explicit
state-change, actor-draw and palette-change evidence in an
ordered scene-event layer instead of hardcoding more room conditions.
**Do not invent** events where runtime evidence is absent. Keep
extracted source/observed/state-inferred and synthetic claims separate,
and keep the UI out of decoders and validators.

## Non-goals

No SCUMM interpreter, ScummVM replacement, automatic cross-room
support claim, all-edition support, HD scaling, audio work, unrelated
Windows debugging, general AI upscaling or speculative room scripting.
Do not merge draft PR #17 or #8 solely on the basis of source-only CI.
