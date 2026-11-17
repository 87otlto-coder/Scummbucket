# MI2 Room55 — complete entry sound/script handoff LSCR224 (17 November 2026)

**Evidence:** read-only original DOS VGA `MONKEY2.001` SHA256 `ad045372e0d49626503bb50fca29a687ec8e01ef75d9b8bca702a366d143819e`. Original Room55 LSCR224 tagged chunk `0x49A160`, bytecode begins at `0x49A169`, **33/33 bytes, 11 source-aligned instructions, one valid branch target**, independently checked with pinned [ScummVM v2026.4.0 script_v5.cpp](https://github.com/scummvm/scummvm/blob/v2026.4.0/engines/scumm/script_v5.cpp) and [script.cpp](https://github.com/scummvm/scummvm/blob/v2026.4.0/engines/scumm/script.cpp). **No runtime, exact MIDI/iMUSE interpretation or independent descumm output.** No original resources committed.

Complete linear source bytecode and branch:

| PC | Source opcode | Semantics |
| ---: | --- | --- |
| `0x000` | `62 77` | `stopScript(119)` (global script ID 119, **not** sound119) |
| `0x002` | `4C 01 10 01 FF` | `soundKludge([272])` (word-vararg 0x0110) |
| `0x007` | `68 00 00 78` | `Var0 = isScriptRunning(120)` |
| `0x00B` | `28 00 00 10 00` | `equalZero(Var0)`: if global120 is running (Var0 !=0), branch to PC0x020 and stop; if not, execute next sound/setup steps |
| `0x010` | `1C 72` | `startSound(114)` |
| `0x012` | `4C 01 FF FF FF` | `soundKludge([-1])` |
| `0x017` | `2A 78 FF` | `startScript(120)` |
| `0x01A` | `3C 77` | `stopSound(119)` |
| `0x01C` | `3C 71` | `stopSound(113)` |
| `0x01E` | `3C 73` | `stopSound(115)` |
| `0x020` | `A0` | stopObjectCode |

The exact audio effect of `soundKludge` words **272 and -1** must be interpreted through the actual sound/iMUSE engine state, which was NOT instrumented. The source proves the operation arguments, not whether each sound is audible, active in a given device configuration, or synchronized to a particular native framebuffer update.

This completes the **Room55 entry call tree** source alignment:

`ENCD → startScript(224); startScript(200)` where:
- **224** is this conditioned sound/global-script handoff.
- [200](MI2_ROOM55_COMPLETE_ENTRY_SCRIPT200_20261117.md) initializes 23 objects, walkboxes8–11, eight actor positions/talk colors and starts 211/213 plus conditionally212.
- [211](MI2_ROOM55_COMPLETE_SPATIAL_SCRIPT211_20261117.md) performs distance/Y-dependent idle/group scheduling.
- [212](MI2_ROOM55_COMPLETE_SPEAKER_CONTROLLER_20261117.md) handles active speaking actor animation.
- [213](MI2_ROOM55_SEVEN_PAIR_SPEECH_SYNC_20261117.md) synchronizes paired object images with animation flags.
- [220–223](MI2_ROOM55_COMPLETE_IDLE_SCRIPTS220_223_20261117.md) are ambient randomized schedulers that can also start the speaking actor's image loops.

**Remaining:** decode locals 214–219 and identify global script119/120's semantics if useful for precise audio or timing. The original game must still be captured before claiming animation or sound fidelity.

**Status:** original bytecode aligned; actual engine execution/pixels/audio unverified.
