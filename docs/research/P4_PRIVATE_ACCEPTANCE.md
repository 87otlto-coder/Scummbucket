# Windows private P4 acceptance gate

The public Windows CI suite intentionally does **not** upload, read, or reproduce private original-game captures. This local runner is the last evidence gate for [draft PR #8](https://github.com/87otlto-coder/Scummbucket/pull/8).

The script lives in `SOURCE/ScummBucket/tools/p4_private_acceptance.ps1`. The canonical machine layout remains exactly three top-level folders: `SOURCE`, `TOOLS` and `FIXTURE`.

## Preconditions

- The F-drive checkout must be on `research/p4-engine-palette-trace`, have no local modifications, and match its **previously fetched** `origin` tracking ref. This script does **not** fetch or fast-forward your checkout.
- The pinned `FIXTURE/GAMES/MonkeyIsland2_DOS_VGA/MONKEY2.000` and `.001` archive hashes must match the existing Room 7 preflight; original archives remain read-only.
- The 87 paired Room 7 engine/presentation captures, sweep JSON report, 784×144 panorama/ZP01 and two Room 23 walk-capture directories must be present in the existing F-drive locations. If the Work session's output is still in a separate desktop `FIXTURE`, do not blindly move/overwrite it; verify and use a separate approved copy or update the workspace deliberately.
- Python 3.10+, Pillow and Git must be installed.

## Run

Open PowerShell from **any** directory:

~~~powershell
$script = 'F:\Dev\SCUMMBUCKET\SOURCE\ScummBucket\tools\p4_private_acceptance.ps1'
& $script
~~~

This default command performs a **read-only** preflight, hashes all 87 captured engine buffers and prints missing evidence or checkout differences. It never changes the game archives, repository or output tree.

After resolving all preflight diagnostics, run:

~~~powershell
& $script -Full -OpenPreview
~~~

`-Full` sets private fixture environment variables only for the duration of the run, executes the repository's unit and available private tests, then uses `tools.verify_room7_scene` to reconstruct the complete 87-frame pinned scene into **a fresh timestamped directory** under `FIXTURE/OUTPUT/Room7`. The output cannot overwrite an earlier run. It checks 87 PNGs, zero indexed mismatches, the documented negative-control count (778) and a self-contained HTML file containing PNG data URLs. The produced manifest records each frame's data and archive/capture dependencies.

`-OpenPreview` opens that new HTML file using the Windows file association. **The user must confirm the animation actually plays in the browser**; launching the file is not evidence that all frames rendered.

## Failure and evidence handling

A dirty/diverged checkout, missing fixture, archive hash mismatch, failed regression, changed output hash, or missing embedded frame fails with an explicit error. A partially written timestamped output is retained as diagnostic evidence and never labeled successful. Only the user may approve deleting redundant outputs. The runner never calls `git fetch`, `git reset`, `git push` or deletes a fixture.

Hosted Windows GitHub Actions executes only `-CheckSyntax` to verify PowerShell loading without private files. It cannot attest to game-capture fidelity. This acceptance remains pinned to the **debugger-equivalent 23→7 entry**; natural gameplay entry and other SCUMM editions remain untested.

Do not commit generated HTML, screenshot frames, archives or local captures. Share only derived hashes and test summaries as appropriate.
