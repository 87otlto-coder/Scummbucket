# 13 November 2026 — uploaded ScummVM save room probe

**Evidence class: directly decoded save bytes; no live gameplay execution.**

Uploaded `monkey2.s01`: **21,769 bytes**, SHA-256
`968bbdfaa855f35e0e89c271172d3d185448f256213f87d527cfa2b18ccea8ad`.
Gzip decompresses to **101,167 bytes**, SHA-256
`b80e4854e20541a39636ed236ed68f7b51e38f90d6e6aeea80e1b18918f9447e`.
After decompression: `SCVM`, save version **124**, description `poep`.
`THMB` begins at byte **44** with inclusive size **32,022**;
`INFO` begins at **32,066** with version 2 and size 26; the
SCUMM serializer starts at **32,092**. Following the 16-byte game MD5:
`_curPalIndex=0`, `_currentRoom=23`, `_roomResource=23`,
`_numObjectsInRoom=3`, `_currentScript=255`.
The game MD5 field is `3686cf8f89e102ececf4366e1d2c8126`
(as serialized, not independently matched to the original archive).

**Conclusion: structurally consistent ScummVM v124 saved state in Room 23,
not a Room 7 save.** This says nothing about whether a live ScummVM process
successfully resumes the file, or about natural gameplay entry into Room 7.

The first version of the saved-entry launcher incorrectly checked the
first four *compressed* bytes for `SCVM`. The corrected code
`scummbucket/scummvm_save.py` parses gzip or raw v124 saves read-only,
with a decompression cap, thumb/info boundary validation and a saved-room
field extracted using the source serializer. In the Room 7 capture path,
both saved room and room resource must equal 7 **before** any files are
created. User-supplied save data, thumbnail and game artwork stay
outside Git.

Source: [ScummVM v2026.4.0 SCUMM serializer](https://github.com/scummvm/scummvm/blob/v2026.4.0/engines/scumm/saveload.cpp).
