"""Synthetic recovery tests; never launch ScummVM or use private game data."""
from hashlib import sha256
import json
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch
import unittest

from tools import recover_cross_room_capture as recovery


class RecoveryTests(unittest.TestCase):
    def setUp(self):
        self.temp=TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name)
        for top in ("SOURCE","TOOLS","FIXTURE"):
            (self.root/top).mkdir()
        self.fixture=self.root/"FIXTURE"
        self.capture=self.fixture/"CAPTURES"/"Room7"/("cross-room-"+"a"*32)
        self.capture.mkdir(parents=True)
        self.report=self.fixture/"REPORTS"/"Room7"/self.capture.name
        self.report.mkdir(parents=True)
        self.game=self.fixture/"GAMES"/"MonkeyIsland2_DOS_VGA"
        self.game.mkdir(parents=True)
        archives={}
        for name,bytes_ in (("MONKEY2.000",b"index"),("MONKEY2.001",b"resource")):
            (self.game/name).write_bytes(bytes_)
            archives[name]=sha256(bytes_).hexdigest()
        self.archives=archives
        self.build=self.root/"TOOLS"/("ScummVM-P4-CrossRoom-"+"b"*32)
        self.build.mkdir()
        self.exe=self.build/"scummvm.exe"
        self.exe.write_bytes(b"distinct linked binary")
        self.exe_hash=sha256(self.exe.read_bytes()).hexdigest()
        (self.build/"cross-room-exe.sha256").write_text(self.exe_hash)
        (self.build/"cross-room-build.json").write_text(json.dumps({
            "status":"linked_executable_version_checked_not_runtime_capture",
            "exe_sha256":self.exe_hash,
        }))
        run=dict(command=[str(self.exe),"monkey2"],capture_mode="cross_room",
                 indexed_rooms=[7,12],script_trace="OPCODES",
                 archives=archives,exe_sha256=self.exe_hash)
        (self.capture/"run.json").write_text(json.dumps(run))
        for marker in ("doorway.enabled","capture.enabled"):
            (self.capture/marker).touch()
        (self.report/"doorway.json").write_text("{}")
        (self.report/"decoded.txt").write_text("framehash metadata")

    def _run(self, script_status="opcode_trace_observed",
             index_status="indexed_capture_with_actor7_8_observed"):
        def script(capture,report):
            result=dict(status=script_status,capture=str(capture),
                        engine_exe_sha256=self.exe_hash,opcode_observations=91)
            (report/"script_trace.json").write_text(json.dumps(result))
            return result
        def indexed(capture,report):
            result=dict(status=index_status,capture=str(capture),
                        indexed_frame_count=472,
                        room12_actor_draw_counts={"7":200,"8":150})
            (report/"cross-room-indexed.json").write_text(json.dumps(result))
            return result
        with (patch.object(recovery,"ARCHIVES",self.archives),
              patch.object(recovery,"analyze_scripts",side_effect=script),
              patch.object(recovery,"verify_indices",side_effect=indexed)):
            return recovery.recover(self.root,self.capture)

    def test_reprocess_accepted_capture_no_game_launch_or_video_regeneration(self):
        old=(self.report/"doorway.json").read_bytes()
        result=self._run()
        self.assertEqual(result["status"],"postcapture_evidence_complete_scene_fidelity_pending")
        self.assertTrue(result["original_raw_capture_untouched"])
        self.assertEqual(result["script"]["opcode_observations"],91)
        self.assertEqual(result["indexed"]["indexed_frame_count"],472)
        self.assertEqual((self.report/"doorway.json").read_bytes(),old)
        with patch.object(recovery,"ARCHIVES",self.archives):
            replay=recovery.recover(self.root,self.capture)
        self.assertEqual(replay["status"],"postcapture_evidence_complete_scene_fidelity_pending")
        self.assertEqual(replay["script"]["status"],"preexisting_report_preserved")
        self.assertEqual(replay["indexed"]["status"],"preexisting_report_preserved")

    def test_missing_actor_state_remains_incomplete(self):
        result=self._run(index_status="partial_indexed_capture_missing_actor7_or_actor8")
        self.assertEqual(result["status"],"postcapture_evidence_incomplete")

    def test_missing_raw_report_or_wrong_capture_path_fails_closed(self):
        with patch.object(recovery,"ARCHIVES",self.archives):
            with self.assertRaisesRegex(ValueError,"canonical"):
                recovery.recover(self.root,self.report)
            (self.report/"doorway.json").unlink()
            with self.assertRaisesRegex(ValueError,"Previous doorway/video report incomplete"):
                recovery.recover(self.root,self.capture)

    def test_changed_executable_is_rejected(self):
        self.exe.write_bytes(b"tampered")
        with patch.object(recovery,"ARCHIVES",self.archives):
            with self.assertRaisesRegex(ValueError,"absent or changed"):
                recovery.recover(self.root,self.capture)

    def test_invalid_previous_report_must_not_be_overwritten(self):
        (self.report/"script_trace.json").write_text(json.dumps(
            dict(status="opcode_trace_observed",capture="another-run",
                 engine_exe_sha256=self.exe_hash)))
        existing=(self.report/"script_trace.json").read_bytes()
        def indexed(capture,report):
            result=dict(status="indexed_capture_with_actor7_8_observed",capture=str(capture))
            (report/"cross-room-indexed.json").write_text(json.dumps(result))
            return result
        with (patch.object(recovery,"ARCHIVES",self.archives),
              patch.object(recovery,"verify_indices",side_effect=indexed)):
            result=recovery.recover(self.root,self.capture)
        self.assertEqual(result["status"],"postcapture_evidence_incomplete")
        self.assertEqual(result["script"]["status"],"FAILED_EXISTING_REPORT")
        self.assertEqual((self.report/"script_trace.json").read_bytes(),existing)


if __name__ == "__main__":
    unittest.main()
