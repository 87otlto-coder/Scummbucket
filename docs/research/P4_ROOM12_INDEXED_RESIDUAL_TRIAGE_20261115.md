# P4 Room 12 — first independent indexed-compositor result

15 November 2026. Original Monkey Island 2 DOS VGA. Captured ordinary
Room 7 -> Room 12 -> Room 7 route, private capture ID
cross-room-e4deddf716114bc9907d5d99e1b85232.

**Status: PARTIAL_INDEXED_RECONSTRUCTION — NOT ACCEPTED.**

## Operator-reported, full 244-frame comparison

The first independent source-based compositor compared all Room 12 engine
frames against the original private indexed front buffers, not against
approximated RGB or merely a flattened background.

The original game archives reported:
- MONKEY2.000 SHA-256: cde7aa8980317e3a750fbb3b49884cdddaf1ff3d4231a0c840b22cceed9033f1.
- MONKEY2.001 SHA-256: ad045372e0d49626503bb50fca29a687ec8e01ef75d9b8bca702a366d143819e.
- Source Room 12 chunk SHA-256: 75e48923aeb8e97bf4826135338588e2c84f43adce554aef194aae2e4943e553.

The user supplied console output (the full per-frame comparison JSON is
still retained privately on F: and has **not** been independently reviewed):

| Measurement | Recorded aggregate |
| --- | ---: |
| Room 12 engine frames | 244 |
| Indexed-pixel observations (320x144 each) | 11,243,520 |
| Reconstructed-versus-engine indexed mismatches | **6,184** |
| Exact matching pixel observations | 11,237,336 (99.9449994%) |
| Mismatches without depth masks | 65,527 |
| Error reduction with masks | 59,343 (90.56%) |
| Pixels changed by applying masks | 59,343 |
| Source-versus-recorded background mismatches | **0** |

The exact equality of mask-modified pixels and error reduction implies all
59,343 mask-induced changes were corrections for the current recorded
comparison. This is a strong negative control **for this captured route**,
not general support for every depth-plane interaction.

The residual mismatch rate is approximately 0.055%, or 25.34 indexed
pixel observations per frame on average. **Do not promote this to a
99.945% animation fidelity claim.** Most observations are static room
background; the source actor animation, costume cels and dynamic object
composition remain unaccepted until all frames are exact.

The user generated the original non-overwriting result under:

FIXTURE/REPORTS/P5/room12-indexed-c80aa6e1bdf14405a18110ad79ea32ec

The PowerShell stage correctly returned an error after writing the
partial report. This is expected and must not be converted to success.

## Next: local read-only residual clustering, not another recording

The exact failure patterns are not recoverable from totals alone. New
tools/triage_room12_residuals.py joins the old comparison JSON with
the independently recovered indexed actor report, validates their
capture identity, indexed frame IDs, ticks, draw order, front SHA-256,
sample totals and all four aggregate counters.

It reports: count of exact/partial frames, worst frames, contiguous error
runs, error distribution grouped by original draw order, actual Guybrush
presence, and observed actor 1/7/8 animation cursor vectors. It
does **not** rewrite any F: data, infer a faulty actor, perform new image
rendering or claim renewed independent pixel verification.

Read-only Windows PowerShell 5.1 procedure, after ensuring clean P5
research checkout and updating from GitHub:

~~~powershell
Set-Location -LiteralPath 'F:\Dev\SCUMMBUCKET\SOURCE\ScummBucket'
$fx = 'F:\Dev\SCUMMBUCKET\FIXTURE'
$comparison = Join-Path $fx 'REPORTS\P5\room12-indexed-c80aa6e1bdf14405a18110ad79ea32ec\room12-indexed-compare.json'
$indexed = Join-Path $fx 'REPORTS\Room7\cross-room-e4deddf716114bc9907d5d99e1b85232\cross-room-indexed.json'

if (!(Test-Path -LiteralPath $comparison -PathType Leaf)) { throw "Missing original comparison: $comparison" }
if (!(Test-Path -LiteralPath $indexed -PathType Leaf)) { throw "Missing recovered indexed metadata: $indexed" }

python -B -m tools.triage_room12_residuals --comparison $comparison --indexed $indexed
if ($LASTEXITCODE -ne 0) { throw 'Metadata triage or provenance failed' }
~~~

Send the printed JSON or the original complete room12-indexed-compare.json.
If the residuals cluster around actor 7, actor 8, or specific cursor
transitions, isolate an original COST cel or render phase with bounded
tests. If they cluster near room geometry or edge clipping, inspect
native pixel placement and masks. Do not fit sprite coordinates or
paint over mismatches without source or engine evidence.

Room 34's state-selection holdout remains gated on an accepted Room 12
reconstruction. Public Git and CI must never contain original archives,
native indexed frames, actor capture binaries, or image exports.
