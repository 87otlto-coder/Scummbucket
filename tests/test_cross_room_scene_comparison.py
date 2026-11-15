"""Synthetic only: Room 12 source+observed actor indexed comparison boundaries."""
from hashlib import sha256
import json
from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace
from unittest.mock import patch
import unittest

from tools.compare_cross_room_scene import compare


def pose(actor,costume,color):
    live=[0,color]+[0]*30
    return dict(id=actor,screen_x=0,draw_y=0,plane=0,scales=[255,255],
                facing=180,costume=costume,logical_frame=12,stopped=0,
                cursors=[0]+[65535]*15,palette_override=live)


class Room12ComparisonTests(unittest.TestCase):
    def setUp(self):
        self.tmp=TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root=Path(self.tmp.name)/"FIXTURE"
        self.capture=self.root/"CAPTURES"/"Room7"/"cross-room-test"
        self.capture.mkdir(parents=True)
        self.report=self.root/"REPORTS"/"Room7"/"cross-room-test"
        self.report.mkdir(parents=True)
        self.game=self.root/"GAMES"/"MonkeyIsland2_DOS_VGA"
        self.game.mkdir(parents=True)
        self.dst=self.root/"REPORTS"/"P5"/"comparison"
        self.front=bytes([9])+bytes(46079)
        self.original=b"original synthetic indexed frame"
        (self.capture/"engine-001.bin").write_bytes(self.original)
        (self.capture/"run.json").write_text(json.dumps(dict(capture_mode="cross_room")))
        self.actors=[pose(7,20,7),pose(8,41,9)]
        manifest=dict(status="indexed_capture_with_actor7_8_observed",
                      scene_fidelity="NOT VALIDATED",
                      frames=[dict(room=12,indexed_frame=1,tick=200,
                        actors=self.actors,raw_sha256=sha256(self.original).hexdigest(),
                        front_sha256=sha256(self.front).hexdigest())])
        (self.report/"cross-room-indexed.json").write_text(json.dumps(manifest))
        self.scene=dict(
            manifest=dict(dimensions=[320,144],room_sha256="source-room",
                          sources=[dict(name="synthetic",sha256="a"*64)]),
            background=bytes(46080),masks={})
        cel=SimpleNamespace(rel_x=0,rel_y=0,width=1,height=1,slots=b"\1",
                            move_x=0,move_y=0)
        costume=lambda:SimpleNamespace(force_right=False,colors=16,
            palette=b"\0\4"+bytes(14),
            limb=lambda n,pos:None if pos==65535 else (0,cel))
        self.costumes={20:costume(),41:costume()}

    def fake_engine(self,raw,number):
        self.assertEqual(number,1)
        return dict(top=0,state=[]),[bytes(768)]*4,bytes(46080),self.front,bytes(64000)

    def _compare(self):
        with (patch("tools.compare_cross_room_scene.load_scene",return_value=self.scene),
              patch("tools.compare_cross_room_scene.costumes_from_archive",
                    return_value=self.costumes),
              patch("tools.compare_cross_room_scene.engine",side_effect=self.fake_engine)):
            return compare(self.game,self.capture,self.dst)

    def test_exact_indices_are_proven_only_for_the_recorded_sample(self):
        result=self._compare()
        self.assertEqual(result["status"],"recorded_route_exact_indexed_match")
        self.assertEqual(result["samples"],1)
        self.assertEqual(result["totals"]["indexed_mismatches"],0)
        self.assertEqual(result["frames"][0]["draw_order"],[7,8])
        self.assertTrue((self.dst/"engine-reference.png").is_file())
        self.assertTrue((self.dst/"indexed-differences.png").is_file())

    def test_incomplete_composition_remains_partial_with_first_mismatch(self):
        self.front=bytes([5])+bytes(46079)
        report=json.loads((self.report/"cross-room-indexed.json").read_text())
        report["frames"][0]["front_sha256"]=sha256(self.front).hexdigest()
        (self.report/"cross-room-indexed.json").write_text(json.dumps(report))
        result=self._compare()
        self.assertEqual(result["status"],"PARTIAL_INDEXED_RECONSTRUCTION")
        self.assertEqual(result["unexplained_mismatches"],1)
        self.assertEqual(result["frames"][0]["first_mismatch"],[0,0])
        self.assertEqual(result["frames"][0]["bbox"],[0,0,1,1])

    def test_input_sha_mismatch_fails_before_any_output(self):
        (self.capture/"engine-001.bin").write_bytes(b"changed")
        with self.assertRaisesRegex(ValueError,"source changed"):
            self._compare()
        self.assertFalse(self.dst.exists())

    def test_existing_comparison_output_is_not_overwritten(self):
        self.dst.mkdir(parents=True)
        with self.assertRaises(FileExistsError):
            self._compare()


if __name__=="__main__":
    unittest.main()
