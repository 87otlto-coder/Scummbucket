# MI2 Room 55 — entry-to-helper script call graph (2026-11-16)

**Research-only source bytes.** This is a cross-resource, script-caller *candidate graph*, NOT observed runtime call execution. Original DOS VGA input `MONKEY2.001` stored-byte SHA-256 `ad045372e0d49626503bb50fca29a687ec8e01ef75d9b8bca702a366d143819e`. The exact short ENCD body is instruction-aligned by hand against ScummVM v5; other large-script call-site offsets below are **raw candidate matches** pending instruction-boundary validation via descumm. Original resources remain read-only and outside Git.

## Strong source-backed root: ENCD (fully aligned)

Room 55 `ENCD` decoded chunk begins at offset **4,815,067**, total 15 bytes, **seven-byte script body** following the eight-byte header. The body's entire instruction sequence is:
- Body `0x0000`: `0A E0 FF` → `startScript(224)`, zero args.
- Body `0x0003`: `0A C8 FF` → `startScript(200)`, zero args.
- Body `0x0006`: `00` → stop/end script.

This proves the archive contains a **room-entry script that requests local scripts 224 and 200**, using the v5 `o5_startScript` instruction semantics. It does not prove they run in any particular live gameplay state, because room entry, resource mode and script scheduler were not captured.

## Branching descendants — source candidate call sites

Room 55 `LSCR[200]` source chunk at **4,815,092**, total length 311 bytes, body 302 bytes. Its first 23 `drawObject(..., no explicit state)`-shaped instructions are structurally consistent with initializing many room objects (but have not been independently descumm-aligned). Later:
- Body **0x006F** (111): raw `2A D1 FF` matches `startScript(209)`; this calls the previously decoded two-image random-dwell sequence of object 615 if the branch executes.
- Body **0x0124** (292): raw `2A D4 FF` matches `startScript(212)`.
- Body **0x0127** (295): raw `2A D5 FF` matches `startScript(213)`.
- Body **0x012A** (298): raw `2A D3 FF` matches `startScript(211)`.
- The first three calls above could be protected by conditions or only be reached under particular script states. A static instruction sequence is not runtime proof.

Room 55 `LSCR[212]` source chunk at **4,816,550**, total length 599 bytes (590-byte body). Its script body contains raw `startScript`-shaped references to the small, independently source-walked animation loops:

| Body offset | Raw candidate | Destination | Independent analysis available? |
| --- | --- | ---: | --- |
| 0x0015 (21) | `2A C9 FF` | local 201 | yes: 74-byte state loop |
| 0x002C (44) | `2A CB FF` | local 203 | yes: 74-byte state loop |
| 0x00D6 (214) | `2A CC FF` | local 204 | yes: 74-byte state loop |
| 0x00E3 (227) | `2A CD FF` | local 205 | yes: 74-byte state loop |
| 0x00F0 (240) | `2A CE FF` | local 206 | yes: 74-byte state loop |
| 0x00FD (253) | `2A CF FF` | local 207 | yes: 92-byte state loop |

The six loop resources may be **alternatively triggered**, rather than simultaneously active. The apparent conditional-dispatch blocks and any actor-related events need proper script analysis. The call sites are *candidate offsets*; do not claim whole-body decoding or that all children execute in the same frame.

**Potential reachability spine:**

```text
Room 55 ENCD (entry script)
  +-- startScript(224) [entry-level request verified]
  `-- startScript(200) [entry-level request verified]
         +-- startScript(209) [candidate under branch] --> object 615 random 5..10 yields
         +-- startScript(212) [candidate] --> selects among 201,203,204,205,206,207
         +-- startScript(213) [candidate]
         `-- startScript(211) [candidate]
```

*Do not present this tree as observed call execution or as simultaneous child animation.* To claim a full caller graph we need global callers, arguments, control-flow reachability, stop/cancel interactions and the scheduler phase.

## Why it matters

The original Room 55 evidence progressed from "many object images" to **script-aligned loop models**, then to a **source-backed entry node** and **plausible dispatch layer**. Capturing only object-frame changes would miss who starts/stops the animation, and when. A useful future P4 manifest must preserve hierarchical trigger provenance (ENCD → script → downstream script → object state event), not just frame IDs and nominal durations.

## Verification gates (none completed here)

1. Run authentic descumm against Room 55 scripts 200/212, confirm every candidate call is a real opcode boundary, and reconstruct conditional target branches and localVar parameters.
2. Observe natural room entry, scripts 224/200, scheduler status, and which descendants truly run. Record script slot/PC and actual vars, no inferred frame-time.
3. Recreate only the observed subset of object state events with source-native decoded assets and match native indexed front buffers.
4. Preserve and test room-entry vs debugger teleports; forced entry may bypass normal script and result in different active animations.

Sources:
- https://github.com/scummvm/scummvm/blob/v2026.4.0/engines/scumm/script_v5.cpp
- https://github.com/87otlto-coder/Scummbucket/blob/research/mi2-spelunk-20261116/docs/research/MI2_ROOM55_STATIC_EVENT_LOOPS_20261116.md
