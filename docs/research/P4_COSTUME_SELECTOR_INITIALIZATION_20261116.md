# P4 — V5 selector initialization source audit (16 November 2026)

## Scope and evidence

Read-only examination of the user-supplied original DOS VGA MI2 `mi2.zip`,
with archive pair fingerprints preserved in
`docs/validation/P4_COSTUME_SELECTOR_INITIALIZATION_20261116.json`.
This is archive-derived and source-backed, **not a runtime execution trace**.

ScummVM v2026.4.0:
- `engines/scumm/costume.cpp`, `ClassicCostumeLoader::costumeDecodeData`
  maps `frame * 4 + direction`, consumes a 16-bit limb mask, observes a
  separate `usemask`, distinguishes `0xFFFF` (clear limb), `0x79`
  (stop) and `0x7A` (resume); normal selectors assign start/end/cursor,
  one-shot high bit, and the direction-specific limb frame identity.
- `engines/scumm/actor.cpp`, `Actor::animateCostume`, advances progress
  and only calls the costume loader according to animation-speed gating.
  A source-level implementation does not itself validate runtime cadence.

## Audit counts (independent empty state per selector)

| Measure | Archive occurrences |
| --- | ---: |
| COST resources | 162 |
| Declared selector slots | 7,193 |
| Unused pointer slots | 3,719 |
| Defined selectors initialized without parser errors | 3,474 |
| Limb-clearing commands | 1,702 |
| Stop entries | 469 |
| Resume entries | 314 |
| One-shot high-bit entries | 1,535 |
| New limb frame assignments from empty states | 6,174 |
| Sound opcodes within selected command ranges | 83 |

Counts are references in stored selector/range data, not unique events
observed in gameplay. Overlapping selector references can repeat commands.
No script timing, active-scene selection or native event behavior is claimed.
The 12 COST 129 **cel pixel** failures remain; selector initialization
is a different decoding step and does not prove those pixels valid.

## Implemented improvement

`scummbucket/classic_animation.initialize` now parses the entire selected
record before applying updates. A truncated later limb cannot leave an
apparently initialized earlier limb when an exception is raised. A new
`AnimationState.limb_frames` array records the selected direction-specific
animation ID for initialized or cleared limbs. Stop/resume modifies only
the stopped mask and preserves prior cursor/frame state, matching the
referenced source control flow.

Synthetic tests cover source frame identity, stop/resume, clear, usemask,
one-shot/old behavior compatibility, malformed later records, unavailable
selectors and bad state width. These are bounded decoding tests, not
independent engine runtime comparisons.

## Next runtime acceptance gates

Instrument actual selector initialization calls, including nonempty initial
states, `usemask` variations, stop/resume and one-shot cases. Compare every
limb's `curpos`, `start`, `end`, `frame` and stopped bits against the
pre- and post-original engine state. Native nonzero-speed and sound events
remain separate. No broad claim for MI1 or other editions.

Work stays on the existing draft PR #18; no original game resources or
private captures committed; Windows-only CI; no workflow artifacts.
