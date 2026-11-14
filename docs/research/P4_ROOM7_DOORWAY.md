# Room 7 doorway capture — 14 November 2026

Exterior frames 961 and 962 have engine ticks 961 and 1113 and SDL timestamps 97,433 and 112,635 ms. The exterior run omitted ticks 962 through 1112. Its room filter prevents attribution of any coordinate, room ID, clipping plane or script action within that interval. A new ordinary-input round trip can establish what happens on its own route. Its dwell time can differ.

## Private evidence

The earlier chat reported CRC checks and byte matches between the attachments and their F-drive counterparts. The research ZIP contained 49 Markdown files and one Room 34 event JSON. Its saved-entry document describes a separate play.zip. The mask-0972.zip report bundle contained navigation.json, 603 overlays for fresh draws with visible mask effects, and a world-route image. The original per-frame engine and presentation binaries reside separately under FIXTURE.

Work independently ran tools.analyze_room7_navigation on all 1,149 local pairs. The new work-recheck-274169e820654dbe91ae6e05bb5125ca/navigation.json in FIXTURE/REPORTS/Room7 reproduced the accepted SHA-256 772fe65fa8edbda456973de6bc31f400a6fda2b3a1843e9f13d2069a55866826. The earlier 5,518-error analysis is retained. Engine coordinates, boxes, scales and 694 plane-1 draws are runtime observations. The archive-derived compositor reused 455 poses within their respective continuous segments and matched 52,945,920 indexed front pixels. Omitting the mask produced 81,234 differences across repeated observations. The reference 1.mp4 has no shared clock with either run.

## Operator protocol

Use the installed ScummVM-P4-Doorway-20261114-b build in TOOLS (SHA-256 2fef123e96f76595d343dcfb137f1b94c8c457edbc2e809dec57a6ac411d87be). In Windows PowerShell run:

~~~powershell
& { Set-Location -LiteralPath 'F:\Dev\SCUMMBUCKET\SOURCE\ScummBucket' -ErrorAction Stop; python -B -m tools.room7_doorway --root 'F:\Dev\SCUMMBUCKET' }
~~~

From the restored bridge position, walk left along the walkway and enter the ship. Once inside, use the stairway to return. Allow Guybrush to stop outside and close the game window normally. Finish within 2,400 engine ticks and 4,800 SDL presentations. Avoid opening the debugger or game menus during the route. A new private capture directory is reserved on every launch. The launcher verifies both archives and the Room 7 save, copies the save into that directory, and directs subsequent saves there. Raw RGB frames, run metadata and logs stay under FIXTURE/CAPTURES/Room7. The report and video are written to a fresh matching FIXTURE/REPORTS/Room7 directory.

Tick rows give end-of-loop room ID, actor room, world X/Y, active box, camera X/Y, viewport origin, X/Y scale and last fresh draw in the tick. The third draw field is the selected depth plane. An empty draw field means no fresh sample. SDL records every presentation while enabled, including multiple presentations per tick. Presentation tick identifies the loop in progress or most recently started at readback. During effects its image can precede the final state of that loop. Video timestamps are SDL milliseconds relative to the first presentation. The verifier checks the return sequence, consecutive engine ticks, binary IDs and stamps, then decodes FFV1 and checks every RGB hash and timestamp. Review video and adjacent tick rows at each room change before interpreting any discontinuity as scripted relocation.

## Validation and diagnostics

A private idle smoke run of build a produced Room 7 actor and SDL records. Game-window approval timed out before navigation. At the tick limit ScummVM opened its debugger and continued producing SDL frames. The run was stopped and its partial files retained at FIXTURE/CAPTURES/Room7/doorway-118c94263cf44af9b856906a6824c0f1. Build b disables capture at the tick cap and separately bounds SDL frames. Both compiler logs remain under TOOLS, including the inherited unsigned-xstart warning and Git version lookup diagnostic in the isolated build copy. The corrected executable linked successfully. A synthetic three-frame round trip at 148, 247 and 401 ms passed full FFV1 decode, timestamp and RGB verification. Interior gameplay evidence remains pending.


## Source-script trace replay (subsequent checkpoint)

The 14 November continuous user-run doorway capture established **Room 7 -> Room 12 -> Room 7** at consecutive engine ticks, with restored positions (54,54) -> (259,58) and (265,59) -> (55,55). This closes the earlier continuous-room-coverage gap; it does **not** by itself establish the source instructions and operands that triggered the transition.

Use the existing pinned doorway build with ScummVM's built-in SCRIPTS and OPCODES channels. This is not a new custom ScummVM patch. The script-tracing launcher adds --debugflags=SCRIPTS,OPCODES and --dump-scripts; it creates a new dumps directory under a new unique private capture. It MUST NOT set --debug-channels-only: in the SCUMM engine Scumm::debugC forwards to ordinary debug(), and the latter discards every message when that option is enabled. The existing executable, save and archive hashes remain pinned by the normal launcher.

From **Windows PowerShell**:

~~~powershell
$ErrorActionPreference = 'Stop'
$repo = 'F:\Dev\SCUMMBUCKET\SOURCE\ScummBucket'
Set-Location -LiteralPath $repo
if ((git branch --show-current).Trim() -ne 'research/p4-engine-palette-trace') {
    throw 'Wrong Git branch; do not overwrite or switch a dirty checkout'
}
if ((git status --porcelain)) {
    throw 'Checkout has uncommitted changes; inspect before updating'
}
git fetch origin research/p4-engine-palette-trace
if ($LASTEXITCODE -ne 0) { throw 'Git fetch failed' }
git merge --ff-only origin/research/p4-engine-palette-trace
if ($LASTEXITCODE -ne 0) { throw 'Fast-forward failed; no forced changes' }
python -B -m tools.room7_doorway_script_trace --root 'F:\Dev\SCUMMBUCKET'
if ($LASTEXITCODE -ne 0) { throw "Script trace exited $LASTEXITCODE; preserve capture" }
~~~

**Game route:** restored Room 7 right-side bridge -> walk left into the ship -> in Room 12, walk down the stairs and back up -> return to Room 7 -> stop outside -> close ScummVM normally. Do not open the debugger, change rooms artificially, or leave the game idle until the 2,400-tick/4,800-presentation recording limit.

The launcher writes to new matching FIXTURE/CAPTURES/Room7/doorway-<uuid> and FIXTURE/REPORTS/Room7/doorway-<uuid> directories. The report includes doorway.json, doorway.mkv, script_trace.json and timestamped frames. The private capture includes ticks.tsv, presents.tsv, run.json, console.log, runtime.log and dumps (game script bytes; **do not commit or publish**). Keep all original files read-only.

script_trace.json records executed script numbers, engine opcode handler names, reported offsets, probable opcode starts and hashes of private dump files. It explicitly does not equate opcode log entries with specific engine ticks or decode opcode operands. Source-level confirmation requires matching the executed sites to the original SCUMM v5 resource bytes or disassembly, then verifying the target room/object operands. Missing opcode channel output is reported as incomplete; do not treat an automatically successful room-transition recording as script-level proof.

**Share:** ZIP the new report's script_trace.json, new capture's console.log, runtime.log, ticks.tsv, run.json, plus any error output. Preserve the dumps locally unless requested for a private inspection; never put game scripts into Git. The full video is optional because the previous doorway video has already been verified.

### 14 November diagnostic: intentionally failed opcode-channel gate

The user ran the original trace launcher from commit 86085e4. The ordinary doorway loop **passed** (291 consecutive ticks, 751 presentations). Room 7 -> Room 12 is at ticks 139/140, and Room 12 -> Room 7 at 245/246. The final report correctly returned script_opcode_debug_channel_missing; console.log contained only 229 bytes of startup text, and runtime.log only a 222-byte open/close log. The executable and dump-scripts option worked (private entry/exit and room scripts were enumerated).

**Source-backed root cause:** SCUMM engines/scumm/debugger.cpp has a legacy debugC(DEBUG_OPCODES,...) wrapper which, after checking the channel, calls ordinary debug(). common/debug.cpp suppresses ordinary debug() whenever gDebugChannelsOnly is true, as selected by --debug-channels-only in base/main.cpp. Thus the prior script-trace launch suppressed its own opcode log. The fix removes that command-line switch, retains explicit channels, and adds a regression test rejecting reintroduction of the incompatible switch.

A new run is required to obtain executed opcode sites; **no engine recompilation is necessary**. Preserve doorway-9e2a36535af54a9ca2f75a1d0be1aebb as valid navigation/video evidence, but NOT as script execution evidence. The existing raw private dumps can support disassembly research without another game run, but they do not independently prove which script paths executed. This corrected command was not yet confirmed against a fresh Windows game run at the time of this update.


### 14 November — executed doorway scripts and source operands independently verified

A subsequent user-run script-trace archive, doorway-4ecbce57669248bc816e4993b3306ca9.zip, contains 274 consecutive engine ticks, 678 timestamped presentations, 7,473 observed SCUMM v5 opcode executions over 303 unique sites, and 59 privately dumped script resource references (hashes only in the public metadata report). The fixed opcode channels produced evidence successfully after removal of --debug-channels-only. Its Room 7 -> 12 transition is ticks 139/140, with world positions (54,54) -> (259,58), plane 1 -> 2, scale 150 -> 179. Return Room 12 -> 7 is ticks 211/212, positions (265,59) -> (55,55), plane 2 -> 1, scale 180 -> 150. Those positions are observations from the engine tick recorder.

The original DOS VGA game files provided privately were independently re-read and matched the pinned MONKEY2.000 and MONKEY2.001 SHA-256 checksums. The original MONKEY2.001 resource is XOR decoded with key 0x69, LOFF room locations validated and the executed opcode sites aligned within the VERB subchunk of their respective OBCD object resources:

| Execution | Original room/object label | SCUMM opcode offset (relative to ROOM, after opcode byte) | Decoded destination | Post-entry walk destination |
| --- | --- | ---: | --- | --- |
| o5_loadRoomWithEgo at script 40 | Room 7, object 40, ship | 76330 (absolute decoded archive byte 468669 for opcode) | Room 12, object 102, stairway | (221,87) |
| o5_loadRoomWithEgo at script 102 | Room 12, object 102, stairway | 30666 (absolute decoded archive byte 941184 for opcode) | Room 7, object 40, ship | (105,77) |

For the v5 opcode 0x24, ScummVM engines/scumm/script_v5.cpp reads a direct 16-bit object number, an 8-bit room number, and two signed 16-bit walk coordinates; room.cpp startScene handles room change and object-relative entry positioning. The source-derived walk coordinates are *subsequent targets*, not the actor's first observed origin in the destination room. No per-opcode engine tick is present in the legacy debug log. These two one-time opcode executions are source-aligned and their order agrees with the two consecutively logged room transitions, but exact intra-tick timing or additional entry-script side effects cannot be assigned without further instrumentation.

Independent FFV1 decoding of all 678 uploaded video frames reproduced every exported RGB PNG's raw pixel hash and the decoded framehash record. All 678 presentation timestamps matched doorway.json. The original present-*.bin buffers were not included in this new upload and remain outside this independent audit. No private script dumps or original game resource bytes were committed to SOURCE.

The independent, read-only source audit can be reproduced with the metadata-only verifier supplied alongside the private chat evidence. This establishes the two transition opcode operands; further gameplay replay is not necessary to identify these specific source-level targets. Any further inquiry into entry-script positioning would require a separate narrower question and trace.
