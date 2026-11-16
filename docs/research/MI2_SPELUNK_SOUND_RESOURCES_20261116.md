# MI2 spelunking — original DOS VGA sound-resource census (16 November 2026)

Status: **source-structure reconnaissance only**, not audio decoding, musical reconstruction, playback, MIDI export or original-DOS verification. No audio resources are stored in Git.

## Evidence / method

- Source: user-supplied original-style `mi2.zip`, members `mi2/MONKEY2.000` and `mi2/MONKEY2.001`; decoded resource member SHA-256 of **stored original bytes** `ad045372e0d49626503bb50fca29a687ec8e01ef75d9b8bca702a366d143819e`.
- The read-only standalone Python probe read 110 LFLF room bundles from the decoded (XOR 0x69) original resource member, inspected all direct `SOUN` chunks, linked each to the index `DSOU` slot by source offset, and recorded first contained tags. This scan was *not* integrated into or rerun using the maintained ScummBucket parser and does not decode the full internal sound chunk grammar.
- **199 `SOUN` resources**, each resolved to one of **199 `DSOU` IDs**, across **59 rooms**; total containing `SOUN` chunk length **1,890,518 bytes**. Their individual stored sizes include metadata, not necessarily playable audio data.
- Every SOUN inspected begins with the internal four-byte `SOU ` tag (including trailing ASCII space). The source probe classified its first inner candidate tag and next header only; do not assume one single sound encoding per scene or playback channel.

| First embedded alternative | Header after alternative | Indexed SOUN count | Initial source classification (not a decoder) |
| --- | --- | ---: | --- |
| `ROL ` | `MDhd` | **142** | Roland/MIDI-oriented music data candidate |
| `ADL ` | `MDhd` | **53** | AdLib-oriented music/sfx data candidate |
| `SBL ` | `AUhd` | **3** | Sampled sound-effect data candidate |
| `SPK ` | `MDhd` | **1** | PC Speaker/PCjr-oriented data candidate |
| **Total** | | **199** | |

These labels are supported by ScummVM's resource-subtype handling in `engines/scumm/sound.cpp` (tag preference and sampled sound effects). **They are alternatives detected at the first embedded subtype position, not necessarily a complete list of all alternatives present inside each SOU resource.** Do not assume `ROL ` is a Standard MIDI File or `ADL ` contains already-rendered PCM. They are not equivalent to four fully decoded playable formats.

### Precision targets for P5

All source offsets below refer to decoded `MONKEY2.001` byte positions; original resource file XOR obfuscation changes byte values but not positions.

1. **Three SBL candidates are all in room 13**: `DSOU[70]` SOUN offset **1,071,825** (2,390 bytes), `DSOU[71]` offset **1,074,215** (3,230 bytes), `DSOU[72]` offset **1,077,445** (1,718 bytes). ScummVM source states that `SBL ` records can wrap VOC-style samples with `AUhd` / `AUdt` children. Test those exact chunks first for raw sample export and duration/quality determination, without fabricating a codec.
2. **The sole SPK candidate** is `DSOU[59]` in **room 33**, SOUN at offset **2,621,693** (190 bytes), next header `MDhd`. This is a compact PC-speaker-specific future fixture.
3. **Roland-oriented candidate** `DSOU[101]` in room 7: offset **475,994**, length **30,016**; `DSOU[151]` also in room 7 at **506,479**, length **43,520**. This aligns structurally with the existing Room 7 finding of scripts referencing these sound IDs, but **does not prove they played in the captured session**.
4. **AdLib-oriented candidate** `DSOU[48]` in room 7: offset **506,010**, length **469**. Again, storage association and previously documented script reference are separate from actual playback.
5. One header anomaly: `DSOU[1]` in room 6 at offset **392,118** (SOUN length **214**) has an internal `SOU ` raw length field of **zero** in the quick scan. This needs careful interpretation against the sound reader, without labeling the whole sound resource broken. A broad parser that assumes all internal lengths are ordinary outer chunk lengths may fail.
6. The largest SOUN wrapper found is **69,841 bytes**, `DSOU[222]` in room 110 at offset **9,001,382** (`ROL `). The next largest is `DSOU[154]` in room 103, **68,319 bytes** at offset **8,462,926**. These are size/format stress targets, not meaningful duration estimates.

Largest concentration of stored SOUN resources is **room 70: 25 resources**; additional room concentrations: rooms 90 (9), 91 (8), 87 (8), 29 (8), 47 (7). Do not conflate density with scene runtime music complexity: iMUSE can trigger globally indexed sounds from scripts stored in entirely different rooms.

## ScummVM source interpretation and implementation implications

The pinned ScummVM `engines/scumm/sound.cpp` `readSoundResource` selects a resource **alternative** based on output driver/device, with explicit priority rules for `ROL `, `ADL `, `SBL `, and `SPK `, among other tags. Its sampled SBL support documents `AUhd/AUdt` (or `WVhd/WVdt`) and VOC-style data; device selection can determine which music variant is actually loaded.

Hence **preserve the full source `SOUN` chunk in read-only extraction**, catalog *all* contained alternatives without discarding them, and keep the original device-independent resource ID. Never treat ScummVM's chosen output as the only source format or convert a raw chunk to a `.mid` merely by renaming. If the eventual decoder understands SBL PCM/VOC, record source rate, sample channel count, encoding, exact byte extent, wrapper offsets, and any uncertainty.

Sound extraction and sound *execution* are different:
- Archive fact: sound resource ID, offsets, sizes, tag hierarchy and hashes.
- Source semantic evidence: per-device sound subtype selection and iMUSE sound state.
- Runtime evidence still missing: active music/sfx voices, tempo, transitions, loops, triggers, fades, sample timing and precise output heard.
- Speculative/unverified: inferred duration of a `ROL ` file and interactions between scripts.

Reference: https://github.com/scummvm/scummvm/blob/v2026.4.0/engines/scumm/sound.cpp

## Non-destructive future plan (not performed)

1. Extend a validated structural sound parser under `SOURCE/ScummBucket` to enumerate all nested alternatives per `DSOU` ID and preserve unrecognized bytes and diagnostics; store only hashes/manifests in Git.
2. Run private original-archive tests of small ADL, SPK, ROL, SBL and anomalous zero-length-field resources; validate read-only integrity and chunk bounds.
3. Decode first three SBL candidates into lossless PCM only when sample header semantics are independently confirmed, then compare audio playback to ScummVM.
4. Separately research iMUSE event formats/tempo and device-specific alternatives; no invented fixed MIDI playback timing.
5. Keep produced audio and waveforms in `FIXTURE/OUTPUT` and reports in `FIXTURE/REPORTS`, outside Git.

**Boundary:** 199 DSOU sound slots structurally linked and classified by initial embedded subtype, not 199 audible playable tracks, not an implementation-complete P5 result.
