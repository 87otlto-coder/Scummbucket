# P4 spelunking — Room 44: script-driven, repeated scenery state machine

**16 November 2026 · Source-only · No native debugger, playback, tests or
fresh runtime validation.** Primary edition is original DOS VGA MI2.
[Machine-readable source-offset register](../validation/P4_SPELUNK_ROOM44_20261116.json).

## What changed from the earlier candidate list

Room 44 is more promising than an ordinary pair of objects with the same
position. The original source contains **20 OBCD/OBIM object pairs, 6 LSCRs,
one ENCD, one EXCD and no active room palette-cycle records**. Each of
the 20 OBCD `VERB` tables has only the empty terminator and no handler,
and the OBNA names are empty. This is a room with many graphics controlled
by scripts rather than direct object-verb dispatch; it is not proof that
every object moves.

Original archive hashes: MONKEY2.000
`cde7aa8980317e3a750fbb3b49884cdddaf1ff3d4231a0c840b22cceed9033f1`;
MONKEY2.001
`ad045372e0d49626503bb50fca29a687ec8e01ef75d9b8bca702a366d143819e`.

Room `ROOM` chunk: offset **3,513,409**, size **110,035** in
XOR-decoded MONKEY2.001 (all offsets in this report are zero-based).

## Source object relationship

| Object | Loaded OBCD ordinal* | Original rectangle | Stored images | Source data |
|---:|---:|---|---:|---|
| 451 | 5 | (88,48) 112×96 | 1 (IM01) | OBCD 3,621,357 / OBIM 3,564,983 |
| 461 | 17 | (88,48) 112×96 | 3 (IM01–IM03) | OBCD 3,621,921 / OBIM 3,595,741 |

*Ordinal is the original source OBCD ordering, not independently observed
local object slot numbering in a native capture. Room 44 has no parent
references in its 20 original CDHD headers.

ScummVM
[`o5_drawObject`](https://github.com/scummvm/scummvm/blob/v2026.4.0/engines/scumm/script_v5.cpp#L1031-L1129)
queues the selected object and resets any local object with an exactly
matching current x/y/w/h to zero, before setting the requested state.
Therefore the **source-backed conditional consequence** of
`drawObject(461,state)` is that object 451 is cleared *if both retain
their original matching rectangles at execution*. Do not assume
runtime placement, current states or presentation order from source
metadata alone.

## Local script 201: bounded control-block reconstruction

Original LSCR 201: chunk offset **3,622,713**, 411 bytes, SHA-256
`db68dae76da0fb3ec2c70f31c0b06405a8a4a4a456d14f286a526c026d00cefe`.

The source bytes around the four `drawObject(461)` patterns are
self-consistent with ScummVM v5
[`o5_isEqual` and `jumpRelative`](https://github.com/scummvm/scummvm/blob/v2026.4.0/engines/scumm/script_v5.cpp),
[`o5_add`](https://github.com/scummvm/scummvm/blob/v2026.4.0/engines/scumm/script_v5.cpp)
and `o5_drawObject` operand rules:

- At 3,622,849, `o5_notEqualZero` branches away to 3,623,008
  if working variable **164** is zero.
- At 3,622,854, `o5_add` increases Var[164] by **1**.
- The following conditional tests and their apparent `drawObject`
  destinations are:

| Original source opcode | Condition | Apparent effect | Failed-condition destination |
|---:|---|---|---:|
| 3,622,859 | Var[164] == 2 | draw 461 state 1 at 3,622,866 | 3,622,875 |
| 3,622,875 | Var[164] == 3 | draw 461 state 2 at 3,622,882 | 3,622,891 |
| 3,622,891 | Var[164] == 4 | draw 461 state 3 at 3,622,916, with additional commands | 3,622,962 |
| 3,622,962 | Var[164] == 5 | draw 461 state 1 at 3,622,969 and set Var[164]=0 | 3,622,983 |

The earlier static survey's state order **1,2,3,1** therefore sits
inside a coherent conditional counter block rather than being four
arbitrary unaligned matches. Additional branches and script side effects
exist; this is **not** proof that gameplay reaches all four cases,
that every step is presented, or that each lasts one rendered frame.
`Var[164]` is explicitly assigned 1 in an adjacent candidate block of
LSCR 205 at source offset **3,623,303**; its actual trigger is still
to be traced through prior conditions.

## Repeating source structures

The body tails contain v5-style 16-bit signed relative jumps whose
calculated targets land precisely on a source script body start:

| LSCR | Body start | Tail jump opcode | Calculated target | Relevant control |
|---:|---:|---:|---:|---|
| 201 | 3,622,722 | 3,623,120 | 3,622,722 | `breakHere` at 3,623,119 |
| 202 | 3,623,133 | 3,623,158 | 3,623,133 | local delay-variable candidate at 3,623,142 |
| 203 | 3,623,171 | 3,623,251 | 3,623,171 | delay/wait logic to inspect |
| 205 | 3,623,264 | 3,623,309 | 3,623,264 | `breakHere` at 3,623,308 |

Script 200 has an additional *internal* backward jump from
3,622,709 to 3,622,405, so source-level repetition is not confined
to script 201. These offsets use the C++ decoder's signed 16-bit
relative-jump rule; no loop was actually exercised in the engine here.

The **room-entry ENCD** at offset 3,622,152 contains a contiguous
five-call sequence of `startScript`-shaped byte runs:

| Candidate source offset | Local script |
|---:|---:|
| 3,622,326 | 202 |
| 3,622,329 | 203 |
| 3,622,332 | 205 |
| 3,622,335 | 201 |
| 3,622,338 | 206 |

Those calls are plausible at source level; whether room-entry branch
gates reach this region, execution overlaps, or scripts are restarted
requires a complete disassembly and later runtime evidence.

## Next static and live evidence gates

1. Use **separately installed** ScummVM Tools `descumm -5 -o -h`
   to confirm the ENCD startScript calls and LSCR 201, 202, 203, 205
   opcode boundaries, conditionals, variable updates, branch destinations
   and yield/loop semantics. Do not distribute the GPL disassembler
   source inside this repository.
2. Trace all reads/writes of Var[164] across these local scripts and
   relevant global callers, then classify state activation as confirmed
   source path, still not observed execution.
3. When Windows runtime access returns, record the executed
   `drawObject(461)` sequence, any peer-state resets of 451, actual
   object draw queue, script scheduler tick, viewport, palette/actor state
   and independent indexed frontbuffer.
4. Accept only observed frame/timing data, not a guessed loop FPS.
   Preserve every failed or absent trace channel.

**Evidence:** archive-decoded objects, source-hashed scripts and
source-backed opcode block. **Not verified:** independent descumm
alignment, native branch reachability, selected state timings, true
scene visibility, complete indexed rendering. No game source bytes,
disassembly transcripts, original image data, binaries or captures
are committed.
