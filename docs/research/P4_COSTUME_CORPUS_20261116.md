# P4 COST selector corpus — archive-only research checkpoint

16 November 2026. Research branch research/p4-observed-event-replay,
draft PR #18. Roadmap remains P4 background animation.

## Real MI2 DOS VGA original archive, read-only investigation

A temporary independent Python structural audit read the supplied mi2.zip,
decoded MONKEY2.000/001 with XOR 0x69 and resolved 162 original DCOS-linked
COST chunks. The same decoder principles have been turned into the reusable
source-only audit module and CLI below. The committed CLI still needs a
separate run against the private original archives to claim that *it*
reproduces these exact aggregate numbers.

Original resource SHA-256:
- MONKEY2.000: cde7aa8980317e3a750fbb3b49884cdddaf1ff3d4231a0c840b22cceed9033f1
- MONKEY2.001: ad045372e0d49626503bb50fca29a687ec8e01ef75d9b8bca702a366d143819e

| Structural source-only check | Result |
| --- | ---: |
| Linked costumes | 162 |
| Format 0x58 / 16-color | 122 |
| Format 0x59 / 32-color | 40 |
| Declared animation selector slots | 7,193 |
| Unused/zero-pointer slots | 3,719 |
| Defined pointer slots | 3,474 |
| Consistent defined selectors | 3,462 |
| Failed defined selectors | 12 |
| Selectors with drawable limb ranges | 3,235 |
| Referenced cel positions inspected | 24,930 |
| Distinct costume/limb/position references | 13,016 |
| Zero-area referenced cel positions | 5 |
| Failures outside COST 129 | 0 |

All 12 remaining selector failures are in COST 129, selectors 4–15, room 91,
with a shared referenced cel failing bounded RLE decode. The cel header
specifies 2x2 pixels, but its two remaining RLE bytes supply only three
pixels. The source COST has 169 bytes and SHA-256
6ba5fb15dd825567e521fb55c079dcb27ea88c3930fed3fd23cc13404d6f452b.
This is evidence of a truncated cel *under the current bounded decoder*,
not proof that the original DOS engine could never draw it or that the
remaining pixel should be synthesized. **Do not pad or conceal this failure.**

Five zero-area references are found in COST 50 (two) and COST 61 (three).
A separate zero-area correction allows valid empty cel movement metadata,
and synthetic tests check following-limb position and source indices.

## Reproducible source-only inventory

scummbucket/costume_corpus.py audits original indexed selector pointer tables,
limb ranges and their referenced cel positions. It preserves failures for
individual selectors without silently skipping neighboring references.
tools/audit_costume_corpus.py verifies the input archive fingerprint after
inspecting it and emits only JSON metadata and failure locations. It never
renders images, interprets SCUMM scripts or modifies original game data.
An optional --output requires a brand-new report file, with exclusive creation.

On the operator's Windows machine, create a new unique report name:

~~~powershell
Set-Location -LiteralPath 'F:\Dev\SCUMMBUCKET\SOURCE\ScummBucket'
$game = 'F:\Dev\SCUMMBUCKET\FIXTURE\GAMES\MonkeyIsland2_DOS_VGA'
$out = 'F:\Dev\SCUMMBUCKET\FIXTURE\REPORTS\P4\costume-corpus-NEW.json'
python -B -m tools.audit_costume_corpus --game $game --output $out
# A PARTIAL result (12 known failures) must exit 2 and retain the JSON.
~~~

The source-only aggregate counts are not live animation selections, timings,
draw order or proof of pixel-exact runtime fidelity. Selectors with zero
pointers are tracked separately rather than counted as valid animations.
Synthetic tests prove parser/report/partial-failure contracts, not original
source correctness. All proprietary resources and output report bodies stay
outside Git. Windows-only GitHub CI uploads no artifacts.

## Next evidence gates

1. Run the *committed* tool on original MI2 to independently reproduce the
   temporary audit's aggregate counts and retained COST 129 failures.
2. Inspect COST 129 source/render path for unusual intentional command or
   encoding semantics. Never guess an extra decoded pixel.
3. Classify script-selected/actual runtime animation coverage separately
   from stored selector catalog; nonzero cadence and event control remain open.
4. Do not reopen Room 12 or Room 34 native runtime investigations here.

## Follow-up: independent replay and root-cause grouping

The uploaded original MI2 resource pair was independently scanned again
read-only. The original source SHA-256 values remained unchanged. The same
7,193-slot classification reproduced: 3,719 unused, 3,462 consistent defined,
12 failed defined, all 12 in COST 129.

The 12 failing selectors (4 through 15) resolve to the same costume command
index 0, limb 0, and cel offset 155 within COST 129. The cel header declares
width 2, height 2, but its only two remaining encoded bytes are `12 21`,
which encode 2 + 1 = 3 local-palette slots under the existing v5 RLE rules.
The next byte in the resource file belongs to the next `CHAR` chunk. The
original COST chunk boundary must not be crossed to fill the fourth pixel.

The corpus audit now includes `failure_groups` and
`distinct_failed_reference_groups` to distinguish selector failures
from distinct failing limb/command references. This is still *not* a count of
unique physical cel resources for arbitrary malformed pointer tables.
Pre-reference parse failures stay as ungrouped singleton records; source
reference aggregation never suppresses per-selector diagnostics.

The independent local replay was a small source-only harness matching the
repository's selector/cel rules. The committed CLI remains to be run directly
on the operator's original archive; until then, do not claim CLI-original
acceptance. No native engine capture was added, and no automatic correction
to COST 129 was made.
