# P4 — Room 12 absent-draw actor forensic checkpoint

Date: 15 November 2026
Original DOS VGA Monkey Island 2. Research branch:
research/p5-cross-room-reconstruction (P4 scene animation, not P5 audio).
**Status: 232 exact indexed frames, 12 non-exact; full-scene not accepted.**

## What the actual first comparison established

The existing private 244-frame Room 12 indexed comparison has:
- 11,243,520 pixel observations; 6,184 mismatches.
- Exact indexed reconstruction in 232 of 244 frames.
- Source static background mismatches: 0 in every frame.
- Unmasked foreground errors: 65,527; source mask corrections:
  59,343; masked remaining errors: 6,184.
- Every one of the 232 frames with an actor-1 (Guybrush) draw record is
  exactly pixel-equal to the original engine front buffer.
- Every one of the 12 frames **without** actor-1 draw records has mismatches.

Problem tick groupings (each part is 320x144):
- 213–214: 550 errors each (1,100), bbox [33,50,56,94].
- 217–220: 344 errors each (1,376), bbox [43,51,62,90].
- 223–228: 618 errors each (3,708), bbox [29,49,52,94].

These results are more informative than the overall approximately
99.945% pixel-observation agreement. Most image pixels are unchanging
background. The failure is **exclusively tied to absent actor-1 draw
records in this capture**, not yet causally proven to be Guybrush pixels.

Actor 7 (COST 20) and actor 8 (COST 41) are both recorded in all 244
interior frames and use recurring animation cursor states seen in
fully exact frames. This reduces the plausibility of a generic COST20/
COST41 decoding defect, but does not rule out local overlap, buffering,
object layers, or draw-phase instrumentation omissions.

The recorder's actor hook emits draw_actor only for
!hitTestMode and actor room == engine current room, in rooms 7/12.
It is therefore possible for an actor-related pixel change to exist
without a corresponding draw_actor record. This is a *hypothesis*, not
evidence that the game actually drew a missing actor.

## New purely diagnostic read-only code

tools/diagnose_room12_missing_actor.py:
- Reopens only the historical original game archives and private original
  engine indexed frames, checking raw frame, original front and source
  background SHA-256 against previously verified metadata.
- Recomputes the source compositor for each of the 12 partial frames
  and demands exact equality of its hash, mismatch count and bounding
  box with the saved prior comparison. Does not introduce new baseline
  definitions or overwrite the original partial result.
- Categorizes original differences into observed foreground absent
  from the candidate, candidate-only foreground, or different
  foreground-index colours.
- Compares only the residual pixel positions with the neighboring
  original captured framebuffers to test persistence/caching.
- Inserts Guybrush's **nearest preceding and following observed**
  recorded draw poses into temporary in-memory candidate renders at
  three draw-order locations, checking whether any actually reduce
  the 6,184 mismatches. These trials are explicitly counterfactual:
  they do NOT amend the original timeline, assert a character pose,
  or declare a reconstruction pass.
- Keeps the original indexed capture and previous comparison read-only.
  Optional saved JSON must be exclusively created under FIXTURE/REPORTS/P5.
  It does not record new gameplay, modify ScummVM, or draw object images.

Synthetic unit tests isolate a missing actor pixel, a genuinely unrelated
object-like pixel, tampered frame/metadata hashes and misleading extra
draw records. Original private raw frame tests remain a distinct acceptance
gate and must be executed on the operator's F: disk.

## Safe operator invocation: Windows PowerShell 5.1

In the original clean repository checkout, after fast-forwarding the
research branch (do not switch branches or overwrite dirty files):

~~~powershell
$ErrorActionPreference = 'Stop'
Set-Location -LiteralPath 'F:\Dev\SCUMMBUCKET\SOURCE\ScummBucket'

$branch = 'research/p5-cross-room-reconstruction'
if ((git branch --show-current).Trim() -ne $branch) { throw 'Unexpected branch' }
if (git status --porcelain) { throw 'Dirty working tree; stop safely' }
git fetch origin $branch
if ($LASTEXITCODE -ne 0) { throw 'Fetch failed' }
git merge --ff-only "origin/$branch"
if ($LASTEXITCODE -ne 0) { throw 'Fast-forward failed' }

$fx = 'F:\Dev\SCUMMBUCKET\FIXTURE'
$game = Join-Path $fx 'GAMES\MonkeyIsland2_DOS_VGA'
$capture = Join-Path $fx 'CAPTURES\Room7\cross-room-e4deddf716114bc9907d5d99e1b85232'
$indexed = Join-Path $fx 'REPORTS\Room7\cross-room-e4deddf716114bc9907d5d99e1b85232\cross-room-indexed.json'
$comparison = Join-Path $fx 'REPORTS\P5\room12-indexed-c80aa6e1bdf14405a18110ad79ea32ec\room12-indexed-compare.json'
$output = Join-Path $fx ('REPORTS\P5\room12-absent-actor-' + [guid]::NewGuid().ToString('N') + '.json')

python -B -m tools.diagnose_room12_missing_actor --game $game --capture $capture --comparison $comparison --indexed $indexed --output $output
if ($LASTEXITCODE -ne 0) { throw 'Original indexed actor-absence forensic check failed' }
Write-Host "Private forensic JSON: $output"
~~~

Upload the new JSON or paste its summary. Report the counterfactual
error totals and classification; do not patch actor timing merely
because a counterfactual candidate improves errors. If source-state
evidence independently establishes a persistent actor draw or an
unlogged object layer, implement that separately and reverify all
244 original frames, including the 232 already exact. Room34 remains
blocked until this gate has verified full indexed composition.

Neither copyrighted game resources nor private actor captures belong
in Git/CI/public artifacts. PR #8 and draft PR #17 remain unmerged.
