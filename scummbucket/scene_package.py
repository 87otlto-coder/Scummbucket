"""Private source-package prototype; integrity checks are not scene fidelity."""
from hashlib import sha256
import json
from pathlib import Path
from .scene_source import load_scene

def export_source(game, room_id, destination):
    scene=load_scene(game,room_id)
    dest=Path(destination)
    dest.mkdir(parents=True,exist_ok=False)
    files={'room.bin':scene['room_bytes'],'background.idx':scene['background'],'palette.rgb':scene['palette']}
    files.update({f'ZP{z:02}.mask':m for z,m in scene['masks'].items()})
    records={}
    for name,data in files.items():
        with (dest/name).open('xb') as f:f.write(data)
        records[name]=dict(size=len(data),sha256=sha256(data).hexdigest())
    manifest=dict(scene['manifest'],files=records,
        package_boundary='Private original-resource derivatives. Not distributable game assets. No automatic playback.',
        fidelity_status='VALIDATION PENDING',integrity_status='exported',
        scene_state=None,playback_evidence=None)
    with (dest/'source.json').open('x',encoding='utf8') as f:json.dump(manifest,f,indent=2)
    return manifest

def verify_source(destination):
    dest=Path(destination)
    m=json.loads((dest/'source.json').read_text(encoding='utf8'))
    if m.get('schema')!='scumm-source-scene/0.1':raise ValueError('Unknown source schema')
    w,h=m['dimensions']
    if type(w) is not int or type(h) is not int or not 0<w<=2048 or not 0<h<=1024:
        raise ValueError('Invalid source dimensions')
    required={'room.bin','background.idx','palette.rgb'}|{f'ZP{int(z):02}.mask' for z in m['masks']}
    if set(m['files'])!=required:raise ValueError('Unexpected source file inventory')
    expected={'room.bin':m['room_sha256'],'background.idx':m['indexed_sha256'],'palette.rgb':m['palette_sha256']}
    sizes={'room.bin':m['room_length'],'background.idx':w*h,'palette.rgb':768}
    for z,r in m['masks'].items():
        expected[f'ZP{int(z):02}.mask']=r['sha256'];sizes[f'ZP{int(z):02}.mask']=w*h
    for name in required:
        if (dest/name).is_symlink():raise ValueError('Source file symlink refused')
        data=(dest/name).read_bytes();r=m['files'][name]
        if len(data)!=r['size'] or len(data)!=sizes[name] or sha256(data).hexdigest()!=r['sha256'] or r['sha256']!=expected[name]:
            raise ValueError(f'Source integrity mismatch: {name}')
    return dict(status='integrity_verified',room_id=m['room_id'],files=len(required),
                scene_fidelity='VALIDATION PENDING',runtime_state_present=m['scene_state'] is not None)
