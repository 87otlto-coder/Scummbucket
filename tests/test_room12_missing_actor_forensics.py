"""Synthetic-only indexed camera/frame counterfactuals; no DOS copyrighted art."""
from copy import deepcopy
from hashlib import sha256
import json
from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace
from unittest.mock import patch
import unittest

from scummbucket.scene_source import compose_actor_layers
from tools.diagnose_room12_missing_actor import diagnose


def digest(data):
    return sha256(data).hexdigest()


class MissingActorForensicsTests(unittest.TestCase):
    def setUp(self):
        self.tmp=TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        root=Path(self.tmp.name)
        self.capture=root/"capture"
        self.capture.mkdir()
        self.game=root/"game"
        self.game.mkdir()
        self.cmp=root/"compare.json"
        self.idx=root/"indexed.json"
        self.scene=dict(manifest=dict(dimensions=[320,144],room_sha256=digest(b"ROOM12")),
                        background=bytes(320*144),masks={})
        def costume(color):
            cel=SimpleNamespace(rel_x=0,rel_y=0,width=1,height=1,
                                slots=b"\1",move_x=0,move_y=0)
            return SimpleNamespace(force_right=False,colors=16,
                palette=bytes([0,color])+bytes(14),
                limb=lambda n,p:None if p==65535 else (0,cel))
        self.costumes={1:costume(5),20:costume(6),41:costume(7)}
        def actor(num,x):
            return dict(id=num,screen_x=x,draw_y=10,plane=0,
                        scales=[255,255],facing=180,
                        costume={1:1,7:20,8:41}[num],
                        logical_frame=0,stopped=0,cursors=[0]+[65535]*15,
                        palette_override=[255]*32)
        self.actor1=actor(1,10)
        self.a7=actor(7,20)
        self.a8=actor(8,30)
        self.rows=[
            dict(room=12,tick=150,indexed_frame=150,
                 actors=[self.actor1,self.a7,self.a8]),
            dict(room=12,tick=151,indexed_frame=151,
                 actors=[self.a7,self.a8]),
        ]
        self.predicted=compose_actor_layers(self.scene,self.costumes,[self.a7,self.a8])
        self.observed=compose_actor_layers(self.scene,self.costumes,
                                          [self.actor1,self.a7,self.a8])
        self.original_fronts={150:self.observed,151:self.observed}
        for row in self.rows:
            n=row["indexed_frame"]
            raw=("original raw %d" % n).encode()
            (self.capture/("engine-%03d.bin" % n)).write_bytes(raw)
            row["raw_sha256"]=digest(raw)
            row["front_sha256"]=digest(self.original_fronts[n])
            row["background_sha256"]=digest(self.scene["background"])
        # The original indexed gate has two records; comparison is of 151 only.
        self.indexed=dict(schema="scummbucket-cross-room-indexed-evidence/1",
                          status="indexed_capture_with_actor7_8_observed",
                          scene_fidelity="NOT VALIDATED",
                          capture=str(self.capture.resolve()),
                          frames=self.rows)
        self.comparison=dict(
            schema="scummbucket-room12-indexed-multi-actor-probe/1",
            status="PARTIAL_INDEXED_RECONSTRUCTION",
            capture=self.indexed["capture"],
            source_room_sha256=self.scene["manifest"]["room_sha256"],
            samples=1,unexplained_mismatches=1,
            frames=[dict(indexed_frame=151,tick=151,
                         draw_order=[7,8],indexed_errors=1,bbox=[10,10,11,11],
                         predicted_indexed_sha256=digest(self.predicted),
                         engine_indexed_sha256=digest(self.observed))],
        )
        self._write()

    def _write(self):
        self.idx.write_text(json.dumps(self.indexed))
        self.cmp.write_text(json.dumps(self.comparison))

    def fake_engine(self,raw,number):
        return (dict(),[bytes(768)]*4,self.scene["background"],
                self.original_fronts[number],bytes(320*200))

    def run_diagnostic(self):
        with (patch("tools.diagnose_room12_missing_actor.load_scene",return_value=self.scene),
              patch("tools.diagnose_room12_missing_actor.costumes_from_archive",
                    return_value=self.costumes),
              patch("tools.diagnose_room12_missing_actor.engine",
                    side_effect=self.fake_engine)):
            return diagnose(self.game,self.capture,self.cmp,self.idx)

    def test_identifies_missing_foreground_and_last_recorded_pose_control(self):
        original_raw=(self.capture/"engine-151.bin").read_bytes()
        result=self.run_diagnostic()
        self.assertEqual(result["status"],
                         "counterfactual_diagnostics_only_not_a_rendering_acceptance")
        self.assertEqual(result["original_residual_pixels"],1)
        self.assertEqual(result["residual_categories"],
                         {"observed_foreground_missing_from_candidate":1})
        rec=result["frames"][0]
        self.assertEqual(rec["actual_bbox"],[10,10,11,11])
        self.assertEqual(rec["adjacent_recorded_front"]["previous"]
                         ["observed_matches_at_residual_positions"],1)
        self.assertEqual(rec["nearest_recorded_actor1_counterfactuals"]
                         ["last_observed"]["candidate_errors"]
                         ["before_other_actors"]["errors"],0)
        self.assertEqual((self.capture/"engine-151.bin").read_bytes(),original_raw)

    def test_conclusion_is_not_forced_if_missing_pixels_are_some_other_object(self):
        altered=bytearray(self.observed)
        altered[10*320+10]=0
        altered[10*320+40]=9
        self.original_fronts[151]=bytes(altered)
        self.rows[1]["front_sha256"]=digest(bytes(altered))
        self.comparison["frames"][0]["indexed_errors"]=1
        self.comparison["frames"][0]["bbox"]=[40,10,41,11]
        self.comparison["frames"][0]["engine_indexed_sha256"]=digest(bytes(altered))
        self._write()
        result=self.run_diagnostic()
        self.assertEqual(result["original_residual_pixels"],1)
        self.assertEqual(result["frames"][0]
                         ["nearest_recorded_actor1_counterfactuals"]
                         ["last_observed"]["candidate_errors"]
                         ["before_other_actors"]["errors"],2)

    def test_mismatching_saved_candidate_or_front_hash_is_rejected(self):
        self.comparison["frames"][0]["predicted_indexed_sha256"]="0"*64
        self._write()
        with self.assertRaisesRegex(ValueError,"no longer reproduces"):
            self.run_diagnostic()
        self.comparison["frames"][0]["predicted_indexed_sha256"]=digest(self.predicted)
        self.rows[1]["front_sha256"]="0"*64
        self._write()
        with self.assertRaisesRegex(ValueError,"front digest"):
            self.run_diagnostic()

    def test_any_residual_frame_with_actor1_draw_is_not_diagnosed_as_absence(self):
        self.rows[1]["actors"]=[self.actor1,self.a7,self.a8]
        self.comparison["frames"][0]["draw_order"]=[1,7,8]
        self._write()
        with self.assertRaisesRegex(ValueError,"not exclusively"):
            self.run_diagnostic()


if __name__=="__main__":
    unittest.main()
