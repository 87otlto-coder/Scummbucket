# Independent Z-plane reconstruction for MI2 DOS VGA

## Result

The predictor reads original RMIM/IM00 and OBIM/IMxx resources and explicit scene state. The captured packed mask bytes enter only the comparator. The existing Room 24, Room 35 and Room 7 scene comparators use the predicted masks for actor clipping on this path. Their original controls remain available.

| Capture | Frames | Mask bytes | Mask bits | Byte / bit mismatches | Indexed back / front mismatches |
|---|---:|---:|---:|---:|---:|
| Room 24, corrected hook 6 / RNG probe | 64 | 737,280 | 5,898,240 | 0 / 0 | 0 / 0 |
| Room 35, effective Bit92 clear | 32 | 368,640 | 2,949,120 | 0 / 0 | 0 / 0 |
| Room 35, effective Bit92 set | 32 | 368,640 | 2,949,120 | 0 / 0 | 0 / 0 |
| Room 7, pinned camera sweep | 87 | 1,002,240 | 8,017,920 | 0 / 0 | 0 / 0 |
| Total | 215 | 2,476,800 | 19,814,400 | 0 / 0 | 0 / 0 |

Each frame contributed two 320×144 packed planes, 5,760 bytes apiece. All captured planes were supported in these runs. Final palettes matched throughout and the sampled counters in Rooms 24 and 35 matched. Room 7 has no counter fields in the pinned packets. Disabling ZP01 in the Room 7 replay reproduced the expected **778** indexed mismatches. Its pinned back-buffer check covered **4,008,960** pixels.

With object layers disabled, Room 24's background ZP01 differs by 13,952 bytes and 93,344 bits across its 64 frames. Room 24's reconstructed ZP01 produced three distinct hashes, one for each observed state of object 246. Room 35's background-only differences total 320 bytes / 1,376 bits with Bit92 clear and 512 bytes / 2,912 bits with Bit92 set. Room 35 produced one ZP01 hash per branch despite the clear branch cycling across all eight object 364 states. The set branch draws the masks for visible objects 361, 362 and 365. Room 7's scrolling crop uses the authored background plane.

## Source, representation and supported semantics

The indexed background decoder now exposes optional decoded masks, chunk offsets, lengths and strip tables. The RMIH count excludes reserved plane zero. Original DOS VGA background and object chunks in these fixtures use a little-endian 16-bit offset per strip and the existing mask RLE decoder. Zero offsets denote missing strips. Packed output stores one byte per eight horizontal pixels, MSB left, in scanline order. A set bit occludes a clipped actor. The reported view width is 40 strips, while the Room 7 world width is 98 strips.

The shared packed compositor starts with the original background and replays object layers in explicit back-to-front order. The installed ScummVM renderer uses reverse local-slot traversal for ordinary DOS v5 room objects. A present opaque-codec strip replaces its mask byte. A transparency-aware strip with mask merge enabled ORs its bits. A missing strip clears under replacement and preserves under OR. An absent object plane leaves existing plane bytes unchanged. Replaying a fresh baseline restores areas occupied by removed or moved objects in the supported redraw model. Actual animated object strips in these captures use replacement. OR, sparse, clipping, and restoration behavior have synthetic coverage. The reference for engine semantics is the installed ScummVM 2026.4.0 snapshot, specifically Gdi::decodeMask in gfx.cpp and ScummEngine::drawRoomObjects and v5 object setup in object.cpp. No upstream renderer body was copied.

The comparison records archive fingerprints, source chunk offsets, strip layouts, per-plane hashes, source module hashes, capture-packet hashes, explicit object states and positions, and byte/bit counts. When a mask differs, it records the first byte, MSB-first bit, viewport pixel and values. Unsupported geometry or plane counts fail explicitly. Original manifest and comparison paths remain available.

## Evidence boundaries

- **Archive decoded:** masks, authored geometry, indexed art and costume resources.
- **Engine source backed:** strip semantics, layer ordering, native packing and viewport cropping.
- **Runtime observed:** selected object states, room-slot order, applicable object positions, camera, actor pose and depth, timing, and prior palette inputs. Room 35 retains the previously reconstructed pose during its established idle redraw case.
- **Pixel verified:** both reconstructed mask planes and both indexed buffers for the 215 frames listed above.
- **Synthetic:** OR, sparse offsets, restoration and clipping controls that were not exercised by every runtime fixture.
- **Unsupported outside this envelope:** non-strip-aligned placement/viewports, alternate engine mask layouts, special all-plane draws and arbitrary incremental draw-queue histories. The three sampled debugger-equivalent entries do not establish natural gameplay entry or archive-only scheduling.

## Windows reproduction

Use an existing source-derived Room 35 export and the private captures named below. Run from the branch's checkout. Choose a fresh report directory each time.

```powershell
$root = 'F:\Dev\SCUMMBUCKET'
Set-Location "$root\SOURCE\ScummBucket"
$f = "$root\FIXTURE"
$c = "$f\CAPTURES"
$o = "$f\REPORTS"
$waterfall = 'ABSOLUTE_PATH_TO_EXISTING_ROOM35_SOURCE_EXPORT'
$cases = @(
    @{ Room = 24; Capture = "$c\Room24-hook6b-ed69bee5d8f745ab98a84a5f13693ad2" },
    @{ Room = 35; Capture = "$c\Room35-c-clear-e3b0ac785cc4400bb79dcf4b0aa9852b" },
    @{ Room = 35; Capture = "$c\Room35-c-set-8ab85a61cca349e4b9a5d5769df09052" },
    @{ Room = 7; Capture = "$c\Room7\sweep-20261110-a" }
)
foreach ($case in $cases) {
    $report = "$o\ZPlane-$($case.Room)-$([guid]::NewGuid())"
    $options = @()
    if ($case.Room -eq 35) { $options = @('--waterfall-export', $waterfall) }
    python -B -m tools.verify_independent_zplanes $f $case.Capture $report --room $case.Room @options
    if ($LASTEXITCODE) { throw "Verification failed for $($case.Capture)" }
}
python -B -m unittest discover -s tests
```

The actual runs used the canonical read-only archives and pinned Room 7 sweep, plus the Room 24/35 captures in the writable mirrored FIXTURE tree. The Windows sandbox denied `git -C F:\Dev\SCUMMBUCKET\SOURCE\ScummBucket`. Local implementation and tests used the isolated P4 validation snapshot. Full canonical wrapper acceptance remains blocked at that checkout check. No private binary captures or assets are committed. The existing source-lineage review remains open and no PR was merged.
