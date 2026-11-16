# MI2 Room 48 — actor staging and object-state transition in LSCR 202 (2026-11-16)

Research-only independent original-archive opcode walk against pinned ScummVM v5 handler definitions, **not** original DOS/ScummVM runtime capture or complete descumm confirmation. The analyzed source is original DOS VGA `MONKEY2.001`, stored-byte SHA-256 `ad045372e0d49626503bb50fca29a687ec8e01ef75d9b8bca702a366d143819e`; original bytes not modified.

Room 48: native 320×144, 41 object IDs, 34 zero-image `OBIM`s, nine stored image states, 18 local scripts, 3 background Z-planes. Original source image decoded privately shows a cluttered interior containing layered goods and furnishings; visual scene identity/costume layering are not independently verified.

## Full narrow static walk

`LSCR[202]`: chunk starts at decoded resource offset **4,180,353**; **113-byte body**, **28 aligned v5 instructions**, no unread bytes or invalid relative-branch targets. The narrow parser handles only opcode types used in this script (`equalZero`, `putActorInRoom`, `putActor`, `stopScript`, `animateActor`, `breakHere`, `walkActorTo`, `setClass`, `waitActor`, `setState`, `startScript`, `jumpRelative`, `stopObjectCode`). This is stronger evidence than the earlier unaligned setState byte patterns, but **not descumm-validated** and still lacks actual execution observations.

The initial bit-variable gates reference `0x8044` and `0x8056` (two separate bit refs; semantics of each game flag are not yet traced). The relative branches divide setup and subsequent staging. The following are source-decoded candidate operations, not proof their branch is taken:

| Script-body offset | Static operation |
| --- | --- |
| `0x0000,0x0005` | Test bit-variable references `0x8044`, `0x8056` |
| `0x000A` | Put actor **7** in room **48** |
| `0x000D` | Position actor 7 at **(203,66)** world-pixel coordinates |
| `0x0013` | Put actor **8** in room **48** |
| `0x0016` | Position actor 8 at **(175,66)** |
| `0x001F` | Stop local script **214** |
| `0x0021–0x002A` | Actor 7/8 animation actions **1,1,245,244**, respectively |
| `0x002D` | Explicit `breakHere` script yield |
| `0x002E` | Walk actor 7 toward **(225,66)** |
| `0x0034` | Walk actor 8 toward **(150,66)** |
| `0x003A` | Set class argument 160 on object 513 (v5 class 32 **set**) |
| `0x0041` | Set class argument 32 on object 518 (v5 class 32 **clear**) |
| `0x0048` | **WaitForActor(8)**; progress is actor-motion gated, not fixed wall-clock time |
| `0x004B` | Move actor 8 out to room **0** |
| `0x004E` | Set object 517 state 1 |
| `0x0052` | Clear class 32 on object 517 |
| `0x0059` | Set object 515 state 1 |
| `0x005D–0x006D` | Branch on bit `0x8056`; select object 514 state 1 **or** 0 |
| `0x006D` | Start local script **214** with no explicit variable arguments |
| `0x0070` | End bytecode |

Relevant source engine semantics:
- `o5_putActor` uses world pixel positions, unlike `o5_drawObject`'s optional object-placement parameters, which are multiplied by 8. **Do not apply an 8x transform to actor walk coordinates.**
- `o5_wait` with `SO_WAIT_FOR_ACTOR` is condition-gated and may defer execution; this sequence cannot be faithfully recreated from a uniform frame interval without observing actor motion state.
- `setClass` with argument 160 sets class 32, whereas argument 32 clears class 32. These are not independent class numbers 160 versus 32.
- `setState` on object 517/515/514 and actor animation/movement are different mechanisms; both may contribute to scene's foreground.
- Zero-image objects are not visible sprites merely because they have class/state script instructions.

## Why this matters for P4

This is an archive-backed example combining **actor entrance/placement, multiple costume animations, walking, actor-completion waits, object class changes and object image states** in a room with three depth-mask planes. It is categorically different from Room 55 random image-state yields, Room 72 dynamic object placement and Room 44 facial object composition. The existing archive-only `scene_inventory.py` cannot establish this temporal/conditional event chain.

**Do not assert object 514 is always shown**: its state 1/0 outcome depends on `0x8056`. **Do not assert actors 7 and 8 appear together in every visit**: two initial bit checks control the path.

Follow-up: run authentic descumm for LSCR 202, determine entry/caller and bit-variable writers, trace LSCR 214 relationship, capture actor 7/8 COSTs and motion, then compare native indexed frames under ZP01/ZP02/ZP03 with state/class transitions. No gameplay verification performed in this spelunk session.

References:
- https://github.com/scummvm/scummvm/blob/v2026.4.0/engines/scumm/script_v5.cpp (`o5_putActor`, `o5_putActorInRoom`, `o5_animateActor`, `o5_walkActorTo`, `o5_setState`, `o5_wait`, `o5_setClass`)
- https://github.com/scummvm/scummvm/blob/v2026.4.0/engines/scumm/object.cpp
