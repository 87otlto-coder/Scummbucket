# Room 7 costume 142 archive validation

Verified using ClassicCostume at a177070 and the two preflight-pinned original DOS archives. DCOS[142] links to room 7, relative offset 192120, MONKEY2.001 decoded offset 584460, length 1509, SHA-256 7ef3e98fb9cd824782b0cf7e93d9e7f3c059354557ec7e08d714eda9425a7c5f.

The only non-null animation pointers (6 and 14) select limb 0, sequence start 0, last relative position 0 and command 0. Both decode the same cel at COST offset 119. Dimensions 89 × 51, relative position (−47,−50), move (0,0). Column-major 32-color RLE decodes 4539 slots, including 2314 transparent slot-zero pixels. Slot zero maps to palette index 5 but must be skipped. This establishes an archive-derived single-pose candidate without needing a guessed animation cursor. Runtime visibility and pose still require front-buffer comparisons.
