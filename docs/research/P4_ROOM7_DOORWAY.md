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
