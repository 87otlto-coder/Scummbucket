"""Private, offline replay packages; discrepancies travel with the evidence.

Packages contain original-resource derivatives and captured state: keep them
outside Git/public uploads. No playback duration or missing draws are invented.
Hashes detect corruption, not a maliciously replaced complete package.
"""
from hashlib import sha256
import json
from pathlib import Path
import re

from .classic_costume import ClassicCostume
from .inspector import chunks
from .object_images import _decode_zplane
from .observed_scene_replay import replay_observed_frame
from .palette_probe import decode_room_background_indexed
from .scene_package import export_source, verify_source


def _json(value):
    return (json.dumps(value, indent=2, sort_keys=True) + '\n').encode('utf-8')


def export_replay_package(game, destination, comparison, sequence, costumes):
    """Save explicit samples plus source components, including non-exact samples."""
    if (comparison.get('schema') != 'scummbucket-observed-event-replay-comparison/1' or
            sequence.get('schema') != 'scummbucket-observed-scene-sequence/1' or
            comparison['room_id'] != sequence['room_id'] or
            comparison['samples'] != len(sequence['frames']) or
            comparison['room_sha256'] != sequence['source_room_sha256']):
        raise ValueError('Comparison/sequence binding mismatch')
    dest = Path(destination)
    dest.mkdir(parents=True, exist_ok=False)
    source = export_source(game, comparison['room_id'], dest/'source')
    if source['room_sha256'] != comparison['room_sha256'] or source['sources'] != comparison['original_archives']:
        raise ValueError('Original archive changed before replay packaging')
    contents = {'events.json': _json(sequence), 'comparison.json': _json(comparison)}
    for number, costume in costumes.items():
        if type(number) is not int or not 0 <= number <= 65535:
            raise ValueError('Invalid original costume identity')
        contents[f'costume-{number:05}.bin'] = costume.data
    records = {}
    for name, content in contents.items():
        with (dest/name).open('xb') as out:
            out.write(content)
        records[name] = dict(size=len(content), sha256=sha256(content).hexdigest())
    manifest = dict(schema='scummbucket-observed-replay-package/1', room_id=source['room_id'],
                    source_manifest_sha256=sha256((dest/'source/source.json').read_bytes()).hexdigest(),
                    files=records, scene_acceptance=comparison['status'],
                    boundary='Private copyrighted source derivatives and observed state. Do not publish.',
                    timing='sample ordering only; native playback cadence not established')
    with (dest/'replay.json').open('xb') as out:
        out.write(_json(manifest))
    return verify_replay_package(dest)


def load_replay_package(destination):
    """Check inventory and independently re-decode source room image/masks."""
    dest = Path(destination)
    if dest.is_symlink() or (dest/'source').is_symlink() or (dest/'replay.json').is_symlink():
        raise ValueError('Replay package symlink refused')
    manifest = json.loads((dest/'replay.json').read_text(encoding='utf-8'))
    if manifest.get('schema') != 'scummbucket-observed-replay-package/1':
        raise ValueError('Unknown replay package schema')
    records = manifest['files']
    if (not isinstance(records, dict) or not {'events.json', 'comparison.json'} <= set(records) or
            len(records) > 258 or any(name not in ('events.json', 'comparison.json') and
              not re.fullmatch(r'costume-[0-9]{5}\.bin', name) for name in records)):
        raise ValueError('Invalid replay file inventory')
    if {p.name for p in dest.iterdir()} != set(records) | {'source', 'replay.json'}:
        raise ValueError('Unexpected replay package entry')
    contents = {}
    for name, record in records.items():
        path = dest/name
        if path.is_symlink() or not path.is_file() or not 0 <= path.stat().st_size <= 64_000_000:
            raise ValueError('Invalid or excessive replay file')
        data = path.read_bytes()
        if len(data) != record['size'] or sha256(data).hexdigest() != record['sha256']:
            raise ValueError(f'Replay integrity mismatch: {name}')
        contents[name] = data
    source_path = dest/'source/source.json'
    if source_path.is_symlink() or sha256(source_path.read_bytes()).hexdigest() != manifest['source_manifest_sha256']:
        raise ValueError('Source manifest integrity mismatch')
    verify_source(dest/'source')
    sm = json.loads(source_path.read_text(encoding='utf-8'))
    if {p.name for p in (dest/'source').iterdir()} != set(sm['files']) | {'source.json'}:
        raise ValueError('Unexpected source package entry')
    room = (dest/'source/room.bin').read_bytes()
    bg = decode_room_background_indexed(room, room_offset=0, room_length=len(room))
    if (bg['indexed_pixels'] != (dest/'source/background.idx').read_bytes() or
            bg['initial_palette'] != (dest/'source/palette.rgb').read_bytes() or
            [bg['width'], bg['height']] != sm['dimensions']):
        raise ValueError('Source image re-decode mismatch')
    im = bg['source']['im00_offset']
    layers = chunks(room, im+8, im+int.from_bytes(room[im+4:im+8], 'big'), 'IM00')
    masks = {int(n.tag[2:]): _decode_zplane(room, n, width=bg['width'], height=bg['height'])
             for n in layers if n.tag.startswith('ZP') and n.tag[2:].isdigit()}
    if set(masks) != {int(z) for z in sm['masks']} or any(
            mask != (dest/f'source/ZP{plane:02}.mask').read_bytes() for plane, mask in masks.items()):
        raise ValueError('Source depth re-decode mismatch')
    scene = dict(manifest=sm, background=bg['indexed_pixels'], palette=bg['initial_palette'], masks=masks)
    costumes = {int(name[8:13]): ClassicCostume(data) for name, data in contents.items()
                if name.startswith('costume-')}
    comparison = json.loads(contents['comparison.json'])
    sequence = json.loads(contents['events.json'])
    if (comparison.get('schema') != 'scummbucket-observed-event-replay-comparison/1' or
            sequence.get('schema') != 'scummbucket-observed-scene-sequence/1' or
            not isinstance(sequence.get('frames'), list) or not 0 < len(sequence['frames']) <= 1000 or
            sm['room_id'] != manifest['room_id'] or sm['room_id'] != comparison['room_id'] or
            sm['room_id'] != sequence['room_id'] or comparison['room_sha256'] != sm['room_sha256'] or
            sequence['source_room_sha256'] != sm['room_sha256'] or
            comparison['indexed_report_sha256'] != sequence['indexed_report_sha256'] or
            comparison['samples'] != len(sequence['frames']) or
            len(comparison['frames']) != len(sequence['frames']) or
            manifest['scene_acceptance'] != comparison['status']):
        raise ValueError('Replay source/event/comparison binding mismatch')
    return scene, costumes, sequence, comparison


def verify_replay_package(destination):
    """Re-render without game installation/capture and retain reference limitations.

    Candidate hashes are checked against the saved original comparison. Its
    engine-reference hashes/errors remain historical evidence, not a fresh
    direct comparison to raw frontbuffers, which this package does not contain.
    """
    scene, costumes, sequence, comparison = load_replay_package(destination)
    previous = (-1, -1)
    for packet, expected in zip(sequence['frames'], comparison['frames']):
        identity = (packet['events'][0]['tick'], packet['indexed_frame'])
        if identity <= previous:
            raise ValueError('Replay observed sample order regression')
        previous = identity
        result = replay_observed_frame(scene, costumes, packet)
        if (result['indexed_frame'] != expected['indexed_frame'] or result['tick'] != expected['tick'] or
                result['raw_sha256'] != expected['raw_sha256'] or
                result['indexed_sha256'] != expected['predicted_indexed_sha256'] or
                result['palette_sha256'] != expected['predicted_palette_sha256']):
            raise ValueError('Offline replay differs from original comparison')
    return dict(status='offline_replay_reproduced', room_id=scene['manifest']['room_id'],
                frames=len(sequence['frames']), historical_scene_acceptance=comparison['status'],
                historical_exact_frames=comparison['exact_frames'],
                historical_indexed_errors=comparison['indexed_errors'],
                raw_reference_revalidated=False, source_images_redecoded=True,
                native_timing_verified=False)
