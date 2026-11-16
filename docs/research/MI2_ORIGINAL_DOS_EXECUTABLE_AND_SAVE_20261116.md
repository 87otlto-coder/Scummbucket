# MI2 DOS executable, audio drivers, and native saved state — original-archive reconnaissance (2026-11-16)

**Status: static file/header inspection only; NO execution, disassembly, save loading or gameplay verification.** Authorised uploaded `mi2.zip` was opened read-only; no constituent game resources or copyrighted text/music/art/ROMs are committed.

## Unexpected archive resources

Besides the original-style `MONKEY2.000/.001` resource pair, the archive includes these DOS-era binaries:

| ZIP member | Byte length | Raw member SHA-256 | Initial structural observation |
| --- | ---: | --- | --- |
| `MONKEY2.EXE` | **110,811** | `b16a5b67be5440316ebac405b129d69469649bc7d7b6a49d577d31074577dd50` | DOS MZ executable, header size 224 paragraphs, **864 relocation entries**, CS 4015, IP 9864 |
| `ADLIB.IMS` | 20,624 | `5c85b310d53fbfd523c3e6c171b165c3bb62415beb0d5e615429913bbea0a051` | DOS MZ-style module, 2 relocations |
| `ROLAND.IMS` | 18,976 | `e24efc2890104fd2953f65e97f81b30c6e25a55c7044ebef146ad7d5f09f5cab` | DOS MZ-style module, 2 relocations |
| `SOUNBLAS.IMS` | 24,808 | `ddaadb334e9140f0a56d2c90d7c722e397032595594ce939a1864ac02d4c77a7` | DOS MZ-style module, 21 relocations; identifies Creative Sound Blaster in static string scan |
| `SPEAKER.IMS` | 20,062 | `620c35abb2250200aee0c8c7d97eb0269f6f6c7b3663086d36280a0f7709398f` | DOS MZ-style module, 2 relocations |
| `SAVEGAME.001` | **37,908** | `b2864c0301004f7e72489f2acb54e9c9dba51276520956bc171ed9a4263e6795` | Starts with bytes `31 32 33 00` (ASCII `123\0`); contains apparent game-text strings and nonuniform binary regions. **Format, version, room, save slot and compatibility are not decoded.** |

The `MONKEY2.EXE` header's DOS page count (217), last-page byte count (219) and 110,811-byte member length are **arithmetically consistent**. This is a meaningful executable-container signature check, not original-game provenance authentication or assurance the program runs.

The four `.IMS` members also use `MZ` headers, and their names/embedded readable identifiers are consistent with audio driver modules. Do **not** equate module presence with which driver was selected at runtime. Their archive content is a separate potential original-interpreter comparison source and must remain under `FIXTURE/GAMES`, not `SOURCE` or Git.

The ZIP also contains `MT32_CONTROL.ROM` (65,536 bytes), `MT32_PCM.ROM` (524,288 bytes) and a small `.mid` file. These are third-party/possibly copyrighted inputs, **not ScummBucket project code or material for redistributable validation assets**. Do not upload them to GitHub or package them in public fixtures.

## Implications for original DOS fidelity research

1. ScummVM source analysis is useful but not identical to the original DOS interpreter. The supplied `MONKEY2.EXE` is a potential *independent original implementation* to examine with a license-compatible 16-bit disassembler/DOS debugger after the user's normal verification window resumes.
2. Particularly valuable unknowns for an eventual static/disassembly pass: original `CYCL` raw flag `0x0004` in Room 35, anomalous Room 64 `0xD906`, palette counter scheduler, actor/room drawing semantics, and original native save format. This is a **hypothesis/research plan**; no addresses in EXE have been tied to those handlers.
3. A DOS `SAVEGAME.001` is **NOT a ScummVM `monkey2.s01` file**, even if the archive includes both types elsewhere. Do not rename or feed it into existing ScummVM save-state tools as though its serialized format were established. ScummVM's older FAQ expressly warned that original game saves generally are not compatible. The four ASCII header bytes may be a save description, not a magic signature; do not guess.
4. The original executable and audio-driver identifiers should be recorded in future runtime capture manifests for provenance, alongside exact game resource hashes, emulator/driver revision, display/audio settings, and measured output.
5. No original EXE/driver/save files should be relocated, modified or checked into Git; if a future experiment needs copies, make separate non-overwriting paths under `F:\Dev\SCUMMBUCKET\FIXTURE\CAPTURES` or tool builds under `TOOLS`.

External context, not a substitute for direct verification:
- https://www.scummvm.org/old/faq.php — original savegame compatibility caveat.
- https://www.dosdays.co.uk/topics/Games/game_monkey2.php — reference DOS file listing with several same size members. Similar file sizes alone do not fingerprint the particular archive as an exact identified retail edition.

**Boundary:** binary/header structure, byte counts, and hashes are directly observed. Original executable functionality, palette flag meaning, savegame semantics, game version and runtime compatibility remain unresolved.
