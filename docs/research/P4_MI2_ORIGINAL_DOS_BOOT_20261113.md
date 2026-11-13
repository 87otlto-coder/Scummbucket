# MI2 original DOS VGA — standardized interactive startup protocol

**13 November 2026. Status: operator-observed startup sequence, not yet a completed
Room 7 DOS save-load capture.**

This protocol applies to **every integration or visual fidelity test that starts
the original `MONKEY2.EXE` through a DOS emulator**. It is **not** a requirement
for synthetic Python unit tests, archive parsers or the separate instrumented
ScummVM saved-entry capture route. Record which route was used in every report.
A successful archive/image test does not imply that the executable was booted.

## Why the protocol is mandatory

The original DOS game may display a copy-protection recipe prompt before
difficulty selection and before the in-game load menu becomes available.
The operator has observed that entering `0` repeatedly gets through this
prompt with their edition. Treat this as **edition-specific observed behavior**,
not an assumption about all releases. A KIXX edition manual indicates that
any four digits may be accepted, but this does not prove every DOS edition
will respond identically. The normal game's difficulty selection follows.
The original game's F5 interface provides Save/Load operations.

**Do not use** `tools.run_room23_frames --native-room7-save` to open the
uploaded `SAVEGAME.001`. That launcher is ScummVM-specific and now explicitly
requires an `SCVM` header; the original DOS saved game has no such header.

## Reusable interactive boot sequence for a test agent

1. **Identify and preserve input:** check the DOS VGA game's original
   `MONKEY2.000`, `MONKEY2.001`, `MONKEY2.EXE` and `SAVEGAME.001`;
   fingerprint before the run and preserve original bytes. Launch the game
   from a **fresh, non-overwriting working copy** placed somewhere under
   `F:\Dev\SCUMMBUCKET\FIXTURE`. An emulator or DOSBox installation is an
   external tool and belongs under `TOOLS` unless installed system-wide.
2. **Wait for the copy-protection prompt.** Only when visibly present,
   enter zeros into the requested recipe input(s) and submit. Do not hold
   `0` down blindly after the screen transitions. Use a bounded number of
   attempts; if the prompt persists, **stop and record the blocker** instead
   of guessing a result. Record what was actually entered and whether the
   screen advanced; never claim the behavior was universal.
3. **Wait for difficulty selection.** Explicitly choose and log the selected
   difficulty (`easy/lite` or `hard`, as labeled by this game edition).
   Do not assume a default. If the screen is skipped, record that explicitly.
4. **Open the original in-game Load menu.** The game's original manual
   identifies **F5** for its Save/Load interface. Choose **Load**, select
   the intended DOS `SAVEGAME.001` entry, and confirm gameplay resumes.
   A loaded save may restore its own difficulty: distinguish the boot-menu
   selection from the actual loaded state.
5. **Confirm the room, not the filename.** Capture a screenshot/video plus,
   if independently available, the runtime room ID. A room can be called
   **Room 7 engine-verified** only when the runtime room ID is observed.
   A matching screenshot without runtime instrumentation is **visually
   consistent with Room 7**, not a verified numeric room ID.
6. **Begin the experiment only after the load.** For each independent
   DOS gameplay test run, repeat or explicitly document this complete
   startup sequence; capture the post-load state and record the input
   file hashes, difficulty, UI steps, emulator/version, observed entry
   path, caveats and output hashes.

**Fail closed:** missing prompt confirmation, uncertain difficulty, failed
save load, unknown room, or absent evidence must be reported as partial or
blocked. Do not relabel the old debugger-driven 87-frame capture as a natural
gameplay route.

## Uploaded private-save observation

The `SAVEGAME.001` supplied on 13 November 2026 has **37,908 bytes**,
SHA-256 `b2864c0301004f7e72489f2acb54e9c9dba51276520956bc171ed9a4263e6795`.
It is byte-identical to `mi2/SAVEGAME.001` in the user's `mi2.zip`.
Its first four bytes are `31 32 33 00` (`123\0`), not ScummVM's
`53 43 56 4d` (`SCVM`). These facts establish source identity and
save-format incompatibility with the ScummVM launcher. **The actual saved
room remains unverified**: do not infer it from `SAVEGAME.001` or those
first four bytes.

## Evidence boundaries

Only derived hashes, descriptive steps and diagnostic reports belong in
`SOURCE/ScummBucket/docs`. Original DOS/ScummVM saves, screenshots,
engine traces and any generated previews remain in `FIXTURE`, outside
Git. Never overwrite or relocate existing saves/captures.

The original DOS bootstrap is a **separate test path** from the pinned
`87×320×144` ScummVM indexed Room 7 verification. To compare the DOS
save scene to those ScummVM traces, first observe the room in DOSBox,
then separately capture equivalent in-engine state with supported
instrumentation. No automatic save conversion is implemented.
