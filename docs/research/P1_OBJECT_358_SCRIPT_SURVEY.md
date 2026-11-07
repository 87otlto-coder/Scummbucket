# P1 — Room 34, Object 358: Script-Pattern Evidence Register

**Status:** Original 17 byte patterns now **independently confirmed as instruction starts**; subsequent instruction-level behavior analysis completed, but **gameplay execution and animation timing remain unverified**  
**Date:** 2026-11-07  
**Scope:** Specific user-supplied original DOS Monkey Island 2 resource pair only

## 1. Source identity

- `MONKEY2.000` SHA-256: `cde7aa8980317e3a750fbb3b49884cdddaf1ff3d4231a0c840b22cceed9033f1`
- `MONKEY2.001` SHA-256: `ad045372e0d49626503bb50fca29a687ec8e01ef75d9b8bca702a366d143819e`
- File-level byte transform: XOR `0x69` (as independently observed and documented in P0).
- All source offsets in this document are **zero-based byte offsets in XOR-decoded `MONKEY2.001`**; the same offsets apply to stored file slices, but bytes differ by XOR.

The game archives and extracted resources are **not** stored in GitHub.

## 2. Verified resource relationships

- Room ID **34**: `ROOM` starts at decoded `MONKEY2.001` offset **2,690,237**.
- Object **358**: `OBIM` offset **2,718,583**, length **21,960** bytes; `IMHD` declares **16** states (`IM01` through `IM10`).
- Object **358**: matching `OBCD` offset **2,740,543**, length **47** bytes; `CDHD` contains matching object ID 358.
- The room contains **7 `LSCR` chunks** plus `ENCD` and `EXCD` (9 local script chunks total).
- Local script **201**: `LSCR` offset **2,740,982**, chunk length **5,050** bytes.
- Local script **202**: `LSCR` offset **2,746,032**, chunk length **1,107** bytes.
- The other two room objects are IDs 356 and 357.

Object identity, image state count, script source offsets and SCUMM chunk boundaries have been structurally validated. No original images were rendered.

## 3. Candidate state-related script bytes

The `script_candidates.py` module compares raw script payload windows against the **direct-object** forms of SCUMM v5 `drawObject` (opcode family `05/45/85/C5`) and `setState` (`07/47/87/C7`). Variable **object-ID** variants `85/C5/87/C7` are explicitly **not** interpreted as literal object IDs. The scanner handles direct-object variants and distinguishes literal-state values from variable-state operands.

Across room 34, **17 matches for object 358** occur in local scripts 201 and 202:

| Script | drawObject patterns | setState patterns | Total |
| --- | ---: | ---: | ---: |
| 201 | 7 | 4 | 11 |
| 202 | 4 | 2 | 6 |
| **Total** | **11** | **6** | **17** |

Of the 11 draw patterns, **4** have a variable-reference state operand (raw reference 100); **7** have a literal state value 1. All 6 set-state patterns have literal value 0.

Selected reproducible byte windows:

| Offset (decimal) | Script | Hex bytes | Candidate interpretation |
| ---: | ---: | --- | --- |
| 2,742,765 | 201 | `05 66 01 02 01 00` | drawObject(358, state 1) |
| 2,742,844 | 201 | `05 66 01 82 64 00` | drawObject(358, state **variable reference 100**) |
| 2,744,442 | 201 | `07 66 01 00` | setState(358, state 0) |
| 2,746,412 | 202 | `05 66 01 02 01 00` | drawObject(358, state 1) |
| 2,746,455 | 202 | `05 66 01 82 64 00` | drawObject(358, state **variable reference 100**) |
| 2,746,838 | 202 | `07 66 01 00` | setState(358, state 0) |

The same room contains additional candidate matches targeting object 357; they must not be confused with object 358.

### Critical evidence qualification

**Historical scanner limitation:** The original byte-wise scanner did not know instruction boundaries and correctly marked all matches `instruction_alignment_verified=false`. That limitation still applies to **new unverified byte patterns**. However, **all 17 object-358 matches were subsequently independently corroborated by a real external `descumm` run** (section 6).

**New analysis:** The full user-supplied disassembly reports establish a scripted password/number demonstration. State selection is `min(15, 3*n-1+r)` for selected number `n=1..5` and random `r=0..2`; see [the source-backed behavior analysis](P1_ROOM34_OBJECT_BEHAVIOR.md) and [machine-readable 17-event register](P1_ROOM34_OBJECT_EVENTS.json). That is script-level evidence, **not** recorded gameplay.

Do not overwrite the scanner's **raw** evidence flag as though its byte-pattern scan had become a disassembler. Preserve each verification method and its level of evidence separately. Gameplay execution, frame timing and image appearances remain unverified.

## 4. Reference implementations and licensing

- [ScummVM `engines/scumm/script_v5.cpp`](https://github.com/scummvm/scummvm/blob/master/engines/scumm/script_v5.cpp): `setupOpcodes()`, `o5_drawObject()`, `o5_setState()`, and `getVarOrDirectWord()`.
- [ScummVM Tools `engines/scumm/descumm-tool.cpp`](https://github.com/scummvm/scummvm-tools/blob/master/engines/scumm/descumm-tool.cpp): supports the `-5` SCUMM v5 script option and `LSCR` header handling.
- [ScummVM Tools `engines/scumm/descumm.cpp`](https://github.com/scummvm/scummvm-tools/blob/master/engines/scumm/descumm.cpp): established SCUMM v2–v5 script disassembler, suitable as a **separately sourced reference** for checking actual instruction boundaries.

**Licensing:** The ScummVM Tools descumm sources declare GNU GPL version 3 or later. Do **not** copy or embed their code into ScummBucket without an explicit license and architecture decision. Running a separately installed GPL tool against locally owned game resources for comparison is a promising research workflow.

## 5. Evidence labels and unresolved questions

| Item | Status | Follow-up |
| --- | --- | --- |
| Object 358 has 16 stored image states | **Directly observed** | Decode state images in P2/P4 |
| OBIM and OBCD match object ID 358 | **Directly observed** | Preserve paired positions |
| Scripts 201/202 include 17 direct-object state-operation instructions | **17 instruction starts confirmed** by independent `descumm` | Preserve offsets and external evidence |
| Four `drawObject` instructions select temporary `Var[100]` | **Verified from disassembly** | Compare images and runtime variable values |
| State formula `min(15, 3*n-1+r)` | **Disassembled**, ScummVM RNG range independently checked | Verify visual output and runtime |
| These instructions execute in real gameplay | **Not yet observed** | Trace gameplay branches and callbacks |
| Object 358 cycles autonomously | **Not demonstrated**; interaction-driven script context identified | Seek genuine autonomous room animations elsewhere |
| Animation frame order and elapsed timing | **Not established** | Instrument executed state changes and renderer |

## 6. Independent instruction-offset comparison (available in ScummBucket)

**Implementation status:** A `verify-descumm` command has been added to the P1 feature branch. It exports only the selected original `LSCR` chunk to an OS temporary directory, invokes the **separately installed** ScummVM Tools `descumm` executable with `-5 -o -h`, and compares emitted instruction start offsets and opcode bytes to our existing candidates. It deletes the temporary script after the process exits and does not commit proprietary data.

**Real disassembler run status: COMPLETED BY USER ON WINDOWS (2026-11-07).** The user ran the official ScummVM Tools `descumm.exe` against the original game archive via ScummBucket's `verify-descumm` adapter and supplied screenshots of both terminal results. The research environment itself did not execute that external binary; our evidence for its successful execution is the supplied output, not the mocked CI tests.

| Local script | Candidates checked | Confirmed opcode starts | Not emitted | Opcode conflicts | Adapter result |
| --- | ---: | ---: | ---: | ---: | --- |
| 201 | 11 | 11 | 0 | 0 | `success` |
| 202 | 6 | 6 | 0 | 0 | `success` |
| **Total** | **17** | **17** | **0** | **0** | **All matched** |

**Evidence scope:** Each positive match establishes that `descumm` emitted the expected **opcode at the same script-body instruction offset** as the existing direct-object byte pattern. It supports instruction-boundary alignment. The adapter does not yet compare full decoded operand semantics with the disassembler's human-readable output and cannot establish whether a branch executes, how frequently it executes, or any animation frame timing. The script's structure and image-state relationships remain separate from observed gameplay.

The four `CYCLE_FLAGS_UNVERIFIED` warnings seen in both screenshots originated from the whole-archive palette-cycle inspection and are not caused by these local scripts. They remain open diagnostic findings.

The original private script chunks were separately rechecked by SHA-256, without committing them:

| Local script | `LSCR` source offset | Chunk size | XOR-decoded chunk SHA-256 |
| --- | ---: | ---: | --- |
| 201 | 2,740,982 | 5,050 bytes | `3dd3377827386229962e9aae8d681426115ad228efe1ecf36d7469154d1fbc09` |
| 202 | 2,746,032 | 1,107 bytes | `1bb2578f20c0aad5146995f7d40b5cfdd0fe6b5c25a65faaffeddb5f12c82ee9` |

On Windows, download **ScummVM Tools for Windows** from https://www.scummvm.org/en/downloads/ (the tools package, not just the game runner), and extract it into a folder outside the source checkout, for example `C:\Users\87otl\Tools\scummvm-tools`. Find the `descumm.exe` executable, then run:

```powershell
cd "C:\Users\87otl\ScummBucket"
git pull --ff-only origin feature/p1-scumm-v5-inventory

$descumm = (Get-ChildItem "C:\Users\87otl\Tools\scummvm-tools" -Recurse -Filter descumm.exe -File | Select-Object -First 1).FullName

python -m scummbucket verify-descumm "D:\old" --room 34 --script 201 --object 358 --descumm "$descumm"
python -m scummbucket verify-descumm "D:\old" --room 34 --script 202 --object 358 --descumm "$descumm"
```

The `D:\old` input is the original-game directory confirmed working in this user's local session. The full path to the executable is user-configurable; no game archives or binaries are embedded into the application.

**Interpretation rules:**

- `confirmed_opcode_start`: `descumm` emitted the expected opcode at that exact script-body offset. This supports **instruction alignment only**.
- `not_emitted`: no matching offset appeared in the disassembler output. This is **inconclusive**, not automatically a false positive; output may suppress or restructure lines.
- `opcode_conflict`: the disassembler emitted a different opcode at the same offset. This is an error and must be investigated.
- Nonzero disassembler exits, missing executable, malformed output, timeouts, duplicate emitted offsets, and source-hash mismatches are explicitly reported as failures.

**None** of these statuses proves that the script branch executes in-game, that the object cycles automatically, or what its animation timing would be.

### Reproducing this result as a private integration regression

Two opt-in regression tests are available in the repository: the existing archive inventory test, and the new real-disassembler integration test `tests/test_private_descumm.py`. Both skip in CI unless given the user's private inputs. To run both on the Windows workstation (without committing any copyrighted resources):

```powershell
cd "C:\Users\87otl\ScummBucket"
git pull --ff-only origin feature/p1-scumm-v5-inventory
$env:SCUMMBUCKET_MI2_ARCHIVE = "D:\old"
$env:SCUMMBUCKET_DESCUMM = "C:\Users\87otl\Tools\scummvm-tools\descumm.exe"
python -m unittest discover -s tests -v
Remove-Item Env:\SCUMMBUCKET_MI2_ARCHIVE
Remove-Item Env:\SCUMMBUCKET_DESCUMM
```

Do not interpret an optional test skipped because its inputs were absent as an executed verification.

## 7. Next experiment / exit criteria

1. **Completed:** An independently installed `descumm` corroborated all 17 opcode starts for object 358 in scripts 201 and 202, as evidenced by the user-supplied Windows output. This does not imply runtime execution.
2. **Completed:** Examined the two complete user-supplied `descumm` reports. Documented the number/state selection formula, dialogue and cutscene branches, script-level delays, and object 357's distinct placement/reset references. See [behavior analysis](P1_ROOM34_OBJECT_BEHAVIOR.md) and [event metadata](P1_ROOM34_OBJECT_EVENTS.json).
3. **Next:** Decode and visually verify object 358 image states, including state 0 and whether image 16 is ever displayed.
4. **Next:** Trace which branches execute during actual gameplay using ScummVM instrumented observation; measure state transitions in engine ticks and wall-clock time. Do not infer frame duration from `breakHere` or `WaitForMessage` alone.
5. Investigate scripts 25/26 and object 357 separately; a shared cutscene does not establish synchronized environmental animation.
6. Identify and verify a genuinely continuous background-animation example for P4, rather than treating this puzzle object's interactive states as automatic looping.
7. Preserve all four evidence levels: *raw bytes*, *disassembled instructions*, *executed behavior*, and *reconstructed animation*. Keep palette-cycle warnings visible and independently unresolved.

**P1 remains incomplete. This is evidence-gathering in support of P4, not completed animation reconstruction.**
