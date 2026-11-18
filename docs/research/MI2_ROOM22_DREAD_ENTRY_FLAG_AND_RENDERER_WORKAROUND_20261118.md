# MI2 Room22 Dread: entry-controlled object state and original animation defect versus ScummVM fix

**Evidence:** read-only original MI2 DOS VGA MONKEY2.001, stored SHA-256 ad045372e0d49626503bb50fca29a687ec8e01ef75d9b8bca702a366d143819e, and pinned [ScummVM v2026.4.0 script_v5.cpp](https://github.com/scummvm/scummvm/blob/v2026.4.0/engines/scumm/script_v5.cpp) o5_setState/o5_drawObject. The exact original Room22 ENCD source body begins at **0x1C3ACE**, length46 bytes. Manually aligned its full set of short opcodes (not an independently tested official descumm). Original archive/game resource bytes are not committed. **No gameplay run, visual pixel parity or proof of any particular Bit321/129 runtime value.**

## Entire Room22 entry sequence, source PC

- **0x00:** startScript(200) — local room-setup helper.
- **0x03:** putActorAtObject(actor1,object234); **0x07:** animateActor(1,action250).
- **0x0A:** notEqualZero(Bit321), v5 reversed jump. When Bit321 is **nonzero**, continue to **PC0x0F** setState(object240,0), jump over alternate state. When Bit321 is **zero**, branch to **PC0x16** setState(object240,1).
- **0x1A:** notEqualZero(Bit321). Nonzero starts **local202** at PC0x1F; zero branches to PC0x25.
- **0x25:** notEqualZero(Bit125). Bit125 nonzero branches to stop; Bit125 zero starts **local201** at PC0x2A; PC0x2D stop.

This makes original **object240 “Captain Dread”** a **bit-gated object image** rather than a permanent overlay: Bit321 0 selects state1 (original stored IM01), Bit321 1 selects state0. The original source has **seven stored room OBCD entries**, including Dread. Per [Room22 object-only cycle](MI2_ROOM22_CAPTAIN_DREAD_OBJECT_ONLY_CYCL_20261118.md), Dread IM01 is the only identified stored image with nontransparent indices186..191, which overlap CYCL6/7/8; these cycles can matter to the composited image **only if a runtime-visible layer actually uses those indices**. Setting source object state1 alone does not prove pixels survived foreground masking or later object operations.

Bit125 and Bit321's wider puzzle purpose and game-state writers were not independently determined in this report. **Do not assume both local201 and202 execute on the same entry.** The exact 46-byte sequence makes their branches mutually exclusive via Bit321.

## Pinned ScummVM documents an original Captain Dread head animation bug

Primary ScummVM source `ScummEngine_v5::o5_drawObject()` has a targeted conditional engine workaround:

- Game ID MONKEY2, **not Ultimate Talkie**;
- **current room22**;
- current script slot **201**;
- `obj == 237`, `state == 1`;
- source **Bit129 == 1**; and
- `enhancementEnabled(kEnhMinorBugFixes)` is true.

The engine comments explain that after talking to Dread, handing him an object and immediately speaking again, the original game lacks a Bit129 guard and can glitch his head-facing animation. Under enhancement-on, ScummVM instead **skips 32 bytes of the currently executing script** at this point, returning before the ordinary draw. This is a **real branch affecting source PC/scripting**, not merely a postprocessing visual filter.

**Crucial distinction:** this fix relates to original logical **object237**, whereas the three object-only palette cycles were identified in **object240**; do not conflate them. Room22 has a mixture of animated actor/body image state, static/special object overlays and palette effects. The workaround might change which original objects are drawn later in the same script, so a capture with enhancements enabled is **not necessarily an oracle for exact original DOS behaviour**.

## P4 acceptance implications

- Log: original edition and SHA, current logical and physical room, Bit321, Bit125, Bit129, object240 state/visibility and object237 animation/draw, active script201/202 slots/PC, palette six relevant indices186..191, all CYCL counters, and whether ScummVM minor bugfix enhancements were enabled.
- Build **two separate comparison targets** if available: original-equivalent interpretation with that workaround disabled; enhanced ScummVM behaviour with workaround enabled. Never silently report the second as a verified original-script animation.
- Future stopCycle/setCycleSpeed checks and palette phase logs must determine whether all eight CYCL records advance during the actual encounter; original CYCL metadata is only initial state.
- Native index, palette RGB, Z-mask, drawObject same-bounds eviction and actor COST pixels must be compared at native scale before a P4 fidelity claim.

**Status:** original archive entry opcodes + primary ScummVM engine workaround source, **not observed executed behaviour**.
