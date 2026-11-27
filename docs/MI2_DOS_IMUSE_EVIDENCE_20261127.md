# MI2 DOS VGA iMUSE — evidence checkpoint, 27 Nov 2026

## Objective
Understand original 1991 DOS VGA Monkey Island 2 MIDI/iMUSE. The Special Edition banks are clues, not substitutes for DOS sequencer events. Preserve native music assets; do not build a game interpreter.

## Evidence classes
- **S** ScummVM source-confirmed, not necessarily original DOS binary behavior.
- **SE** User-verified Special Edition bank/recording evidence, not DOS MIDI.
- **D** Directly read original DOS resource bytes. **No new D evidence this session**: supplied ZIP could not be inspected.
- **H** Hypothesis requiring original archive/script/trace verification.

## Source-confirmed findings (S)

1. **Device renditions:** ScummVM readSoundResource inspects a SOU container and selects nested ADL, ROL, SPK, SBL etc. according to audio hardware. A faithful extractor must **inventory and preserve all available valid renditions** rather than selecting only ScummVM's preferred playback rendition. Do not presume all renditions exist for every sound ID.
https://github.com/scummvm/scummvm/blob/master/engines/scumm/sound.cpp

2. **MIDI player:** ScummVM Player::start_seq_sound uses findStartOfSound, a Standard MIDI File parser for the usual case, smart jumps, and MDhd for startup parameters. Preserve MThd, MTrk, MDhd and original SysEx and control bytes, not just MIDI note events.
https://github.com/scummvm/scummvm/blob/master/engines/scumm/imuse/imuse_player.cpp

3. **SysEx handlers:** sysex_scumm.cpp handles codes 48 conditional jump-hook; 49 global transpose; 50 part on/off; 51 part volume; 52 program; 53 part transpose; 64 marker; 80 loop; 81 end loop; 96 instrument. These are recognized handlers in ScummVM, **not yet observed event counts in DOS assets**.
https://github.com/scummvm/scummvm/blob/master/engines/scumm/imuse/sysex_scumm.cpp

4. **Game script to jump:** script_v5.cpp o5_soundKludge -> Sound::soundKludge -> Sound::processSoundQueues -> IMuseInternal::doCommand_internal handles setHook, marker queues and loop/jump commands. IMuseInternal::handle_marker triggers queued commands on matching sound/marker IDs. Player::maybe_jump checks an armed hook before jumping to track, beat and tick. This is a verifiable path for a Woodtick transition.
https://github.com/scummvm/scummvm/blob/master/engines/scumm/script_v5.cpp
https://github.com/scummvm/scummvm/blob/master/engines/scumm/sound.cpp
https://github.com/scummvm/scummvm/blob/master/engines/scumm/imuse/imuse.cpp
https://github.com/scummvm/scummvm/blob/master/engines/scumm/imuse/imuse_player.cpp

5. **MI2-specific numeric crosscheck:** script_v5.cpp o5_startSound includes an MI2 workaround describing sound 103 while Largo talks to the bartender, and 110 while Largo talks to Mad Marty. These partially corroborate location-related sound IDs in the user's remaster list, but do **not** prove MIDI resource identity or a complete original transition.

## Special Edition: clues, not source of DOS timing

(SE) User's original-style remaster cue inventory identifies 101 Woodtick (Original XWB stream 2), 103 Bar (3), 104 Wally/Cartographer (4), 110 Laundry (5 selected; additional distinct 185), 111 Carpenter/Woodshop (14), 152 Inn (6 selected; additional distinct 266), 162 Jojo (48). These are **recorded audio**, not MIDI event streams. The synthetic 4:07.730 suite used a 3.539s bar grid and manually applied crossfades; its timing does **not** demonstrate DOS hook positions.

In a 2010 interview music supervisor Jesse Harlin confirms that original MI2 was MIDI-driven, the Special Edition used a different digital system with beat sync, crossfades, markers and layers, and that some musical material was combined or reduced. Therefore, remaster transition suffixes such as _T may suggest musical relatives but do not establish one-to-one original DOS transition mappings.
https://www.audiogang.org/interview-with-lucasarts-jesse-harlin/

## Only two next checkpoints

### Checkpoint 1 — Native DOS SOUN inventory, read-only
From the original DOS VGA edition and ScummBucket's existing archive reader, inspect **candidate** sound IDs 101, 103, 104, 110, 111 and 152. For each, record game file hash, archive offset/length, resource ID, nested rendition tags/offsets/sizes/hashes and MThd/MTrk/MDhd where present. Preserve all original bytes; do not conflate AdLib, MT-32, PC speaker and digitized sound. Mark missing/unsupported cases explicitly. Do not assume SE IDs are confirmed in the DOS archive.

**Acceptance:** At least two byte-validated DOS sounds and per-device variations with accurate provenance. No copyrighted resources in Git.

### Checkpoint 2 — One Woodtick iMUSE event/transition trace
Without synthesis, decode original MIDI delta-times, tempo, PPQN, SysEx 48–53, 64, 80–81, 96, markers and loops to an event JSON with absolute ticks and hook operands. Where the archive and scripts permit, correlate a game sound/command -> MIDI hook/marker -> chosen jump target; distinguish static candidates from observed runtime selection. Compare SE cue names as optional annotation, never as proof of original hook ID.

**Acceptance:** One chain from original game script sound/hook action through a native sound resource to its matching MIDI conditional transition or marker, with unknowns documented. No full interpreter, no automated composition, no broad research sessions.

## Scope and status
This is a research checkpoint, not implemented or tested extraction. ZIP inspection was attempted but current runtime could not read the archive. ScummBucket remains focused on native extraction; BigR is not a dependency. All game data, outputs and reports belong under FIXTURE; third-party software under TOOLS; code and this document in SOURCE. Preserve original archives and existing files.
