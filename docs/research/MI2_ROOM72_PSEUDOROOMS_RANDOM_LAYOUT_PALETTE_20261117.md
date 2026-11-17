# MI2 Room72 — three logical room aliases, procedural object layout and palette-intensity animation (17 November 2026)

**Evidence category:** independent read-only original DOS VGA `MONKEY2.001` bytecode and original `MONKEY2.000` room index; SHA-256 of original .001 member `ad045372e0d49626503bb50fca29a687ec8e01ef75d9b8bca702a366d143819e`. All widths/IDs/bytecode PCs relate to this edition only. Private narrow V5 decoder checked against **pinned ScummVM v2026.4.0** [script_v5.cpp](https://github.com/scummvm/scummvm/blob/v2026.4.0/engines/scumm/script_v5.cpp) (`o5_pseudoRoom`, `o5_stringOps`, `o5_startObject`, `o5_roomOps`, `o5_expression`, `o5_drawObject`) and [room.cpp](https://github.com/scummvm/scummvm/blob/v2026.4.0/engines/scumm/room.cpp) (`startScene` room/resource distinction), [palette.cpp](https://github.com/scummvm/scummvm/blob/v2026.4.0/engines/scumm/palette.cpp) (`darkenPalette`), [script.cpp](https://github.com/scummvm/scummvm/blob/v2026.4.0/engines/scumm/script.cpp) (`0x2000` array indirection). **NOT runtime gameplay, official descumm comparison, original DOS interpreter execution, native pixel parity or a complete P4 decoder implementation.** No copyrighted game source or art committed.

## Critical mapping: logical rooms 130, 131, 132 share *physical* room resource 72

The original DOS archive's **global script1** (stored with Room4) at decoded .001 offset `0x35DD7` contains exactly `CC 48 83 82 84 00`. Pinned ScummVM v5 `o5_pseudoRoom` takes `0x48=72` as resource ID and, for each high-bit byte, assigns `_resourceMapper[j & 0x7F] = 72`:

| Original raw pseudo-room byte | Lookup slot after `&0x7F` | Runtime logical room using the slot | Physical room resource |
| --- | ---: | ---: | ---: |
| `0x83` | 3 | **131** | **72** |
| `0x82` | 2 | **130** | **72** |
| `0x84` | 4 | **132** | **72** |

In pinned ScummVM `startScene` (`room.cpp`), when a room number `>=0x80` is entered in v5, `_currentRoom` and **`VAR_ROOM`** retain the logical 130/131/132 value, while **`_roomResource = _resourceMapper[room & 0x7F]`** becomes 72 and `VAR_ROOM_RESOURCE` names that physical art/script resource. This explains why the original Room72 bytecode explicitly compares **`Var4=VAR_ROOM`** to **130/131/132** even though the LFLF resource bundle and scene art are physically Room72.

**Precision:** byte 0x83 does *not* directly index array slot131; it indexes slot3, and room number131 reaches slot3 when the high bit is stripped at scene load. Both pieces of source are necessary to establish the mapping. The original startup `SCRP[1]` source opcode still requires natural startup reachability, which was not captured. The source data unambiguously stores the mapper assignment.

**P1/P2/P4/P6 implication:** scene identity must be at least `(logical_room_id, physical_resource_room_id, edition)`; globally stored scripts also need their separate **storage bundle** and **currently executing room**. One indexed background can support several divergent scripted states.

## Complete static bytecode census for every room-owned active script in physical Room72

| Resource | Source body start | Body bytes consumed | Narrow instructions | Valid relative targets |
| --- | ---: | ---: | ---: | ---: |
| `ENCD` | `0x5EBA78` | **195/195** | **40** | **7/7** |
| `LSCR200` | see [earlier 487-byte analysis](MI2_ROOM72_DYNAMIC_OBJECT_LAYOUT_20261116.md) | **487/487** | **74** | all aligned |
| `LSCR201` | `0x5EBD3E` | **840/840** | **130** | **57/57** |
| `LSCR202` | `0x5EC08F` | **142/142** | **23** | **10/10** |
| `LSCR203` | `0x5EC126` | **9/9** | **4** | 0 |
| `LSCR204` | `0x5EC138` | **81/81** | **13** | **5/5** |
| `LSCR205` | `0x5EC192` | **199/199** | **37** | **14/14** |
| `EXCD` | `0x5EBA6F` | **1/1** | 1 | 0 |

**Only complete local-script boundary alignment is claimed**; the custom narrow parsers, specific exception semantics, source string-resource state and actual script callers still need official descumm/runtime verification. Importantly, `LSCR204` is an independent palette-effect candidate even though previous background research saw no `CYCL` in this room.

## ENCD: script-initialized dynamic layout, actor interaction, state swap

Room72 ENCD source algorithm:
1. Check current logical room. In the source branch, when **Var[102] != 132 OR Var[456] == 0**, `LSCR201` is run; when **Var[102] == 132 AND Var[456] != 0**, the initializer is skipped. In either case the ENCD executes **`startScript(200)`** immediately after the optional initializer path. Because script200 is the previous **487-byte no-yield dynamic layout renderer**, the resource-derived arrangement can be ready within one interpreter slice.
2. If `getActorRoom(actor1) == 0` source path is chosen, compute a random index derived from `Var[370]`, place Ego in logical **room132** at the selected dynamic object from **`Var[371 + selectedIndex]`**, animate actor action250, temporarily draw that object in state2, then **start Room72 object verb2** using an argument sourced from the selected object ID (source `startScript(203,[chosenObject])`).
3. Swap or rearrange values among two indexed global variable arrays, iterating 49 positions **0..48** (encoded arrays begin at Var356 and Var406 in the source), to carry a mutable arrangement into or out of this room state. The exact original game mechanism/purpose of this swap requires external script/global state analysis.
4. Execute a short Ego cutscene using costume81, actor action250/7, five explicit yields, restore costume1; or take an alternate array-swap path. ENCD terminates.

The **fully aligned** source bytecode contains 40 instructions and all seven valid jump destinations. Do not interpret its random selection as an observed starting actor placement or claim the arrays always swap at room entry regardless of actor state.

## LSCR201: three distinct procedural initialization paths

`LSCR201` fully aligned **840/840 bytes, 130 instructions, 57 relative targets**. Its first `Var4=VAR_ROOM` branches are at PC0x000 (130), PC0x042 (131), PC0x084 (132):

- **Logical130 and logical131:** the two initial blocks currently have **byte-identical** state assignments: `Var356=1`, `Var357=1`, `Var358=0`, `Var359=0`, `Var360=0`, `Var366=0`, `Var370=3`; the selected object layout entries `Var[371+1..3]` become objects **741,742,743**, then jump to exit. These are deliberately distinct logical scene IDs sharing initial layout values, potentially to vary other entry scripts/environment, not proof they look different.
- **Logical132:** when **`Var102 ==71`**, one source path sets a similar simple baseline. Otherwise, the script seeds/counts combinations with **randomized variables**: source `getRandomNr(3)+1` for Var356 (1..4), conditional 1..3 for further counts, 0..4 for Var360, 0..2 for Var366, and 1..3 for Var370.
- It **initializes indexed object arrays** using `0x2000` indirect v5 references, including Var[361+], Var[367+] and Var[371+]. In source code Var[361+index] selections are from object IDs starting at **735**, Var[367+] from **739..740**, and Var[371+] from **741..748**. It **rejects duplicate candidates** for the selected Var371 entries using explicit relative-branch loops. Do not treat selected art states as simply image-number permutations; these are original logical object IDs.
- A later optional branch guarded by **`Var457 == 1` and `Bit365 == 0`** executes `startObject(variableID,verb19)` in a loop with source `getStringChar` probes against **string resource46** using Var459 offset and neighboring positions. This branch has now been proved to **inject the next required statue ID into the one/two/three chosen Var371 slots if absent**. Global script88 contains eight alternative four-object code paths for String46; see [seeded bone-statue paths](MI2_ROOM72_BONE_STATUE_EIGHT_PATHS_20261117.md) and [source-proven target injection](MI2_ROOM72_GUARANTEED_NEXT_STATUE_LAYOUT_20261117.md). No actual game input or runtime object handler has been observed.

The absence of `breakHere` in source201 means this is **procedural scene initialization**, not a fixed-timing animation. Its source RNG calls can be repeated until constraints are satisfied. A future synthetic exporter must record the *actual random selection outcomes and state* rather than pretending one universal scene layout exists.

## LSCR202/203/205: changing navigation, scene states and object scripts

- **LSCR202, 142/142 bytes and 10/10 aligned branches**: accepts an object ID in Local0, sets/clears class **6** based on selected logical room, checks encoded class flags, chooses `loadRoomWithEgo` to physical Rooms **71** or **73** or logical pseudo-room **132**, conditionally increments **Var457** and modifies **Var456**. It distinguishes the corresponding object IDs **731**, **721**, **749**, so these are *scripted navigation* outcomes tied to which part of the procedural scene is clicked.
- **LSCR203, 9/9 bytes**: two `breakHere` yields, then `drawObject(Local0, state1)`, terminate. This is a short *temporary image-state restoration* after another actor/entry operation, not a generic repeating animation.
- **LSCR205, 199/199 bytes and 14/14 aligned jumps**: uses `startObject(Local0,verb19)`, checks three adjacent characters of String46 at offsets based on Var459 against Vars375/**377**/376 **in that source comparison order**, mutates **Var160**, **Var457**, **Var459**, and possibly **Bit365** before routing Ego via `loadRoomWithEgo` to Room71/73 or `loadRoom(132)` with Ego temporarily removed from current room. Both player position and game state must be retained in scene previews.

These mechanisms are not guaranteed to run on arbitrary room entry; `LSCR202/205` callers and object verb dispatch must be traced separately. Do not claim the source scripts can be executed independently in all puzzle states.

## NEW P4 mechanism: LSCR204 is *random palette intensity animation without CYCL*

`LSCR204` fully consumes **81/81 bytes**, 13 instructions, five valid branch destinations. In source:

1. Gate on **`Var49=VAR_VIDEOMODE == 19`**, known VGA mode in ScummVM v5.
2. Sample **`getRandomNr(50) + 230`** into Local0 → raw intensity candidates **230..280**.
3. Reject any new candidate whose absolute difference from previous Local3 is **≤12**. Continue sampling until a change of **at least 13** is selected; then save the accepted value as Local3.
4. Call `roomOps` **`SO_ROOM_INTENSITY`** subopcode `0x88` with **three byte/variable operands** `[Local0,65,157]` and `[Local0,169,187]`. This maps to ScummVM's `darkenPalette(a,a,a,start,end)`, so it modifies **two disjoint palette index ranges**, not indexed pixel bytes.
5. Execute one `breakHere`, jump back and repeat.

**Palette-source nuance:** [ScummVM palette.cpp `darkenPalette`](https://github.com/scummvm/scummvm/blob/v2026.4.0/engines/scumm/palette.cpp) scales the *original active room palette* by `redScale/255`, `greenScale/255`, `blueScale/255` and caps resulting component values at **252** in native v5. Thus do **not** implement it by repeatedly multiplying the *already darkened* palette (which would accumulate drift), nor assume the raw intensity 280 is clamped to 255 before calculation. The engine uses integer arithmetic, so consecutive raw values may map to the same RGB output. Timing/visual phase is a future trace task.

This is a **major inventory gap**: original Room72 has no stored CYCL entries, yet has a source-coded continuously randomized **RGB palette animation with enforced minimum jumps in intensity**. A CYCL-only P4 census will miss it. Add `SCRIPTED_PALETTE_INTENSITY` as a mechanism distinct from `CYCL_PALETTE_ROTATION`, `SO_CYCLE_SPEED`, and `PALETTE_MANIPULATION`.

**Critical caller caveat:** `LSCR204`'s existence and source logic are confirmed. A targeted source search found **no literal direct startScript(204) caller in Room72's scripts or all 50 object verb handlers**; the sole identical literal in indexed global SCRP resources is guarded for Room46, where the local204 identifier refers to a different script. See [caller-gap analysis](MI2_ROOM72_ORPHAN_PALETTE_AND_BONE_CODES_20261117.md). **Indirect call/reachability remains unverified**, so it must be labeled *source-encoded potential palette effect*, not proven animated on a normal visit.

## Next high-value source and runtime gates

- Independently run official `descumm -5 -o` over original Room72 tagged `ENCD`, `LSCR200–205`; compare exact opcode/branch maps with source-aligned narrow walks.
- Find global scripts and object VERB handlers that initialize Vars102,356–377,406–454,456–459, Bit365, string resource46 and that start local204. Distinguish room resource ID72 from logical room130/131/132 and script-storage room.
- Source-driven preview should support separate **logical scene variants**, deterministic seeded/random layout selection, mutable image states, interaction class flags, conditional routing to Rooms71/73, and palette RGB modification; avoid claiming arbitrary source-only scenes as observed.
- Runtime: capture natural entry into each logical room (if reachable), original pseudo-room map, initialization RNG, actual object IDs and pixel bounds, object classes and clicked objects, script204 start/stop and RGB snapshots, indexed native framebuffer and exact timer phase. No release/completion label before matching reference captures.

**Status:** source-verified syntax and static dependencies, original game behavior and fidelity still unverified.
