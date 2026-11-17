# MI2 Room55 — COMPLETE conversation scripts214–219 and shared party guest caller (17 November 2026)

**Source evidence:** read-only original DOS VGA `MONKEY2.001` archive, SHA256 `ad045372e0d49626503bb50fca29a687ec8e01ef75d9b8bca702a366d143819e`, XOR0x69 decoded at unchanged offsets. Independent narrowly scoped SCUMM v5 decoder, implementing only encountered opcode families (conditionals, expression nesting/random, direct/indirect variables, actor print, `resStrLen`-compatible `0xFF` embedded escape byte skipping, script start/stop/waits, delays and image-state control). Source semantics checked with pinned [ScummVM v2026.4.0 script_v5.cpp](https://github.com/scummvm/scummvm/blob/v2026.4.0/engines/scumm/script_v5.cpp) and [script.cpp `resStrLen`](https://github.com/scummvm/scummvm/blob/v2026.4.0/engines/scumm/script.cpp). **No official descumm cross-check, live gameplay, DOS original execution or native image/audio fidelity tests.** Original copyrighted dialogue/resources remain private; no transcript/audio/graphics committed.

## Complete source-boundary verification

| Room55 LSCR | Original tagged chunk start | Body bytes decoded | Instructions | Valid branch targets |
| ---: | ---: | ---: | ---: | ---: |
| **214** | `0x4982A5` | **488/488** | **46** | **20/20** |
| **215** | `0x498496` | **1296/1296** | **125** | **64/64** |
| **216** | `0x4989AF` | **1509/1509** | **164** | **52/52** |
| **217** | `0x498F9D` | **664/664** | **78** | **32/32** |
| **218** | `0x49923E` | **829/829** | **79** | **30/30** |
| **219** | `0x499584` | **865/865** | **62** | **39/39** |
| **Total** | | **5651/5651** | **554** | **237/237** |

A naïve NUL-terminated string scanner would falsely terminate on the embedded `0xFF 0x09 <u16>` control present in script219's original text; this source walk mirrors ScummVM `resStrLen`'s legacy v5 rules, which consume 2 extra bytes following most `0xFF` message-control subcodes. Accurate bytecode alignment here validates **control-data boundaries**, not displayed text/layout.

## Conversation content and source state-machine structure

Original dialogue themes explicitly establish **Mardi Gras party / masked guests**, consistent with [Room55's actor group classification](MI2_ROOM55_MARDIGRAS_CROWD_DIALOGUE_CONTEXT_20261117.md).

Scripts **214,215,217** are group conversation drivers, with persistent original global state counters that determine when to stop using introductory authored exchanges and switch to generic reusable party chatter:

| Script | Group actors | Conversation progress global | Dedicated source dialogue selection | Fallback |
| ---: | --- | --- | --- | --- |
| 214 | actor7 + actor5 | **Var540** (`0x021C`) | current indexed case 0–7 | when counter exceeds 7, `startScript(218,[7,5])` |
| 215 | actor11 + actor8 | **Var541** (`0x021D`) | indexed cases 0–25 | after 25, `startScript(218,[11,8])` |
| 217 | actor12 + actor6 | **Var543** (`0x021F`) | indexed cases 0–11 | after 11, `startScript(218,[12,6])` |

The fully aligned paired-actor `startScript(218)` instruction locations are script214 PC0x020, script215 PC0x063, script217 PC0x04B. These scripts also set relevant image synchronization flags, stop prior visual loops, draw source object states and wait for message/child completion. The counter/branch logic proves a **source-defined exhaustion/fallback system**; actual game state, progress, player interruption, and sequence frequency remain unobserved.

**Script216**, group actor9+10, is independently different: it uses source global **Var542** (`0x021E`) to select among **22** paired party-toast conversation cases (indices 0–21). It first randomly chooses which of actor9/10 takes the first turn; once the counter exceeds 21 it uses random non-repeating choice instead of calling the shared script218. It also manipulates synchronized flags Var167/168 and includes multi-yield and delayVariable timing segments. **Do not** classify 216 as a caller of script218.

### Shared script218: 13 two-speaker conversation patterns

Fully aligned script218 has:
- input **`Local0` and `Local1`** as actor numbers, received from script214/215/217;
- `getRandomNr(1)` at PC0 to decide whether to swap the two speaker roles;
- persistent **Var544** (`0x0220`) as conversation index when it is within **0–12**, incremented after selecting an indexed case;
- thereafter random selection **0–12** while rejecting immediate repetition of a previous stored choice in **Var161** (`0x00A1`);
- **13** source-coded two-speaker cases, typically `print(actorA)`, `wait(message)`, `print(actorB)`, followed by termination.

It is a genuine **parameterized, shared dialogue script** with randomized speaker ordering and non-repeating talk lines, not an animation-frame list. The actual specific dialogue lines remain private and unnecessary in the research output.

### Script219: 18 reusable Guybrush replies and eight identical object callers

Fully aligned Room55 script219:
- uses **Var545** (`0x0221`) as the sequential progress counter while its value is 0–17;
- after exceeding 17, selects a random value **0–17** with rejection of the previous selection in **Var162** (`0x00A2`);
- performs **18** source-coded `printEgo` branches (Guybrush remarks), and terminates after one selected branch.

**New exact archive caller discovery:** Eight Room55 OBCD objects **639,640,641,642,643,644,645,646** all have original OBCD name `party guest` and **byte-identical 37-byte `VERB` chunk payloads** (read-only identical SHA-256 prefix `dc4e5be8d990`).

Each `VERB` table has verb IDs **8,10,90** with relative tagged-chunk offsets **24,41,18**. The **verb10 handler** at tagged-VERB offset 41 is exactly `0A DB FF 00`: `startScript(219)`, then `stopObjectCode`. This is a genuine *fully aligned four-byte verb-handler call*, not an accidental unaligned pattern inside prose. Another verb handler displays a short player response; the verb90 handler mutates a source game variable. The complete semantic labels of verb IDs require normal SCUMM input dispatch/context and should not be invented.

**Source call graph:** `party guest object(639..646).verb10 → LSCR219 → one of 18 Guybrush remarks`.

This coexists with room spatial group dialogue `LSCR211 → LSCR214/215/216/217 → LSCR218`, and with room active speaker visual synchronization `LSCR212/213`. The two event systems may interact through the global talking-actor variable, but *actual overlap/timing* requires runtime evidence.

## Architectural significance

Room55 now demonstrates both:
1. **automatic crowd chatter:** room-situated actors with distance/Y-dependent conversation controllers, sequenced or randomized dialogue, and synchronized image-state animation; and
2. **interactive party guest speech:** eight separate logical object identities reuse a single 18-choice Guybrush script via byte-identical verb handlers.

For P3/P4/P6, retain *logical object*, *actor*, *script*, *dialogue counter*, *speaking actor*, *image state*, and *event timing* as separate fields. Audio, subtitles, masks, costume animation and pixel renderer must still be verified.

**Follow-up gate:** official descumm script214–219 and eight VERB chunks; original SCUMM/ScummVM capture staged by party-guest verb10 and by four spatial groups; track Vars540–545, Vars161/162, current talk actor, actor location, script PC, object states, user-facing string timing, native indexed compositing and audio commands. No acceptance label from source alignment alone.
