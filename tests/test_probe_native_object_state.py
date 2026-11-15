"""Read-only P4 OBIM source-probe tests, synthetic archive only."""
from hashlib import sha256
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch
import unittest

from tools.probe_native_object_state import probe
from scummbucket.inspector import _read_pair
from test_inspector import index,make_zip
from test_object_images import synthetic_resource


class NativeObjectProbeTests(unittest.TestCase):
    def setUp(self):
        self.tmp=TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.path=Path(self.tmp.name)/"synthetic.zip"
        make_zip(self.path,a=index(),b=synthetic_resource())

    def test_probes_all_states_with_original_source_indices_only(self):
        before=self.path.read_bytes()
        result=probe(self.path,room_id=1,object_id=99)
        self.assertEqual(result["status"],"success",result["diagnostics"])
        self.assertEqual(result["summary"],dict(decoded=2,failed=0,unsupported=0))
        self.assertEqual(result["object_source"]["state_tags"],["IM01","IM02"])
        self.assertEqual(result["object_source"]["script_state_pattern_count"],0)
        self.assertEqual([r["opaque_pixels"] for r in result["states"]],[0,64])
        self.assertEqual([r["transparent_pixels"] for r in result["states"]],[64,0])
        self.assertEqual([len(r["zplanes"]) for r in result["states"]],[3,3])
        self.assertTrue(all(r["status"]=="indexed_source_decoded_not_runtime_verified"
                            for r in result["states"]))
        self.assertFalse(result["runtime_state_observed"])
        self.assertFalse(result["runtime_animation_verified"])
        self.assertFalse(result["render_fidelity_verified"])
        self.assertEqual(self.path.read_bytes(),before)

    def test_corrupt_one_state_preserves_other_success_and_explicit_unsupported(self):
        make_zip(self.path,a=index(),b=synthetic_resource(bad_code=251))
        result=probe(self.path,room_id=1,object_id=99)
        self.assertEqual(result["status"],"partial",result["diagnostics"])
        self.assertEqual(result["summary"],dict(decoded=1,failed=1,unsupported=1))
        self.assertEqual(len(result["states"]),2)
        self.assertEqual(result["states"][0]["failure_code"],"STRIP_CODEC_UNSUPPORTED")
        self.assertEqual(result["states"][1]["opaque_pixels"],64)

    def test_missing_object_and_changed_reopened_source_fail_closed(self):
        missing=probe(self.path,room_id=2,object_id=99)
        self.assertEqual(missing["status"],"failed")
        self.assertEqual(missing["diagnostics"][0]["code"],"SOURCE_PREFLIGHT_FAILED")
        a,b,labela,labelb=_read_pair(self.path)
        with patch("tools.probe_native_object_state._read_pair",
                   return_value=(a,b[:-1]+bytes([b[-1]^1]),labela,labelb)):
            modified=probe(self.path,room_id=1,object_id=99)
        self.assertEqual(modified["status"],"failed")
        self.assertIn("changed",modified["diagnostics"][0]["message"])

    def test_invalid_selection_does_not_open_game(self):
        with patch("tools.probe_native_object_state.inspect",
                   side_effect=AssertionError("Must not inspect invalid selection")):
            result=probe(self.path,room_id=-1,object_id=99)
        self.assertEqual(result["status"],"failed")
        self.assertEqual(result["diagnostics"][0]["code"],"SELECTION_INVALID")


if __name__=="__main__":
    unittest.main()
