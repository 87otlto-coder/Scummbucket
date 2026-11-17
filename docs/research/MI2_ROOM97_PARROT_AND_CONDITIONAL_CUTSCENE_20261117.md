# MI2 physical Room97: Parrot actor, randomized costume loops and conditional object cutscene (17 November 2026)

**Evidence:** original DOS VGA MONKEY2.000/.001 source, read-only; MONKEY2.001 SHA-256 ad045372e0d49626503bb50fca29a687ec8e01ef75d9b8bca702a366d143819e. Private narrow v5 opcode parser fully consumed the script bodies below with all valid relative branch targets; semantics checked against pinned [ScummVM v2026.4.0 script_v5.cpp](https://github.com/scummvm/scummvm/blob/v2026.4.0/engines/scumm/script_v5.cpp), particularly actorOps, animateActor, getRandomNr (inclusive), delayVariable, wait, drawObject and ifClassOfIs. **No official descumm crosscheck, no observed runtime or original DOS behavior, no real costume-frame/pixel parity.** All copyrighted bytes remain outside Git.

Physical Room97 is aliased by seven logical room IDs **141,142,143,145,147,148,155**. See [foreign floating-object banks](MI2_PSEUDOROOM_CROSSROOM_OBJECT_BANKS_20261117.md) and [fully aligned imported-object dialogue](MI2_ROOM97_IMPORTED_ANIMATED_DIALOGUE_20261117.md). The original physical RMIM is shared, but script entry chooses object layout, logical room, classes and actor conditions.

## Source alignment

| Local script | Bytes consumed | Instructions | Relative branch checks | Function |
| ---: | ---: | ---: | ---: | --- |
| **203** | 86/86 | 17 | 2/2 | Configure/position Parrot into logical145 |
| **204** | 86/86 | 17 | 2/2 | Configure/position Parrot into logical147 |
| **206** | 53/53 | 9 | 3/3 | Repeating randomized costume action |
| **207** | 32/32 | 6 | 2/2 | Periodic message/auxiliary script check |
| **208** | 228/228 | 122 | 3/3 | Branch-dependent actor+object cutscene, 92 yield opcodes total |
| **212** | 91/91 | 26 | none | Fixed 13-draw image-state sequence |

### Parrot is named in original source, not inferred from the graphics

Room97 local scripts203 and204 both begin with an **actorOps(7)** setup including source-encoded actor name **Parrot**, costume **39**, speech colour217, walk animation frame9, ignore-boxes, never-Z-clip and elevation **100**. Each tests actor7's existing room: if already in current logical room it positions/animates the actor immediately; otherwise it executes **delay(120)** before the actor is put in the target room and walks from offscreen.

- LSCR203: target logical **145**, destination **(85,136)**; offscreen starting X **-10** (signed v5 getVarOrDirectWord), Y150.
- LSCR204: target logical **147**, destination **(111,157)**; offscreen X **-10**, Y180.
- Both then clear a class flag for a different object, yield once, **start local206 and local207**, stop. Entry script calls local203 when logical145 plus Var528==1; calls local204 when logical147 plus Var528==2. These are source-coded ENCD callers, but no gameplay entry has been observed.

### Local206: conditional random animation actions

Loop body:
1. Compute delay **30 + getRandomNr(60)**, therefore integer **30..90 script units**, pause via delayVariable.
2. Choose **actor7 action 7 or8** via 7+getRandomNr(1).
3. Depending on whether VAR_HAVE_MSG (Var3) is zero and VAR_TALK_ACTOR (Var25) equals7, issue the selected action.
4. Return to the top until script is stopped externally.

No single canonical frame sequence exists from this script without recorded random values and dialogue state. The underlying COST39 cels are not yet decoded or compared to engine actor imagery.

### Local207: periodic auxiliary script

Repeatedly computes **(2 + getRandomNr(2)) × 60** → **120,180,240** script units, waits that interval, and if VAR_HAVE_MSG is zero starts global script100. This does not establish a visible animation by itself; the exact side effects of global100 require separate source or runtime examination.

### Local208 / 212: two separate long visual paths

Room97 local208 (228 bytes) is a cutscene with object/actor effects selected by the class status of object **795**, class encoded **134 (0x80|6)**:

- The first branch displays and modifies states of physical Room97 object **1066**, changes object1049/1058 states/classes, uses actor action sequence and sound68; it includes **47 explicit breakHere opcodes** in that source span.
- The alternate branch animates Ego with different actions, starts local **212**, **waits while it is running**, and includes **45 explicit breakHere opcodes** in its source span.
- Both converge at the final restoration of Ego costume1/actions and end the cutscene.

**92 is a count of syntactically present yield opcodes across mutually exclusive source paths, NOT 92 yields executed in one interaction.** Other script-state pauses and branching can affect actual duration.

Local212 contains the exact 13-image-state draw order on Room97 object1066:

**1 → 2 → 3 → 5 → 2 → 4 → 1 → 4 → 2 → 5 → 2 → 4 → 2**.

There are **12 explicit breakHere yields** separating those 13 state writes. Object1066 has **five** original IMxx stored image states. The sequence is finite, not a perpetual loop.

## ScummBucket implications

We now have three source-backed but different visual systems within one shared physical room97:

1. **COST39 actor7 Parrot**, physical character movement and randomized actions in logical145/147.
2. **Imported FLOB object1098** (source bank100, six states), separately started and stopped within the large local202 dialogue.
3. **Local object1066** (source physical97, five states), 13-position fixed source-coded draw sequence in cutscene208/212.

A future scene model must preserve which logical alias is active and distinguish actor costume/cels, floating object source and current-room object state, plus random/timer/dialogue gating. Capture each with costume clip plane and indexed front/back buffer, and only upgrade to P4 acceptance after pixel-faithful comparison.

**Unresolved:** actual costume39 drawing, natural trigger of cutscene208, global100's effect, branch access and exact engine timer cadence. All available evidence in this report is static original source + pinned ScummVM semantics.
