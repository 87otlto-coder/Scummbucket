"""Synthetic cross-room portable animation acceptance tests (no private art)."""
from hashlib import sha256
from io import BytesIO
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from PIL import Image

import scummbucket.room23_portable_animation as portable
from scummbucket.native_animation_common import (
    embed_segment_timeline, inspect_indexed_png
)
from scummbucket.room23_capture_research import (
    parse_room23_hook_log, _split_on_clock_discontinuities
)
from tools.verify_room23_portable_animation import verify


def digest(data):
    return sha256(data).hexdigest()


class Room23PortableAnimationTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.export=Path(self.tmp.name)/"native"
        self.export.mkdir()
        self.log=Path(self.tmp.name)/"capture.raw.log"
        self.index=bytes([176])*(320*144)
        self.plane_hash=digest(self.index)
        self.palette=bytes(range(256))*3
        self.times=[100,200,13000,13100]
        self.samples=[]
        lines=[f"SBP4|BEGIN|23|0|{self.palette.hex()}"]
        for i,ms in enumerate(self.times,1):
            variant=bytearray(self.palette)
            variant[3:6]=bytes([i,0,0])
            current=bytes(variant)
            lines.append(f"SBP4|SAMPLE|{i}|6|6|{ms}|{current.hex()}")
            img=Image.frombytes("P",(320,144),self.index)
            img.putpalette(current)
            path=self.export/f"sample-{i:03d}.png"
            img.save(path)
            self.samples.append(dict(
                sequence=i,file=path.name,millis=ms,offset_ms=ms,
                until_next_ms=(self.times[i]-ms if i<len(self.times) else None),
                timer_pair=[6,6],rotation_ids=[],
                palette_sha256=digest(current),
                png_sha256=digest(path.read_bytes()),
            ))
        self.log.write_text("\n".join(lines)+"\n",encoding="ascii")
        capture=parse_room23_hook_log(self.log.read_bytes())
        self.gaps=_split_on_clock_discontinuities(capture["samples"])[1]
        self.manifest={
            "schema":"room23-background/1","room":23,"size":[320,144],
            "index_sha256":self.plane_hash,
            "archive_pair":[["MONKEY2.000",portable.INDEX_ARCHIVE_SHA],
                            ["MONKEY2.001",portable.KNOWN_DOS_VGA_MI2_SHA256]],
            "first_sample_equivalent_update":331,"calibration_samples":2,
            "heldout_matches":2,"capture_complete":False,"stop_reason":"missing_end",
            "begin_millis":0,"raw_sha256":digest(self.log.read_bytes()),
            "clock_gaps":self.gaps,"frames":self.samples,
        }
        self._manifest()

    def _manifest(self):
        (self.export/"manifest.json").write_text(json.dumps(self.manifest))

    def _prepare(self):
        with patch.object(portable,"INDEX_SHA",self.plane_hash):
            return portable.prepare(self.export,self.log)

    def _package(self):
        with patch.object(portable,"INDEX_SHA",self.plane_hash):
            return portable.package(self.export,self.log)

    def test_room_23_trace_segments_and_offline_html(self):
        result,html=self._prepare()
        self.assertEqual(result["frame_count"],4)
        self.assertEqual(result["mode"],"palette_background_only")
        self.assertFalse(result["capture_complete"])
        self.assertEqual([(s["first"],s["last"]) for s in result["segments"]],[(1,2),(3,4)])
        self.assertEqual(result["segments"][1]["gap_ms_before"],12800)
        self.assertEqual(html.count("data:image/png;base64,"),4)
        self.assertIn('"first":3,"last":4,"gap_ms_before":12800',html)
        self.assertIn("Background only",html)
        self.assertNotIn("__TIMELINE__",html)

    def test_package_preserves_originals_and_refuses_overwrite(self):
        before=(self.export/"manifest.json").read_bytes()
        original=(self.export/"sample-001.png").read_bytes()
        result=self._package()
        self.assertEqual(result["frame_count"],4)
        self.assertEqual((self.export/"manifest.json").read_bytes(),before)
        self.assertEqual((self.export/"sample-001.png").read_bytes(),original)
        self.assertTrue((self.export/"play-standalone.html").exists())
        self.assertTrue((self.export/"animation.json").exists())
        with self.assertRaises(FileExistsError):
            self._package()

    def test_readonly_roundtrip_audit_and_tamper_rejection(self):
        self._package()
        with patch.object(portable,"INDEX_SHA",self.plane_hash):
            result=verify(self.export,self.log)
            self.assertEqual(result["status"],"room23_native_palette_package_verified")
            self.assertEqual(result["frame_count"],4)
            self.assertEqual(result["segment_count"],2)
            (self.export/"play-standalone.html").write_text("tampered")
            with self.assertRaisesRegex(ValueError,"HTML differs"):
                verify(self.export,self.log)

    def test_rejects_forged_holdout_count(self):
        self.manifest["heldout_matches"]=1
        self._manifest()
        with self.assertRaisesRegex(ValueError,"Held-out sample count"):
            self._prepare()

    def test_rejects_wrong_raw_capture(self):
        self.log.write_text(self.log.read_text().replace("|6|6|100|","|6|5|100|"))
        with self.assertRaisesRegex(ValueError,"trace hash differs"):
            self._prepare()

    def test_rejects_wrong_png_and_palette(self):
        path=self.export/"sample-002.png"
        original=path.read_bytes()
        path.write_bytes(original+b"extra")
        with self.assertRaisesRegex(ValueError,"PNG file digest/format mismatch"):
            self._prepare()
        path.write_bytes(original)
        self.samples[1]["palette_sha256"]="f"*64
        self._manifest()
        with self.assertRaisesRegex(ValueError,"palette mismatch"):
            self._prepare()

    def test_rejects_missing_source_frame(self):
        (self.export/"sample-003.png").unlink()
        with self.assertRaises(FileNotFoundError):
            self._prepare()

    def test_historical_enriched_clock_gap_requires_original_source(self):
        # The real 87-frame export has extra source-CYCL observations
        # which cannot be inferred from an SBP4 timestamp-only trace.
        cycles=[dict(id=1,start_color=1,end_color=2,flags=0,rate_raw=16384,offset=0)]
        self.manifest["source_cycles"]=cycles
        self.manifest["source_clut_sha256"]=digest(self.palette)
        historical=dict(self.gaps[0])
        historical.update(
            source_cycle_colors_reinitialized_at_first_post_gap_sample=False,
            changed_cycling_indices_across_gap=1,
        )
        self.manifest["clock_gaps"]=[historical]
        self._manifest()
        with self.assertRaisesRegex(ValueError,"pass --game"):
            self._prepare()
        with patch.object(portable,"_load_source_room23",return_value=(self.palette,cycles)):
            with patch.object(portable,"INDEX_SHA",self.plane_hash):
                result,html=portable.prepare(self.export,self.log,game="synthetic-original")
                self.assertEqual(result["clock_gaps"],[historical])
                self.assertEqual(result["frame_count"],4)
                self.assertEqual(html.count("data:image/png;base64,"),4)
                pkg=portable.package(self.export,self.log,game="synthetic-original")
                self.assertEqual(pkg["clock_gaps"],[historical])
                audit=verify(self.export,self.log,game="synthetic-original")
                self.assertEqual(audit["status"],"room23_native_palette_package_verified")

    def test_historical_enriched_clock_gap_tampering_rejected(self):
        cycles=[dict(id=1,start_color=1,end_color=2,flags=0,rate_raw=16384,offset=0)]
        self.manifest["source_cycles"]=cycles
        self.manifest["source_clut_sha256"]=digest(self.palette)
        historical=dict(self.gaps[0])
        historical.update(
            source_cycle_colors_reinitialized_at_first_post_gap_sample=False,
            changed_cycling_indices_across_gap=1,
        )
        with patch.object(portable,"_load_source_room23",return_value=(self.palette,cycles)):
            for tampered in (
                {**historical,"changed_cycling_indices_across_gap":14},
                {**historical,"source_cycle_colors_reinitialized_at_first_post_gap_sample":True},
                {**historical,"interpretation":"room_reset_proven"},
            ):
                self.manifest["clock_gaps"]=[tampered]
                self._manifest()
                with self.subTest(tampered=tampered):
                    with self.assertRaisesRegex(ValueError,"gap annotations"):
                        self._prepare()

    def test_historical_clut_and_cycle_provenance_mismatch_rejected(self):
        cycles=[dict(id=1,start_color=1,end_color=2,flags=0,rate_raw=16384,offset=0)]
        self.manifest["source_cycles"]=cycles
        self.manifest["source_clut_sha256"]=digest(self.palette)
        historical=dict(self.gaps[0])
        historical.update(
            source_cycle_colors_reinitialized_at_first_post_gap_sample=False,
            changed_cycling_indices_across_gap=1,
        )
        self.manifest["clock_gaps"]=[historical]
        self._manifest()
        with patch.object(portable,"_load_source_room23",
                          return_value=(bytes(768),cycles)):
            with self.assertRaisesRegex(ValueError,"Source CLUT or CYCL"):
                self._prepare_enriched()
        with patch.object(portable,"_load_source_room23",
                          return_value=(self.palette,[])):
            with self.assertRaisesRegex(ValueError,"Source CLUT or CYCL"):
                self._prepare_enriched()

    def _prepare_enriched(self):
        with patch.object(portable,"INDEX_SHA",self.plane_hash):
            return portable.prepare(self.export,self.log,game="synthetic-original")

    def test_rejects_clock_gap_mutation(self):
        self.manifest["clock_gaps"]=[]
        self._manifest()
        with self.assertRaisesRegex(ValueError,"gap annotations"):
            self._prepare()

    def test_rejects_unproven_palette_phase(self):
        self.manifest["heldout_matches"]=0
        self._manifest()
        with self.assertRaisesRegex(ValueError,"holdout evidence"):
            self._prepare()

    def test_rejects_frame_timestamp_change(self):
        self.samples[1]["millis"]=207
        self._manifest()
        with self.assertRaisesRegex(ValueError,"timestamps"):
            self._prepare()

    def test_shared_indexed_integrity_and_serialization(self):
        path=self.export/"sample-001.png"
        inspect_indexed_png(
            path,size=(320,144),index_sha=self.plane_hash,
            palette_sha=self.samples[0]["palette_sha256"],
            png_sha=self.samples[0]["png_sha256"])
        with self.assertRaisesRegex(ValueError,"PNG file digest/format mismatch"):
            inspect_indexed_png(path,size=(320,144),
                                index_sha=self.plane_hash,
                                palette_sha=self.samples[0]["palette_sha256"],
                                png_sha="0"*64)
        self.assertEqual(embed_segment_timeline("a:X",[{"f":1}],marker="X"),'a:[{"f":1}]')
        with self.assertRaisesRegex(ValueError,"exactly one"):
            embed_segment_timeline("no marker",[{"f":1}],marker="X")


if __name__=="__main__":
    unittest.main()
