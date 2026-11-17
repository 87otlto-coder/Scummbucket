# MI2 Room55 identity and four dialogue groups — Mardi Gras party (17 November 2026)

**Evidence:** read-only original DOS VGA `MONKEY2.001`, fingerprint `ad045372e0d49626503bb50fca29a687ec8e01ef75d9b8bca702a366d143819e`, alongside complete bytecode walks of Room55 LSCR200/211/212/213/220–224. This report uses brief **thematic summaries** of the game's original script-embedded text, not reproduced dialogue transcripts or original game assets. Original input remains unchanged/private. **No runtime execution, original interpreter equivalence, full official descumm cross-check or visual/audio parity.**

## Grounded room identity: a crowded Mardi Gras party

A direct read-only source-string inspection of Room55 **LSCR214–219** identified an unmistakable set of conversations about Mardi Gras, costumes/masks, a party, toasts to Elaine, food/drinks, and player interaction with nearby characters. The originally extracted strings prove the *source resource's intended dialogue context* even though exact normal gameplay playback is unobserved.

**Classification correction:** Room55 is not adequately described as generic “background scenery with randomized object states.” It is a **party/crowd scene with actor-driven speech, potentially mouth/pose images, idle animation, proximity-dependent dialogue groups and sound**. It remains useful to P4 as a complex *environmental-scene composition test*, but accurate reconstruction necessarily intersects **P3 costumes/actors** and **P6 interactive preview**. Do not promote its stored object states to a generic looping background GIF.

## Four matching speaker/proximity groups

The fully aligned [Room55 spatial controller](MI2_ROOM55_COMPLETE_SPATIAL_SCRIPT211_20261117.md) maps actor proximity to exactly four group IDs:

| Spatial group ID | Two original actors | Controlling child | Source dialogue character |
| ---: | --- | --- | --- |
| **7** | actor7 and actor5 | LSCR214 | costume-related banter / party chatter |
| **8** | actor8 and actor11 | LSCR215 | mask / costume conversation |
| **9** | actor9 and actor10 | LSCR216 | toasts and group-party remarks |
| **12** | actor12 and actor6 | LSCR217 | lighthearted banter about the party and costumes |

Three of those controlling children have **direct source-byte encoded `startScript(218,[speakerA,speakerB])` calls**:
- Room55 LSCR214 at body PC **0x020**: `0A DA 01 07 00 01 05 00 FF` → script218 with **[7,5]**.
- LSCR215 at body PC **0x063**: `0A DA 01 0B 00 01 08 00 FF` → script218 with **[11,8]**.
- LSCR217 at body PC **0x04B**: `0A DA 01 0C 00 01 06 00 FF` → script218 with **[12,6]**.
- LSCR216's beginning and script source contain numerous party toasts but do **not** have the same literal `0A DA` startScript218 sequence. Its full encoded talking/animation scheduler needs a separate walk; do not infer it calls218.

These three source call sites have coherent v5 word-vararg encodings and consistent known actor identities, but **full alignment of LSCR214–219 is still pending**. Treat only those direct call bytes as local call candidates until the entire respective parent body is walked.

The same actor IDs and relative spatial groupings appear in [Room55 script200](MI2_ROOM55_COMPLETE_ENTRY_SCRIPT200_20261117.md), which initializes all eight actors, positions and talk palette indices, and in [script212](MI2_ROOM55_COMPLETE_SPEAKER_CONTROLLER_20261117.md), which matches current `VAR_TALK_ACTOR` and drives 201/202/203–207 object-state loops.

## Source-level model and priority

The emerging (not runtime-validated) mechanism is:

`Room55 ENCD → script200 → {script211 spatial scheduler; script212 speaker animation; script213 paired object states}`

With **script211** choosing between group conversations214–217 and ambient220–223, and **script212** running per-speaker graphics as dialogue changes. Ambient fallback scripts can also start some of those image loops. **Script224** performs a separate sound/global-script startup handoff.

This makes Room55 a useful validation target for:
1. actor positions, costumes, talk colors and foreground/background layering in a large cast;
2. transitions into/out of a spatial group as Ego approaches characters;
3. mouth/pose image changes under speech and ambient fallback;
4. script-driven dialogue/timing, random delays and independent sound events; and
5. randomized, non-looping composite scene preview that preserves source chronology.

**Still unknown:** full source-aligned LSCR214–219 bodies and their text/choice branches; actor visual costume pixels; real room rendering, script start/cancellation, exact speaker schedule; and whether the party has distinct environmental animated layers independent of actor talk/poses. No copyrighted text transcript/graphics included in Git.

**Research practice:** identify source-controlled *character animation* separately from background/palette animation. The same P4 compositor may need to display both, but P4 background-animation completion should not be conflated with successfully animating dialogue sprites.
