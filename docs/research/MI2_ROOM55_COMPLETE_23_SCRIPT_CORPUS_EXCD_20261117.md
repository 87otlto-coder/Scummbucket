# MI2 Room55 — fully aligned EXIT audio conditions and complete 23-local-script corpus (17 November 2026)

**Evidence category:** read-only original DOS VGA source-bytecode inspection `MONKEY2.001` (SHA-256 `ad045372e0d49626503bb50fca29a687ec8e01ef75d9b8bca702a366d143819e`) combined with prior complete narrow walks of all **23 Room55 LSCR bodies**. Script opcode and source var bindings cross-checked with pinned [ScummVM v2026.4.0 script_v5.cpp](https://github.com/scummvm/scummvm/blob/v2026.4.0/engines/scumm/script_v5.cpp) and [vars.cpp](https://github.com/scummvm/scummvm/blob/v2026.4.0/engines/scumm/vars.cpp). **No runtime, independent official descumm output or indexed-frame fidelity validation.** No original game data/art/transcripts committed.

## Complete exit script and conditional sound handoff

Room55 original `EXCD` tagged chunk offset **`0x497887`**, bytecode body 76 bytes.

**Independent full narrow walk: 76/76 bytes, 11 instructions, 3/3 relative branch destinations on valid boundaries.** The first three conditional guards must all succeed to run the audio cleanup block:

1. **`Var72 == 53`** at PC0x000. ScummVM v5 variable table identifies **Var72 = VAR_NEW_ROOM**, the destination room. If the destination is not Room53, exit script stops immediately.
2. **`getOwner(613) == Var1`** at PCs0x007/0x00C. ScummVM identifies **Var1 = VAR_EGO**, so source requires object613 to be owned by Guybrush. A direct archive CDHD/OBNA source lookup identifies **object613's OBCD name as “map”**, stored with Room55. Whether this logical object is in inventory in a particular save is unobserved.
3. **`Bit[40]==0`** at PC0x013; if set, the source skips cleanup. Bit40's full puzzle purpose/writers have NOT been established.

When these conditions all hold:

| PC | Original v5 operation |
| ---: | --- |
| `0x018` | `stopScript(120)` |
| `0x01A` | `stopScript(122)` |
| `0x01C` | `soundKludge([269,114,0,60])` |
| `0x02A` | `soundKludge([269,118,0,60])` |
| `0x038` | `soundKludge([269,117,0,60])` |
| `0x046` | `soundKludge([-1])` |
| `0x04B` | stop |

The exact original/iMUSE audio semantics of these command arrays and real device response remain unverified. **Do not describe them as literal sound-stop calls or 60 milliseconds** until the appropriate sound interpreter implementation/trace establishes their meaning. The source *does* unambiguously encode those word-vararg lists.

Room55 entry `ENCD` was already fully aligned as 7-byte `startScript(224)`, `startScript(200)`, stop. [LSCR224](MI2_ROOM55_COMPLETE_ENTRY_SOUND224_20261117.md) conditionally starts sound114/global script120 and handles other sound commands. Entry and exit thus coordinate the **same global script120** and multiple sound IDs, but exact audio phase synchronization is not observed.

## Inventory completion milestone: every original Room55 local script body has a narrow full alignment

The original Room55 archive contains **23 LSCR resources totaling 10,183 source bytecode bytes**:

`200,201,202,203,204,205,206,207,209,211,212,213,214,215,216,217,218,219,220,221,222,223,224`.

Source-complete independent narrow walks exist across the following research documents:
- [201/202/203–207/209](MI2_ROOM55_STATIC_EVENT_LOOPS_20261116.md) — earlier 8 script bodies, including loop/random-dwell behaviour.
- [200](MI2_ROOM55_COMPLETE_ENTRY_SCRIPT200_20261117.md) — scene initialization, 23 image draws, actor placement, walkbox flags, conditional Bit210 animation and child setup.
- [211](MI2_ROOM55_COMPLETE_SPATIAL_SCRIPT211_20261117.md) — Ego position/distance and actor-Y-based four-group scheduler.
- [212](MI2_ROOM55_COMPLETE_SPEAKER_CONTROLLER_20261117.md) — `VAR_TALK_ACTOR` image state controller, actor8 close/far modes.
- [213](MI2_ROOM55_SEVEN_PAIR_SPEECH_SYNC_20261117.md) — seven flag-driven paired object-state synchronizations.
- [214–219](MI2_ROOM55_COMPLETE_PARTY_DIALOGUE214_219_20261117.md) — complete conversation source scripts and shared player-guest caller.
- [220–223](MI2_ROOM55_COMPLETE_IDLE_SCRIPTS220_223_20261117.md) — complete randomized ambient/idle child scheduling.
- [224](MI2_ROOM55_COMPLETE_ENTRY_SOUND224_20261117.md) — conditional global sound/script startup.

**Claim scope:** *Every 23 original local script body has a previously reported full-consumption narrow opcode walk*, in addition to fully aligned ENCD and EXCD. This is a significant **static decoding research milestone**, **not** a verified general SCUMM interpreter, complete caller reachability, full verb-handler corpus, independent official descumm agreement, observed gameplay/timing or pixel fidelity.

Outstanding original **OBCD/VERB** handlers beyond eight identical party guests, global script119/120/122 interactions, external callers, sound effects and actual actor/costume masks still need separate work. Full validation must use pinned descumm and real non-enhanced ScummVM captures with original resource hashes.

## Architecture: stateful party scene, not a simple background loop

Room55 now has source-proven:
- 8 positionable actors and 8 identically wired party-guest objects;
- 23 separate local scripts with scene, dialogue, sound, idle and image-state roles;
- a transition-conditioned sound exit;
- actor-relative proximity/Y thresholds and speaker identity driving alternative visual/dialogue modes;
- 7 synchronized object-state pairs, and additional original source imagery;
- sequential-to-random dialogue fallbacks, plus randomized idle dwell/yields.

The P3/P4/P6 viewer needs a stateful event/log representation to preview such a scene. Mark any predicted sequence as **source-derived/inferred** until a real engine trace exists. No copyrighted game data in Git.
