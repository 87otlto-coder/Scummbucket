# MI2 Room72 script204 potential screen-wide palette impact — read-only CLUT crosscheck (18 November 2026)

**Evidence classes separated:** Original DOS VGA MONKEY2.001 SHA-256 ad045372e0d49626503bb50fca29a687ec8e01ef75d9b8bca702a366d143819e (read-only); original physical Room72 CLUT chunk; private previously generated source-native 320×144 background PNG; pinned ScummVM v2026.4.0 palette.cpp. **No gameplay/ScummVM runtime execution or pixel-accuracy verification against an independently observed source.** Source PNG and copyrighted original artwork remain private and outside Git.

## Surprising numerical result: the candidate palette script would touch almost the entire indexed background

Original Room72 tagged CLUT is at decoded .001 offset **0x5D868C**, size **776 bytes** (8-byte header and 768 RGB bytes: a native 256-color palette). The prior privately generated reference **room72_background.png**, dimensions **320×144 RGBA**, SHA-256 **377462ea0024399aaf3c7c48e88c742cd832d51dc1a189384a3da9902d1e0de2**, is a *research-derived image*, not a verified gameplay screenshot. Its alpha is fully opaque.

A read-only crosscheck of its RGB pixels against the original CLUT yields:
- **46,080 of 46,080** RGB pixel positions match a CLUT entry.
- **144 distinct RGB colors** occur in the PNG, all matching **unique** original CLUT indices (no ambiguous duplicate-index inverse mapping among used colors). This makes an unambiguous inferred palette-index histogram for the research reference.
- **37,774 pixels (81.975%)** map to palette indexes **65–157**, targeted by the first original script204 intensity command.
- **7,968 pixels (17.292%)** map to indexes **169–187**, targeted by the second intensity command.
- Together **45,742 of 46,080 pixels (99.2665%)** in the private decoded reference use one of those two disjoint ranges. Only **338 positions (0.7335%)** use colors outside the target ranges.

| Source palette-index range | Count in private native background | Share of 320×144 image | Source operation |
| --- | ---: | ---: | --- |
| 65–157 | **37,774** | 81.975% | Room72 LSCR204 first SO_ROOM_INTENSITY |
| 169–187 | **7,968** | 17.292% | Room72 LSCR204 second SO_ROOM_INTENSITY |
| Outside both | **338** | 0.733% | Not altered by these two commands |
| **Total** | **46,080** | 100% | |

These counts are an exact pixel-to-original-CLUT lookup **for the supplied privately decoded reference**, not independent proof of native frame-buffer fidelity, original DOS runtime display or exact foreground-object coverage. Runtime actor costumes/OBIM overlays could affect the actual screen. A faulty source-native image decoder could still produce RGB colors that happen to be valid CLUT entries; this check is internally consistent but **not an independent renderer oracle**.

## Counterfactual intensity example (never observed)

Room72 LSCR204 was previously completely source-walked (81/81 bytes) and samples scale values230..280, rejects consecutive candidates differing by12 or less, and uses a one-breakHere loop for paired range intensity updates. With pinned ScummVM palette.cpp, RGB is re-derived from room base palette using integer channel*scale/255 and capped to252 in ordinary v5.

Example original background palette index **102** has source base RGB **(160,48,20)**:
- scale230 yields **(144,43,18)**;
- scale280 yields **(175,52,21)**.

Applying that endpoint comparison across *the private reference's inferred index map*, **all 45,742 targeted positions have different RGB values** (99.27% of the background), with 338 positions unchanged. This is a reproducible **synthetic prediction**, not a real screen capture or proof that those two scales occur in adjacent updates.

Given the algorithm's enforced minimum 13-unit scale change and its nearly complete background index coverage, the script is **capable of a very conspicuous whole-room palette effect if executed**. However the [literal caller search](MI2_ROOM72_ORPHAN_PALETTE_AND_BONE_CODES_20261117.md) found no direct startScript(204) in Room72 script/verb resources; the only indexed-global literal call targeted another room. We therefore **must keep source-present, caller-unverified, runtime-unobserved**, not describe the room as visibly flashing during ordinary gameplay.

## P4 implications / cheapest future gate

1. Before spending on visual implementation, instrument Room72 logical130/131/132 scripts and log whether room-local **LSCR204** ever becomes active; gate on actual SCRIPT SLOT, not source script existence.
2. If observed, record full native 256-entry RGB palette per update; source indexed pixels can remain unchanged while almost the entire displayed room changes. Save each scale value, pixel/CLUT hash, script PC and event ordering. Compare the reconstructed target ranges against actual ScummVM and only then original interpreter if needed.
3. If never observed, preserve script204 as **source-present potential/orphan routine** and do not prioritize synthetic animated exports as faithful gameplay.
4. P1/P4 inventory should distinguish palette range **coverage of stored native pixels**, script source reachability, runtime execution and visual appearance. These are four different evidence levels.
5. Original source, private reference PNG and captures belong under FIXTURE; no copyrighted resources in Git.

**Conclusion:** A highly visible, source-encoded palette effect exists in Room72 and its target indices cover 99.27% of a private source-native background reconstruction. Whether this effect *ever actually runs* is still unknown.
