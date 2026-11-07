"""Optional *real* external disassembly regression for the fingerprinted DOS MI2 sample.

Never bundle game resources or descumm in GitHub. Runs only when the user
provides an authorized archive and an existing external descumm executable.
The default CI run skips this test; mocked tests in test_descumm_verification.py
do not replace actual disassembler verification.
"""
import os
from pathlib import Path
import unittest

from scummbucket.descumm_verification import verify_descumm

ARCHIVE = os.environ.get("SCUMMBUCKET_MI2_ARCHIVE")
DESCUMM = os.environ.get("SCUMMBUCKET_DESCUMM")
EXPECTED_RESOURCE_SHA256 = "ad045372e0d49626503bb50fca29a687ec8e01ef75d9b8bca702a366d143819e"
EXPECTED_SCRIPT_HASHES = {
    201: "3dd3377827386229962e9aae8d681426115ad228efe1ecf36d7469154d1fbc09",
    202: "1bb2578f20c0aad5146995f7d40b5cfdd0fe6b5c25a65faaffeddb5f12c82ee9",
}


@unittest.skipUnless(
    ARCHIVE and DESCUMM,
    "Real descumm fixture absent: set SCUMMBUCKET_MI2_ARCHIVE and SCUMMBUCKET_DESCUMM",
)
class PrivateDescummIntegrationTest(unittest.TestCase):
    def test_room34_object358_instruction_alignment(self):
        archive = Path(ARCHIVE)
        disassembler = Path(DESCUMM)
        self.assertTrue(archive.exists(), f"Archive input not found: {archive}")
        self.assertTrue(disassembler.is_file(), f"descumm executable not found: {disassembler}")

        # Verified independently on user-owned input; not an assertion of
        # runtime reachability, loop semantics, or animation timing.
        for script_id, count in ((201, 11), (202, 6)):
            with self.subTest(script_id=script_id):
                report = verify_descumm(
                    archive, room_id=34, script_id=script_id,
                    object_id=358, descumm=str(disassembler),
                )
                self.assertEqual(report["status"], "success", report["diagnostics"])
                self.assertEqual(report["source"]["sha256"], EXPECTED_RESOURCE_SHA256)
                self.assertEqual(
                    report["source"]["script_chunk_sha256"],
                    EXPECTED_SCRIPT_HASHES[script_id],
                )
                summary = report["summary"]
                self.assertEqual(summary["candidates"], count)
                self.assertEqual(summary["confirmed_opcode_starts"], count)
                self.assertEqual(summary["not_emitted"], 0)
                self.assertEqual(summary["opcode_conflicts"], 0)
                self.assertTrue(all(
                    item["disassembly_status"] == "confirmed_opcode_start"
                    and item["instruction_alignment_verified"]
                    and not item["runtime_execution_verified"]
                    and not item["script_control_verified"]
                    for item in report["candidates"]
                ))


if __name__ == "__main__":
    unittest.main()
