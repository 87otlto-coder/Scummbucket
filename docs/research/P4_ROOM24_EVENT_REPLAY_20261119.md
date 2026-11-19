# Room 24 event-driven native comparison

This checkpoint uses PR #21 at `f6126365db613cce717cfc8f9ff94824dc82540b`. The requested separate architecture convergence branch and its GitHub handoff could not be located. This work reuses the verified Room 24 rejection rule, palette hook mapping, native comparator and independent Z-plane compositor.

The pinned debugger-equivalent capture has a scoped RNG call stream. Its entry-time draw occurs before the room-entry marker and leaves script local 0 at state 3. The verifier takes that value as an explicit seed. Subsequent candidates come from observed RNG results plus one. LSCR 200 retries equal candidates, draws on acceptance and yields. The verifier retains its selected state through rejections and checks each logged previous operand against it. The frame association uses consecutive accepts in observed order, with one accept per sampled native frame. This is a bounded capture contract rather than a general script scheduler.

Original archives supply the background, the three image and mask states, and the CDHD position of object 246. The supported draw stack is background, one visible room object and the captured actor draw. The capture's object rows check the predicted visible configuration and placement. The order of multiple visible objects is outside this fixture's verified scope. Palette initialization uses the archive CLUT and observed hook operands. Timer deltas and the actor draw record remain runtime inputs. Camera geometry is fixed and checked against the capture. Unsupported multi-layer ordering, queued special draws and incremental front-buffer restoration require separate implementation and verification.

| Path | Frames | Packed mask bytes | Mask bit mismatches | Indexed back / front mismatches | Palette / counter mismatch frames |
|---|---:|---:|---:|---:|---:|
| Room 24 RNG replay | 64 | 737,280 | 0 | 0 / 0 | 0 / 0 |
| Room 24 snapshot control | 64 | 737,280 | 0 | 0 / 0 | 0 / 0 |
| Room 35 Bit92 clear control | 32 | 368,640 | 0 | 0 / 0 | 0 / 0 |
| Room 35 Bit92 set control | 32 | 368,640 | 0 | 0 / 0 | 0 / 0 |
| Room 7 control | 87 | 1,002,240 | 0 | 0 / 0 | 0 / unsampled |

Room 24 replay matched 64 object states and positions from 95 post-entry RNG calls, including 31 rejected repeats. Room 7 retained 4,008,960 checked back-buffer indices and 778 expected mismatches with ZP01 disabled. The four unchanged control paths total 215 frames and 2,476,800 packed mask bytes.

The opt-in private test reverses and corrupts object rows, flips a reference front pixel and a ZP01 bit, and makes the snapshot depth predictor raise if called. Predicted indexed hashes and events remain identical. The altered state, pixel and mask bit appear as comparison mismatches. The Windows local suite ran 423 tests with 16 skipped and zero failures, including the opt-in test. No new native capture was made.

## Windows reproduction

```powershell
Set-Location 'F:\Dev\SCUMMBUCKET\SOURCE\ScummBucket'
$fixture = 'F:\Dev\SCUMMBUCKET\FIXTURE'
$capture = Join-Path $fixture 'CAPTURES\Room24-hook6b-ed69bee5d8f745ab98a84a5f13693ad2'
$report = Join-Path $fixture "REPORTS\Room24-Events-$([guid]::NewGuid())"
python -B -m tools.verify_independent_zplanes $fixture $capture $report --room 24 --room24-entry-script-local 3
$env:SCUMMBUCKET_ROOM24_GAME = Join-Path $fixture 'GAMES\MonkeyIsland2_DOS_VGA'
$env:SCUMMBUCKET_ROOM24_CAPTURE = $capture
python -B -m unittest discover -s tests -p test_room24_rng_replay.py
```

The actual run used the canonical read-only game files and Room 7 fixture with the writable mirror's Room 24 and Room 35 captures. The Room 24 report SHA-256 was `806044ac180b5f2fe89be75c04f7b422ee7b98fd89c9a4383d457fb9fa1bf847`. The next native milestone needs ordered mutation and redraw evidence for Room 35, including actor retention, then the Room 7 viewport and mask regression through the shared event path.
