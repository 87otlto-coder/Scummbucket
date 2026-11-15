"""No fixture or private media required for indexed residual triage tests."""
from copy import deepcopy
from hashlib import sha256
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from tools.triage_room12_residuals import summarize,read_and_summarize


class ResidualTriageTests(unittest.TestCase):
    def setUp(self):
        def actor(num, cursor=0):
            return dict(id=num,costume={1:1,7:20,8:41}[num],
                        screen_x=num*10,draw_y=100,plane=0,
                        scales=[255,255],facing=180,logical_frame=0,stopped=0,
                        cursors=[cursor]+[65535]*15,
                        palette_override=[255]*32)
        self.rows=[]
        specs=[
            (150,[actor(7),actor(1),actor(8)],0,0,0),
            (151,[actor(7,1),actor(1),actor(8)],3,5,2),
            (152,[actor(7,1),actor(8)],1,2,1),
        ]
        self.matches=[]
        for tick,actors,errors,no_mask,changed in specs:
            digest=sha256(str(tick).encode("ascii")).hexdigest()
            self.rows.append(dict(room=12,tick=tick,indexed_frame=tick,
                                  front_sha256=digest,actors=actors))
            self.matches.append(dict(indexed_frame=tick,tick=tick,
                  engine_indexed_sha256=digest,draw_order=[a["id"] for a in actors],
                  indexed_errors=errors,mask_disabled_errors=no_mask,
                  source_background_errors=0,mask_changed_pixels=changed,
                  bbox=None if errors==0 else [10,30,12,31],
                  first_mismatch=None if errors==0 else [10,30]))
        self.indexed=dict(schema="scummbucket-cross-room-indexed-evidence/1",
            status="indexed_capture_with_actor7_8_observed",
            scene_fidelity="NOT VALIDATED",capture="/private/cross-room-fixture",
            frames=self.rows)
        self.comparison=dict(schema="scummbucket-room12-indexed-multi-actor-probe/1",
            status="PARTIAL_INDEXED_RECONSTRUCTION",
            capture=self.indexed["capture"],
            frames=self.matches,samples=3,indexed_pixel_observations=138240,
            totals=dict(indexed_mismatches=4,unmasked_mismatches=7,
                        source_background_mismatches=0,pixels_modified_by_mask=3),
            unexplained_mismatches=4)

    def test_reports_true_frame_counts_state_groups_and_negative_control(self):
        result=summarize(self.comparison,self.indexed)
        self.assertEqual(result["status"],
                         "derived_metadata_diagnostics_not_scene_acceptance")
        self.assertEqual(result["frames"],3)
        self.assertEqual(result["exact_frames"],1)
        self.assertEqual(result["residual_pixels"],4)
        self.assertEqual(result["median_residuals_per_frame"],1)
        self.assertEqual(result["p90_residuals_per_frame"],3)
        self.assertEqual(result["worst_frames"][0]["tick"],151)
        self.assertEqual(result["actor7_state_count"],2)
        self.assertEqual(result["draw_order_group_count"],2)
        self.assertEqual(result["mask_changed_pixels"],3)
        self.assertEqual(result["masked_errors_eliminated"],3)
        self.assertTrue(result["all_mask_changes_reduce_errors"])
        self.assertEqual(result["error_runs_count"],1)
        self.assertEqual(result["largest_error_runs"][0]["frames"],2)

    def test_refuses_invented_tick_duplicate_frames_or_modified_front_hash(self):
        for change in ("tick","duplicate","front"):
            comp=deepcopy(self.comparison)
            if change=="tick":
                comp["frames"][1]["tick"]=1024
            elif change=="duplicate":
                comp["frames"][1]["indexed_frame"]=150
            else:
                comp["frames"][1]["engine_indexed_sha256"]="0"*64
            with self.subTest(change=change):
                with self.assertRaisesRegex(ValueError,"mismatch|Duplicate"):
                    summarize(comp,self.indexed)

    def test_refuses_mutated_aggregate_or_incomplete_frames(self):
        comp=deepcopy(self.comparison)
        comp["totals"]["indexed_mismatches"]=5
        with self.assertRaisesRegex(ValueError,"aggregate"):
            summarize(comp,self.indexed)
        comp=deepcopy(self.comparison)
        comp["frames"].pop()
        with self.assertRaisesRegex(ValueError,"Missing"):
            summarize(comp,self.indexed)

    def test_explicit_json_provenance_and_read_only_behavior(self):
        with TemporaryDirectory() as tmp:
            c=Path(tmp)/"comparison.json"
            i=Path(tmp)/"indexed.json"
            c.write_text(json.dumps(self.comparison),encoding="utf-8")
            i.write_text(json.dumps(self.indexed),encoding="utf-8")
            before=(c.read_bytes(),i.read_bytes())
            output=read_and_summarize(c,i)
            self.assertEqual(output["comparison_json_sha256"],sha256(before[0]).hexdigest())
            self.assertEqual(output["indexed_json_sha256"],sha256(before[1]).hexdigest())
            self.assertEqual(before,(c.read_bytes(),i.read_bytes()))

    def test_remaining_mask_errors_not_hidden(self):
        comp=deepcopy(self.comparison)
        comp["frames"][1]["mask_disabled_errors"]=4
        comp["totals"]["unmasked_mismatches"]=6
        output=summarize(comp,self.indexed)
        self.assertFalse(output["all_mask_changes_reduce_errors"])
        self.assertEqual(output["residual_pixels"],4)


if __name__=="__main__":
    unittest.main()
