# 13 November 2026 — private native Room 7 ScummVM save confirmed

**Evidence class: read-only direct decoding of the uploaded save; supplemented by
inspection of its own embedded thumbnail. Not an engine-run capture.**

## Supplied file identity

- Uploaded name: `monkey2-1.s01`.
- Original byte count: **24,946**; SHA-256:
  `39035338ed89bdfe754f31e390f247c83095f1938aeae6877c0373ad7f72aa0d`.
- Gzip-wrapped ScummVM save, decompressed to **101,768 bytes**; decompressed
  SHA-256: `17246b1cef60213e13437c53bf2947eb1085c3287a80e7a8af4f15d8e7c151e7`.
- The decompressed stream starts with `SCVM`, serialized save version **124**
  and description **`7`**.

## Decoded SCUMM state

The `THMB` section starts at offset 44 and has total size 32,022 bytes.
`INFO` follows at offset 32,066, version 2, size 26. The game serializer
starts at offset 32,092, with the same 16-byte internal game MD5 field
`3686cf8f89e102ececf4366e1d2c8126` as the prior Room 23 uploaded save.

Immediately after the MD5 field, the serialized values are:

| v124 saved field | Observed value |
| --- | --- |
| `_curPalIndex` | 0 |
| `_currentRoom` | **7** |
| `_roomResource` | **7** |
| `_numObjectsInRoom` | **20** |
| `_currentScript` | 255 |

The object count is consistent with the independently decoded **20 paired
Room 7 objects (IDs 40–59)**, without by itself proving every object state.

## Embedded thumbnail

The save's `THMB` header indicates a **160 × 100**, 2-byte-per-pixel RGB565
snapshot. Decoding the stored pixels as big-endian 16-bit RGB565 produces
a visually recognizable image of Guybrush on the rope bridge with the SCUMM
verb/inventory interface. This visually corroborates the Room 7 identification.
**No thumbnail/image bytes have been committed to the repository.**

## Decision and next verification

**Accepted:** this user-supplied file is structurally consistent with a
ScummVM v124 Room 7 save, and it is suitable for attempting a normal
saved-game launch through the existing guarded `--native-room7-save`
capture path in an instrumented, compatible ScummVM build.

**Not yet accepted:** successful runtime restoration, full 87-frame capture,
exact frame reconstruction from this save, game route/progression provenance,
other rooms or other game editions. A saved room field of 7 does not
prove the path used to enter the room, and a saved thumbnail is not
a substitute for the engine front-buffer comparison.

To re-check on Windows after fast-forwarding the research branch, run from
`F:\Dev\SCUMMBUCKET\SOURCE\ScummBucket`:

~~~powershell
python -B -m tools.inspect_scummvm_save 'PATH_TO_PRIVATE_monkey2-1.s01' --require-room 7
~~~

The command is read-only, prints a hash and saved-state metadata, and fails
nonzero for a wrong room or unsupported format. Do not confuse this with
the full engine capture: follow
[P4_ROOM7_NORMAL_ENTRY_TEST_20261113.md](P4_ROOM7_NORMAL_ENTRY_TEST_20261113.md)
for that separate private experiment. Do not commit the original save or
captured output. Keep the research PR in draft pending the remaining
technical and licensing gates.
