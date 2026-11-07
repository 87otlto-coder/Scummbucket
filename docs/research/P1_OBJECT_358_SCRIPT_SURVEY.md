# P1 — Room 34, Object 358: Script-Pattern Evidence Register

**Status:** Reproducible byte-pattern investigation; **not** verified script disassembly or animation timing  
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

**These are byte-pattern matches, not verified instruction boundaries.** The scanner does not know whether a byte falls in executable code, an instruction operand, a text string, or unreachable code. The matches are consistent with ScummVM's operand encodings but **do not yet demonstrate that these are executable instructions**.

They do not establish a runtime animation, automatic cycling, state order, frame duration, or the triggering gameplay conditions. Script execution and variable 100's actual value remain unverified.

Every machine-readable candidate includes `instruction_alignment_verified=false`, `runtime_execution_verified=false`, and `script_control_verified=false`. Do not promote these flags without a separate test.

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
| Script 201 and 202 carry matching opcode-like windows | **Directly observed bytes**, interpretation provisional | Disassemble with correct alignment |
| Some windows resemble variable-driven draw-state changes | **Provisional** | Identify variable 100 semantics |
| These windows are valid, reachable script instructions | **Not established** | Compare against descumm / script CFG |
| Object 358 animates automatically in game | **Not established** | Observe ScummVM gameplay and timing |
| Animation frames/state order/delays | **Not established** | Instrument verified codepath and renderer |

## 6. Independent instruction-offset comparison (available in ScummBucket)

**Implementation status:** A `verify-descumm` command has been added to the P1 feature branch. It exports only the selected original `LSCR` chunk to an OS temporary directory, invokes the **separately installed** ScummVM Tools `descumm` executable with `-5 -o -h`, and compares emitted instruction start offsets and opcode bytes to our existing candidates. It deletes the temporary script after the process exits and does not commit proprietary data.

**Real disassembler run status: NOT YET PERFORMED.** The research environment did not have `descumm` installed. Unit tests mock its output to verify the matching and error-reporting logic; they are not evidence that an actual source instruction has been independently disassembled.

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

## 7. Next experiment / exit criteria

1. Use an established SCUMM v5 disassembler (prefer independently installed ScummVM Tools `descumm`) on **private, extracted** `LSCR` 201 and 202 bytes.
2. Compare decoded **instruction start offsets** against the 17 recorded byte-pattern offsets. Record confirmed instruction starts, inconclusive/unemitted candidates, opcode conflicts, and undecoded sections with diagnostics.
3. Determine whether variable 100 is used to select image state in an executable branch. Do not infer loop timing from a literal code sequence.
4. Use observed gameplay or instrumented ScummVM rendering to establish any actual animation frame/timing behavior.
5. Preserve source offsets, script IDs and the distinction between *observed raw bytes*, *disassembled code*, *executed behavior*, and *reconstructed animation*.

**P1 remains incomplete. This is evidence-gathering in support of P4, not completed animation reconstruction.**
