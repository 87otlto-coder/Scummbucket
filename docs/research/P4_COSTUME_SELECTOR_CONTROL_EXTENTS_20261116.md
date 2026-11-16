# P4 COST selector stop/resume extent rule — 16 November 2026

P4 source-only correction: ScummVM v2026.4.0
`engines/scumm/costume.cpp` `ClassicCostumeLoader::costumeDecodeData`
reads each start and extra byte, then checks the command at the *start*
position. For initial `0x79` (stop) or `0x7A` (resume), it toggles the
stopped mask without using the `extra` extent as a cel range. Only normal
initial commands update start/end/cursor and limb-frame fields.

ScummBucket's bounded `initialize` and source-only `audit_costume_selectors`
previously required the end of *every* initial command's extent to be within
the COST resource, including stop/resume records. That imposed a condition
not present in the referenced engine branch and could reject otherwise
valid state controls. The code now verifies that the start command is
addressable first; it validates end ranges only for drawable/normal
initializers. Truncated initial command addresses still fail closed.

Synthetic tests use stop and resume records with an unused 127-byte extent
that would run beyond the fixture data, and verify that neither the cursor
nor previous limb frame is overwritten. The selector corpus auditor likewise
recognizes the two controls without reporting drawable ranges.

Archive-wide prior counts remain source observations, not runtime behavior.
This correction is backed by pinned source control flow and synthetic
regression; it has not been independently verified against an original
native stop/resume execution trace. No copyrighted resources committed.
