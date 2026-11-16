# P4 — original MI2 exact-object-rectangle research

16 November 2026. **Read-only archive structural investigation, no native
runtime verification or new executable tests.**

## Source and method

Original DOS VGA MI2 `mi2.zip` was read without modifying it.
Both `MONKEY2.000` and `MONKEY2.001` matched the fingerprints in
[the structured record](../validation/P4_OBJECT_EXACT_RECT_CANDIDATES_20261116.json).

A separate temporary Python metadata scanner parsed the XOR-0x69 decoded
`LECF/LOFF/LFLF/ROOM` hierarchy, paired `OBCD` `CDHD` and `OBIM`
`IMHD` by decoded global object ID, and read the v5 `CDHD` byte-sized
`x, y, width, height` (room-pixel units = stored values times eight).
The parser examined **110 rooms, 1,145 OBCD records and 1,145 matched
OBIM records**, consistent with earlier resource inventory counts.

The scan grouped **exact equality of stored rectangle** (same x, y, width,
height) within the same room. This is not a general geometric overlap
test, nor a record of what remains visible during gameplay. It does not
apply script-driven runtime movement, validate default object state, or
reconstruct local object slot indices.

The source matching criterion follows
[ScummVM v2026.4.0 `o5_drawObject`](https://github.com/scummvm/scummvm/blob/v2026.4.0/engines/scumm/script_v5.cpp#L1104-L1129).
That routine can reset exactly co-located objects to state zero when
the opcode is executed. These groupings are therefore **relevant
candidates**, not verified execution of that opcode.

## Overall structural result

| Measure | Archive result |
|---|---:|
| Room resources examined | 110 |
| Paired source object records | 1,145 |
| Exact-rectangle groups before filtering | 34 |
| Zero-width/height groups excluded | 14 |
| Nonzero group with no stored images excluded | 1 |
| Nonzero-size groups with at least one stored state | **19** |
| Rooms represented by those groups | **15** |
| Objects belonging to selected groups | **192** |
| Groups containing a multi-image-state object | **6** |
| Object records with nonzero parent slot | **6**, across 6 rooms |

Room 94 contributes 136 records from **one 40×24 rectangle**, plus a
separate three-object group. Because the large group dominates the object
total, report both the group count and object count; do not characterize
192 as 192 independently animated scenes.

## Highest information-value groups

| Room | Source CDHD rectangle | Object IDs / counts | Stored IMxx counts | Research hypothesis |
|---|---|---|---|---|
| 94 | (0,0,40,24) | 136 members (sample IDs 897–900) | all 1 | Many possible interchangeable object records |
| 32 | (0,0,72,32) | IDs 333–344 (12) | all 1 | Mutual-exclusivity candidate |
| 72 | (40,32,40,64) | IDs 741–748 (8) | 2 each | Interactions between peer selection and image states |
| 105 | (0,0,56,48) | IDs 1137, 1139, 1142 | 5, 15, 3 | Strong multi-image peer-reset candidate |
| 88 | (104,48,96,72) | IDs 813, 818, 819 | 4, 1, 1 | Mixed single/multi-state peer group |
| 48 | (240,32,24,32) | IDs 517, 515 | 1, 1 | Object 517 additionally has a parent-state gate |
| 107 | two distinct same-rectangle groups | IDs 1147/1150 and 1148/1152 | 3/1 and 2/2 | Mixed group complexity without huge object count |

Room 94 is a high-value structural stress case, but its gameplay
trigger, use and timing are **unknown**. Room 105 is a promising
higher-information *multistate* case. Neither is automatically a
background animation or a justified native capture target until
script/caller relationships are established.

## Six source parent-slot references

| Storage room | Object | Raw parent slot | Raw CDHD flags | Source-derived parentstate |
|---:|---:|---:|---:|---:|
| 13 | 113 | 1 | 0x80 | 1 |
| 29 | 279 | 3 | 0x80 | 1 |
| 38 | 382 | 13 | 0x00 | 0 |
| 39 | 410 | 11 | 0x00 | 0 |
| 48 | 517 | 20 | 0x80 | 1 |
| 89 | 824 | 2 | 0x00 | 0 |

The `parent` field is an **engine-local object slot**, not an object ID.
[object.cpp L1074–1163](https://github.com/scummvm/scummvm/blob/v2026.4.0/engines/scumm/object.cpp#L1074-L1163)
describes v5 parentstate interpretation. Normal draws traverse the
parent chain and compare its low state nibble:
[object.cpp L600–645](https://github.com/scummvm/scummvm/blob/v2026.4.0/engines/scumm/object.cpp#L600-L645).
Parent-slot-to-object identity and actual state are runtime-sensitive.
Do not map a raw slot number directly to an object without observing
the loaded room's local slot order.

## What to investigate later, without inventing animation

1. Search aligned `descumm -5` instruction references targeting the
   listed object IDs. Label byte-pattern candidates separately until
   disassembler instruction boundaries and operands are confirmed.
2. For the selected room, capture **actual** room-local object slots,
   parent-state chains and initial/current rectangles before applying
   a co-location hypothesis.
3. Record executed `o5_drawObject` with all old/new global object states
   and peer resets; distinguish it from `o5_setState`'s dirty-strip path.
4. Capture actual queued and full-pass object draw events and the independent
   indexed frontbuffer, using the phase contract in
   [P4 engine source phase map](P4_SCENE_STATE_ENGINE_PHASE_MAP_20261116.md).
5. Reject any inferred state duration or complete-scene fidelity claim
   until reference comparisons support it.

No copyrighted game bytes, images, audio, private saves, ScummVM
source/binaries or capture data have been committed. Only source-derived
metadata and research conclusions are included. All original inputs
remain read-only, and the roadmap remains P4.
