# P4 Room 7 — uploaded original-archive smoke verification (12 November 2026)

**Scope:** independent, read-only structural and one-cel RLE checks against the user-provided `mi2.zip` in the chat execution environment. This is *new original-archive evidence*, not a new ScummBucket CI or F-drive acceptance run. No original files, decoded pixels, PNGs, firmware ROMs or game resources were committed.

## Input identity

The ZIP contained exactly one pair under `mi2/`. The raw, unmodified members reproduced both previously pinned edition hashes:

| Member | SHA-256 |
| --- | --- |
| `MONKEY2.000` | `cde7aa8980317e3a750fbb3b49884cdddaf1ff3d4231a0c840b22cceed9033f1` |
| `MONKEY2.001` | `ad045372e0d49626503bb50fca29a687ec8e01ef75d9b8bca702a366d143819e` |

Applying the known v5 XOR-`0x69` decoding produced the `RNAM` and `LECF` signatures. These digest matches are strong evidence that this upload is the *pinned* Monkey Island 2 DOS VGA archive, not a new edition claim.

## Room 7 byte-level checks

- Decoded `ROOM` at `MONKEY2.001` offset **392340**, length **82695**; walked **60** bounded immediate child chunks.
- `RMHD`: **784 × 144**, **20** declared room objects.
- `TRNS`: transparent palette index **191**.
- `CYCL`: six records with ranges **16–18, 176–177, 178–179, 180–181, 182–183, 184–185**; raw rates **384, 384, 459, 306, 228, 153**; zero flags for all six.
- The initially pinned offsets were subsequently checked against the original archive's own directory graph: `MONKEY2.000` `DCOS[142]` gives room **7** and room-relative offset **192120**; decoded `MONKEY2.001` `LOFF[7]` points to ROOM source offset **392340**. Their sum is **584460**, the exact start of a bounded `COST` child inside Room 7's `LFLF` bundle. This is independently resolved original-directory provenance, not simply a hardcoded offset. The subsequent **native background and depth-layer pass** is recorded below.

## Costume 142 one-cel structural/RLE check

- Decoded `COST` at `MONKEY2.001` offset **584460**, length **1509**, SHA-256 `7ef3e98fb9cd824782b0cf7e93d9e7f3c059354557ec7e08d714eda9425a7c5f`.
- Header: `0x59` **32 local palette slots**, highest declared animation identifier **14**.
- Independently resolved limb **0**, sequence position **0**, through the COST command and pointer tables to a cel at relative offset **119**.
- Cel header: **89 × 51**, relative **X = −47, Y = −50**, movement deltas **0, 0**.
- Column-major 32-slot RLE decoded **4539** palette-slot positions: **2225 opaque** and **2314 transparent** (slot 0); local slot IDs observed **0–28**.
- RLE consumed **1378** encoded bytes, ending exactly at the resource boundary (`119 + 12 + 1378 = 1509`). Decoded local-slot-plane SHA-256: `0dd785d9b58e4cdc54c9035a4d6875dbafef662df86a42f153cd031735848b15`.

The decoded *known pose* is structurally complete. An end-of-chunk cel alone is **not proof of live animation timing or a complete animation-state inventory**. ScummBucket's renderer code was not imported/run by this independent smoke script.

## Follow-up: complete native panorama and Z-plane extraction

A separate, read-only Python decoder operated on the same byte-verified uploaded archive using bounded SMAP strip pointers and the documented v5 strip algorithms. It successfully reconstructed **98/98** indexed 8-pixel strips, giving **784 × 144** pixels. Codec distribution was **95 strips using codec 68** and **3 using codec 28**; no transparent-background codec was required.

- Reconstructed indexed panorama SHA-256: `843f5d1d81ed8bb8f7353a0c5b3c52d2229505becbd47a411b3cd4314b5bccfc` — **exact match** to the prior F-drive independent Room 7 panorama research.
- Initial 768-byte CLUT SHA-256: `a02937d50fc9d91d71df7bb70ac3d43bd73a95ed007bc6372fe8ba7627c0d88d`.
- Independently expanded native `ZP01` to an **784 × 144** binary mask with **18,366 set pixels**, matching the prior research count. Unpacked mask SHA-256: `4bf76f6b3bdf0a972c0a020b7386fb942621f18d692b3d5a42bd8ce333203214`.
- The pinned COST cel was also exported to a private transparent **89 × 51** RGBA PNG using Room 7's CLUT; the alpha counts match the separately decoded local slots (**2,225 opaque / 2,314 transparent**).

The newly created `room7_background_native.png`, `room7_ZP01_native.png`, and `room7_costume142_cel0_native.png` remain **private local chat artifacts, not Git resources**. Their PNG-byte SHA-256 values are respectively `50fe01a57626f5472d4b62ea6c7f8be2849cc7fa61ebd572d53a3ed51d8d34eb`, `e2ea0bbfbd38d916ba67230e21c36ece2a09104461c25435dca64ac99c433f2e`, and `cd40bb99425a80579a06973fbad2f024a4cdc36848b4cacb300836a337bf0b35`. These hashes describe encoded PNG files, not source-index equality.

**Boundary:** This confirms archive-native background / depth extraction and a single transparent scenery cel, independently of the F-drive's previously generated files. It does not replay the 87 captured engine frames or verify sprite placement, actor timing, visible Z-clipping across frames, or natural room entry.

## Input correction

A separate upload named `mi1.zip` was inspected. It contains a `mk1/` hierarchy and `MK1.EXE` (Mortal Kombat 1), and has **no** `MONKEY2.000/.001` pair or common Monkey Island SCUMM members. It must **not** be treated as a Monkey Island 1 fixture.

## Verification method and limits

An isolated Python standard-library smoke script read the two ZIP members, recomputed SHA-256, XOR-decoded in memory, parsed bounded big-endian chunk headers, checked Room 7 records, followed COST pointers, expanded 32-slot column-major RLE, and checked run boundaries/pixel accounting. It wrote **only metadata JSON**, no asset bytes. A direct test of the mislabeled MI1 upload failed clearly with `Expected exactly one MONKEY2.000; found 0`.

**Not established in this pass:** F-drive file presence, ScummBucket integration-test pass, Room 23 regression, exact Room 7 engine-indexed front-buffer comparison, 87-frame source capture hashes, runtime actor animation states, normal gameplay room entry, or browser visual playback. Those acceptance gates remain separate; draft integration PR #8 must remain unmerged pending its stated requirements.

**Classification:** source bytes and resource structure = independently archive-decoded; `DCOS[142]` room/link provenance = independently index- and LOFF-resolved; pose cel = separately decoded from that linked source; animation/runtime fidelity = not tested here.
