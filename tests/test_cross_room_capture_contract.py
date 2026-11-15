"""Fixture-free cross-room recorder build, capture and evidence contract tests."""
from hashlib import sha256
from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace
from unittest.mock import patch
import json
import unittest

from tools import build_cross_room_recorder as builder
from tools.verify_cross_room_capture import parse_draw_actor, verify


def digest(data):
    return sha256(data).hexdigest()


def row(tick,room):
    return "\t".join(map(str,[tick,room,room,10,20,2,160,100,0,0,150,150,""]))


def draw(actor):
    nums=[actor,10,20,0,150,150,180,20,12,0]+[65535]*16+[0]*32
    return "draw_actor "+" ".join(map(str,nums))


class BuildCrossRoomTests(unittest.TestCase):
    def setUp(self):
        self.temp=TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name)
        for n in ("SOURCE","TOOLS","FIXTURE"):
            (self.root/n).mkdir()
        self.base=self.root/"TOOLS"/builder.DOORWAY_BUILD
        self.base.mkdir()
        for name in builder.SOURCE_FILES:
            p=self.base/name
            p.parent.mkdir(parents=True,exist_ok=True)
            p.write_text(f"orig:{name}")
        (self.base/"scummvm.exe").write_bytes(b"ORIGINAL")
        (self.base/"doorway-exe.sha256").write_text(digest(b"ORIGINAL"))
        self.make=self.root/"TOOLS"/"make.exe"
        self.make.write_bytes(b"synthetic")
        self.dlls=self.root/"TOOLS"/"dlls"
        self.dlls.mkdir()

    def test_preflight_requires_original_fingerprint(self):
        result=builder.preflight(self.root,make=self.make,dlls=self.dlls)
        self.assertEqual(result["source_exe_sha256"],digest(b"ORIGINAL"))
        (self.base/"scummvm.exe").write_bytes(b"CHANGED")
        with self.assertRaisesRegex(ValueError,"fingerprint|digest"):
            builder.preflight(self.root,make=self.make,dlls=self.dlls)

    def test_new_build_never_modifies_original_pinned_executable(self):
        def fake_prepare(src,overlay):
            overlay.mkdir()
            items=[]
            for name in builder.SOURCE_FILES:
                raw=(src/name).read_bytes()
                dest=overlay/name
                dest.parent.mkdir(parents=True,exist_ok=True)
                modified=raw+b"\n// instrumented"
                dest.write_bytes(modified)
                items.append(dict(path=name,input_sha256=digest(raw),
                                  output_sha256=digest(modified)))
            return dict(files=items)
        def fake_build(args,*,cwd,env,stdout,stderr,check):
            self.assertEqual(args[-1],"-j4")
            (cwd/"scummvm.exe").write_bytes(b"NEW-LINKED")
        with (patch.object(builder,"prepare",side_effect=fake_prepare),
              patch.object(builder.subprocess,"run",side_effect=fake_build),
              patch.object(builder.subprocess,"check_output",return_value="ScummVM synthetic")):
            result=builder.build(self.root,make=self.make,dlls=self.dlls)
        self.assertEqual(result["exe_sha256"],digest(b"NEW-LINKED"))
        self.assertEqual((self.base/"scummvm.exe").read_bytes(),b"ORIGINAL")
        self.assertEqual((self.base/"engines/scumm/actor.cpp").read_text(),
                         "orig:engines/scumm/actor.cpp")
        new=Path(result["build_dir"])
        self.assertEqual((new/"cross-room-exe.sha256").read_text().strip(),digest(b"NEW-LINKED"))
        self.assertEqual(json.loads((new/"cross-room-build.json").read_text())["capture_runtime_verified"],False)


class IndexedCrossRoomTests(unittest.TestCase):
    def setUp(self):
        self.temp=TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.folder=Path(self.temp.name)/"capture"
        self.folder.mkdir()
        self.report=Path(self.temp.name)/"report"
        (self.folder/"run.json").write_text(json.dumps(
            dict(capture_mode="cross_room",indexed_rooms=[7,12])))
        for marker in ("capture.enabled","doorway.enabled"):
            (self.folder/marker).touch()
        (self.folder/"ticks.tsv").write_text("\n".join([
            row(1,7),row(2,12),row(3,7)])+"\n")
        (self.folder/"presents.tsv").write_text(
            "1\t1\t100\n2\t2\t200\n3\t3\t300\n")
        for seq in (1,2,3):
            (self.folder/f"engine-{seq:03}.bin").write_bytes(b"RAW")
            (self.folder/f"present-{seq:03}.bin").write_bytes(b"RAW")
        self.draws=[draw(7),draw(8)]

    def fake_engine(self,raw,number):
        room=(7,12,7)[number-1]
        state=[f"scene {room} {number}"]
        if room==12:state.extend(self.draws)
        front=bytes([32])*46080
        backend=front+bytes(56*320)
        return dict(top=0,state=state,wall_ms=number*100,depth_sha256=[]),\
            [bytes(768)]*4,front,front,backend

    def fake_present(self,raw,number):
        return number*100,"sdl",SimpleNamespace(size=(320,200))

    def _verify(self):
        with (patch("tools.verify_cross_room_capture.engine",side_effect=self.fake_engine),
              patch("tools.verify_cross_room_capture.present",side_effect=self.fake_present)):
            return verify(self.folder,self.report)

    def test_actor_7_and_8_present_but_fidelity_still_not_claimed(self):
        result=self._verify()
        self.assertEqual(result["status"],"indexed_capture_with_actor7_8_observed")
        self.assertEqual(result["rooms"],{"7":2,"12":1})
        self.assertEqual(result["room12_actor_draw_counts"],{"7":1,"8":1})
        self.assertEqual(result["scene_fidelity"],"NOT VALIDATED")
        self.assertEqual(result["frames_with_matching_sdl_tick"],3)
        self.assertTrue((self.report/"cross-room-indexed.json").is_file())

    def test_missing_actor_8_reports_partial_evidence_not_success(self):
        self.draws=[draw(7)]
        with self.assertRaisesRegex(ValueError,"actor 7/8"):
            self._verify()
        partial=json.loads((self.report/"cross-room-indexed.json").read_text())
        self.assertEqual(partial["status"],"partial_indexed_capture_missing_actor7_or_actor8")
        self.assertEqual(partial["scene_fidelity"],"NOT VALIDATED")

    def test_rejects_missing_frame_and_mismatched_scene(self):
        (self.folder/"engine-002.bin").unlink()
        with self.assertRaisesRegex(ValueError,"sequential"):
            self._verify()
        (self.folder/"engine-002.bin").write_bytes(b"RAW")
        original=self.fake_engine
        def wrong_scene(raw,number):
            meta,pals,back,front,backend=original(raw,number)
            meta["state"]=["scene 7 2"] if number==2 else meta["state"]
            return meta,pals,back,front,backend
        with (patch("tools.verify_cross_room_capture.engine",side_effect=wrong_scene),
              patch("tools.verify_cross_room_capture.present",side_effect=self.fake_present)):
            with self.assertRaisesRegex(ValueError,"Scene/engine tick linkage"):
                verify(self.folder,self.report)

    def test_actor_row_schema_rejects_incomplete_or_bad_values(self):
        self.assertEqual(parse_draw_actor(draw(7))["id"],7)
        with self.assertRaisesRegex(ValueError,"width"):
            parse_draw_actor("draw_actor 7 2 3")
        with self.assertRaisesRegex(ValueError,"Out-of-range"):
            parse_draw_actor(draw(7).replace("draw_actor 7 ", "draw_actor 1000 ",1))


if __name__=="__main__":
    unittest.main()
