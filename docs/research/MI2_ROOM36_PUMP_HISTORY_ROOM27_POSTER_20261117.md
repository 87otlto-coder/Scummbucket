# MI2 pump-history flag links Room36 animation to Room27 wanted-poster dialogue (17 November 2026)

**Evidence class:** read-only original DOS VGA `MONKEY2.001` resource archive, stored-byte SHA-256 `ad045372e0d49626503bb50fca29a687ec8e01ef75d9b8bca702a366d143819e`, with independently decoded source instructions; opcode meanings checked against pinned ScummVM [v2026.4.0 script_v5.cpp](https://github.com/scummvm/scummvm/blob/v2026.4.0/engines/scumm/script_v5.cpp) and [script.cpp](https://github.com/scummvm/scummvm/blob/v2026.4.0/engines/scumm/script.cpp). **No gameplay execution, official descumm comparison, runtime trace or framebuffer comparison.** Original archive bytes remain private and unchanged.

## 1. Independently aligned scripts

| Source | Native script body | Bytes fully consumed | Opcodes | Relative targets and alignment |
| --- | ---: | ---: | ---: | --- |
| Room27 **LSCR205** | `0x20DCAB` | **1,804 / 1,804** | **94** | **25 / 25** on instruction starts or end |
| Room36 **LSCR200** | `0x2BFB48` | **279 / 279** | **188** | **6 / 6** valid |

Both walks used the same private narrow SCUMM v5 script decoder, which parses the variable-length `printEgo` strings and `waitForMessage` opcodes, v5 `jumpRelative` branch polarity and local/bit variables. Instruction-boundary agreement is a strong structural check, **not** independent original-interpreter validation.

## 2. Room36 pump cutscene is a *history flag writer*

Room36 LSCR200 uses this source instruction sequence:

| Script PC | Original opcode-level action |
| ---: | --- |
| `0x002D` | `equalZero(Bit[763])`, else jump `0x0097` |
| `0x0032` | `move Bit[763] = 1` |
| `0x0037–0x0096` | ego actor costume69 actions **7–10** with **80 `breakHere` yields** |
| `0x0097` | Rejoin, continue actions **11–14**, sound35 and Bit92 transitions |

On first normal pump use when `Bit763=0`, code sets it to 1 and plays a longer series of costume actions. On later normal uses when the flag is set, code skips **80 explicitly encoded yields**. The flag is written at PC0x0032 **after** the first 18 yields following action6. **If a player cutscene-skips before this PC, Bit763 may remain zero**; do not universally claim that every completed/skipped pump interaction sets it. The skip target `0x00EF` bypasses this assignment and reaches the mandatory Bit92 environmental toggle.

The previous report [pump LSCR200](MI2_ROOM36_PUMP_CUTSCENE_SCRIPT200_20261117.md) identified the 158/78 yield paths and skip handling. This document isolates the **cross-room history write** and its downstream use.

## 3. Room27 script205 reads the same flag to customize the wanted poster

Room27 has OBCD objects called **“poster”**, IDs **263** and **265**. Its completely decoded local LSCR205 reads numerous persistent bits and dynamically assembles what Guybrush reads on the poster. It is a large **conditional narrative script**, not a scenery animation loop.

At LSCR205:
- `PC 0x02B2`: **`notEqualZero(Bit763)`**; when Bit763 is zero, branch forward to PC`0x0373`.
- When Bit763 is **nonzero**, it prints a complaint about **tampering with municipal plumbing without an environmental impact report**, then `waitForMessage`; then a second line about transporting animals under improper conditions, followed by another wait.
- If Bit763 is **zero**, PC`0x0373` examines `Bit177`; when Bit177 is set, the script can enter at PC`0x032A` and print **only** the separate animal-transportation line. Therefore the second line is **not exclusive evidence of pump use**.
- `PC 0x06FE`: end override, then cleanup, `Bit761=1`, end cutscene and stop. The initial Bit761 test changes the beginning of the poster-reading text. `Bit761` is a **poster-read history flag** in this path, not an animation-cycle flag.
- The routine also consults numerous unrelated world-state bits and object owner295, illustrating why a raw source scan yields many variable references without proving scenery significance.

**Strong supported consequence:** Source events from Room36's pump-cutscene history affect the dialogue presented by Room27's wanted-poster script, across rooms. This is specifically a **narrative consequence of an animation event**. Preserve it as a *state dependency*, not a mandatory P4 renderer prerequisite.

## 4. Bounded archive-wide read/write evidence

A separate literal-address search through original `ENCD`, `EXCD`, `LSCR`, paired `OBCD/VERB`, and indexed `SCRP` script-bearing storage found exactly **three** mentions of the literal `Bit[763]` address bytes `FB 82`:
- Room36 LSCR200 **two**: one tested branch, one literal set-to-1.
- Room27 LSCR205 **one**: a literal conditional read.

This does **not** exclude indirect bit writes, interpreter state updates, changed game editions, other non-tagged execution paths or incorrect assumptions in generic byte-pattern scans. It does give a narrow high-confidence static linkage. Do not extrapolate to “only three executed accesses” or claim global write coverage exhaustively.

## 5. Engineering implications / further validation

1. Add optional **world-state provenance** for `Bit763`: `source_room=36`, `source_script=200`, `source_pc=0x0032`, and distinguish *normal-completed* from *skipped-before-assignment* pump cutscenes.
2. In P4, reconstruct *visual* pump animation without needing Room27 dialogue logic; if creating P6 scene interactions, expose narrative/world-state ramifications without presenting them as background pixels.
3. For Room27 test vectors, record first-pump vs repeat-pump vs skip-pump and Bit177 overrides. Capture raw bit values and poster dialogue paths, rather than assuming these are inferred from playtime.
4. Compare official `descumm -5 -o` instruction offsets and a pinned ScummVM trace for the key bit writer/reader. Original DOS parity is **not** established.

**Reconstruction status:** independent original archive opcode alignment + pinned engine semantics. No source code change to ScummBucket, no game resources uploaded to Git.
