from hashlib import sha256
import json
from pathlib import Path
import tempfile
import unittest
from scummbucket.scene_package import verify_source

class PackageIntegrityTests(unittest.TestCase):
    def test_tampered_bytes_and_self_rehashed_metadata_are_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp);data={'room.bin':b'ROOM1234','background.idx':b'\1'*64,'palette.rgb':bytes(768)}
            files={n:dict(size=len(b),sha256=sha256(b).hexdigest()) for n,b in data.items()}
            m=dict(schema='scumm-source-scene/0.1',room_id=12,dimensions=[8,8],room_length=8,
                room_sha256=files['room.bin']['sha256'],indexed_sha256=files['background.idx']['sha256'],
                palette_sha256=files['palette.rgb']['sha256'],masks={},files=files,scene_state=None)
            for n,b in data.items():(p/n).write_bytes(b)
            (p/'source.json').write_text(json.dumps(m))
            self.assertEqual(verify_source(p)['status'],'integrity_verified')
            (p/'background.idx').write_bytes(b'\2'*64)
            with self.assertRaisesRegex(ValueError,'integrity'):verify_source(p)
            m['files']['background.idx']['sha256']=sha256(b'\2'*64).hexdigest()
            (p/'source.json').write_text(json.dumps(m))
            with self.assertRaisesRegex(ValueError,'integrity'):verify_source(p)

    def test_extra_traversal_path_is_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp)
            (p/'source.json').write_text(json.dumps(dict(schema='scumm-source-scene/0.1',dimensions=[8,8],masks={},files={'../outside':{}})))
            with self.assertRaisesRegex(ValueError,'inventory'):verify_source(p)
