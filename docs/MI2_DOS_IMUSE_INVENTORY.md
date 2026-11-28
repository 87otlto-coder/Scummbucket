# MI2 DOS VGA music inventory and Woodtick-to-Bar handoff

This checkpoint continues the [original DOS iMUSE evidence note](https://github.com/87otlto-coder/Scummbucket/blob/09216e2aad8ffed115e853c42cc1828aac06029d/docs/MI2_DOS_IMUSE_EVIDENCE_20261127.md).
Use the supplied MI2 fixture. The ZIP's pre-existing MIDI sample and save were excluded from archive analysis. MI1 is unnecessary for this validation.

## Reproduce on Windows

```powershell
Set-Location F:\Dev\SCUMMBUCKET\SOURCE\ScummBucket
python -m unittest discover -s tools -p test_mi2_dos_music.py
python tools/mi2_dos_music.py ../../FIXTURE/mi2.zip "../../FIXTURE/OUTPUT/MI2_DOS_$([guid]::NewGuid().ToString('N'))" --export 1 62 101 103 104 110 111 151 152 162 --woodtick-trace
```

The music branch does not carry the existing P1 Python package. The tool exposes a standalone entry point and uses the same DSOU/LOFF addressing as the P1 inspector. When the branches converge, consolidate the archive layer with that inspector. The tool opens the supplied ZIP or an already extracted game directory read-only and requires a new output directory. It writes inventory JSON and an archive-wide SysEx/marker map. Selected IDs get their complete XOR-decoded SOUN, each rendition chunk, and the original contiguous MThd/MTrk bytes with full event JSON where valid. Re-applying the XOR mask yields the corresponding encrypted bytes. Only keep the outputs in private FIXTURE storage.

## Archive-confirmed

- MONKEY2.000 SHA-256: cde7aa8980317e3a750fbb3b49884cdddaf1ff3d4231a0c840b22cceed9033f1
- MONKEY2.001 SHA-256: ad045372e0d49626503bb50fca29a687ec8e01ef75d9b8bca702a366d143819e
- DSOU has 254 slots. 199 resolve to SOUN and 55 are empty. 195 sounds contain at least one MIDI rendition. All 336 MIDI renditions have SMF format 2, with independent tracks, and a parsed terminal end-of-track event on each track.
- SOUN lengths include the header. SOU and its device chunks declare payload lengths. A bounded recovery handles sounds 1 and 62, whose zero-length SOU wrappers are immediately followed by a complete ADL chunk. Playback selection for these two entries remains unverified.
- 142 ROL (Roland MT-32) and 194 ADL (AdLib FM) renditions hold MDhd metadata and MIDI sequences. 65 SPK and eight SBL entries were preserved as native data. SBL entries have AUhd data and are distinct from the ADL MIDI rendition.
- Archive-wide manufacturer 0x7D counts are 3,523 jump hooks, 858 markers, 476 part-on hooks, 26 global transpose hooks, 20 volume hooks, 15 program hooks, 10 loop instructions and six part transpose hooks. The sample includes 0, 1, 2, 16 and 17. Opcodes 81 and 96 have ScummVM handlers and no archive occurrence in these parsed streams. One opcode 0 event had an unrecognized operand layout and retains its original bytes.
- For format 2, time is calculated independently per track from the MIDI tempo map. These times describe traversal of the raw sequence before runtime jumps, loops, speed changes, or queues. Ordinary SMF players can play supported notes, but require iMUSE semantics and the other resources for adaptive timing.

All offsets below are zero-based within MONKEY2.001. Full per-chunk hashes and tempo details are in the generated inventory.

| Sound | SOUN offset | SOUN bytes | Renditions | Tracks per MIDI rendition |
| --- | ---: | ---: | --- | ---: |
| 101 Woodtick | 475994 | 30016 | ROL, ADL | 7 |
| 103 Bar | 706650 | 16469 | ROL, ADL | 11 |
| 104 Wally | 635649 | 18034 | ROL, ADL | 13 |
| 110 Laundromat | 1170081 | 23459 | ROL, ADL | 11 |
| 111 Carpenter | 1278139 | 21717 | ROL, ADL | 11 |
| 151 Largo | 506479 | 43520 | ROL, ADL, SPK | 9 |
| 152 Inn | 943438 | 19722 | ROL, ADL | 11 |
| 162 Jojo | 723325 | 21707 | ROL, ADL, SPK | 1 |

## Woodtick to the Bloody Lip Bar

**Archive and ScummVM source, static reconstruction.** The trace assumes sound 101 track 0 is active and gives one explicit phase and script variable value. Track numbers are zero-based.

1. The default verb of Woodtick hatch object 42 starts room 7 local script 200. That script calls global script 96 with (7, 9) at 470748 and then executes loadRoomWithEgo for room 9. Local script 201 at 470866 also requests the music route (7, 9) before a room 11 load.
2. Global script 96 is SCRP at 475099, 886 bytes. At 475255 it registers trigger (101, marker 0). At 475279 it queues jump (101, track from variable 100, beat 4, tick 400), and at 475299 it closes that command group. The next trigger, at 475307, waits for (101, marker 1). The room-9 branch queues stop 103 and start 103 at 475801 and 475812, and closes the group at 475971.
3. Example: the queue is ready before Woodtick track 0's marker 0 at tick 3760, with variable 100 resolving to transition track 1. The script sets variable 100 to one plus a random value from zero through four, so this path selects among tracks 1–5. ScummVM's jump formula gives tick 1840. Transition track 1 reaches marker 1 at tick 1920. The queue then starts Bar sound 103 at track 0 tick 0. The two triggers make the handoff wait for authored musical positions. The 80 ticks are the distance from that example's jump target to its outgoing marker.
4. With the Bar exit hook unarmed, Bar track 0's unconditional opcode-48 hook 0 at tick 40140 returns to track 0 tick 1740. The separate conditional exit hook 1 can redirect track 0 to one of tracks 1–10. For example, its event at tick 3760 targets track 1 tick 1840. Bar and Laundromat have the same marker/jump schedule on track 0 in both hardware renditions. The opening Woodtick-to-Bar path above uses a queued jump and two markers. Hook 1 belongs to a prospective Bar exit.
5. The Largo interruption is a separate case. Room 14 local script 205 arms jump hook 1 on sound 151 and later requests sound 110. Both 151 renditions define a 1,000-repeat loop from tick 31840 back to 1160, and phase-dependent hook 1 exits. ScummVM's startSound workaround for 103 and 110 waits while 151 is active. No specific Largo exit phase was observed.

ScummVM reference points in the installed CrossRoom source tree are `script_v5.cpp` lines 2806–2831, 2875–2879, 2892–2898 and 3430–3442; `sound.cpp` lines 151–185, 996–1014 and 1280–1393; `imuse/imuse.cpp` lines 782–824, 898–1017, 1054–1075 and 1177–1202; `imuse/imuse_player.cpp` lines 230–250, 494–503 and 649–679; and `imuse/sysex_scumm.cpp` lines 153–224. Confirmed the current upstream SysEx handler against the repository file as well.

Runtime observation remains outstanding. The generated trace checks actual script operands, the script hash and both renditions' relevant events. It fixes the phase and selected transition track for reproducibility. It neither emulates script scheduling nor measures mixer output. A narrowly scoped runtime follow-up can load a native room 7 save and use the regular doorway, with the iMUSE debug channel for commands and a marker/jump trace for the actual phase and track selected.

## Special Edition correlation

The matching candidate IDs and common MIDI tempo of 442477 microseconds per quarter make the SE bank cue labels useful starting points. At 4/4 that is 1.769908 seconds per MIDI measure, or 3.539816 seconds across two measures. The prior SE suite grid of 3.539 seconds is close to that two-measure duration. This is a tempo clue. The creative pickup offsets cannot recover the selected DOS jump phase, queue state, or transition track. A one-to-one correlation of an SE transition recording to an original DOS MIDI section is still open. The first useful comparison is phrase or onset alignment against separately auditioned DOS transition tracks, followed by runtime confirmation.

The loose fixture pair matches both ZIP member hashes. Three synthetic tests cover sizes, malformed MIDI, tempo, running status, hooks, markers, loops, byte retention and no-overwrite. The supplied archive run independently compared 48 exported SOUN/rendition/MIDI files to their original decoded archive ranges and checked that selected track event bytes concatenate to the exact MTrk payloads.
