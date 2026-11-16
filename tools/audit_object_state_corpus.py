"""Read-only native-object corpus validation; emits hashes/counts, never pixels.

Compares native indices/opacity with the existing P2 RGBA export assembly.
Both paths share low-level strip/mask decoders: agreement is a regression
consistency check, not independent runtime fidelity or script verification.
"""
import argparse
from collections import Counter
from hashlib import sha256
from io import BytesIO
import json
from pathlib import Path

from PIL import Image

from scummbucket.inspector import inspect, _read_pair, XOR_KEY
from scummbucket.native_object_state import decode_indexed_object_state
from scummbucket.object_images import decode_object_state


def audit(game):
    inv = inspect(game)
    if inv['status'] != 'success':
        raise ValueError('Original archive inspection failed')
    index, resource, _, _ = _read_pair(game)
    if [sha256(b).hexdigest() for b in (index, resource)] != [s['sha256'] for s in inv['sources']]:
        raise ValueError('Original archive changed after inspection')
    decoded = bytes(b ^ XOR_KEY for b in resource)
    resources = inv['resources']['resource_inventory']
    totals, codecs, failures = Counter(), Counter(), Counter()
    rows = []
    for room in inv['scene_inventory']['rooms']:
        totals['rooms'] += 1
        nodes = [n for n in resources if n['room_id'] == room['room_id']]
        palettes = [n for n in nodes if n['tag'] == 'CLUT']
        transparent = [n for n in nodes if n['tag'] == 'TRNS']
        for obj in room['objects']:
            totals['objects'] += 1
            image = obj.get('image')
            if image is None:
                totals['objects_without_image'] += 1
                continue
            tags = image['image_state_tags']
            if not tags:
                totals['objects_without_stored_states'] += 1
                continue
            totals['objects_with_stored_states'] += 1
            for tag in tags:
                row = dict(room_id=room['room_id'], object_id=obj['object_id'],
                           state_tag=tag, obim_offset=image['source_offset'], status='failed')
                rows.append(row)
                totals['states_attempted'] += 1
                try:
                    if len(palettes) != 1 or palettes[0]['length'] < 776 or len(transparent) != 1 or transparent[0]['length'] < 9:
                        raise ValueError('Missing/ambiguous room CLUT/TRNS')
                    pal = decoded[palettes[0]['offset']+8:palettes[0]['offset']+776]
                    trns = decoded[transparent[0]['offset']+8]
                    state = decode_indexed_object_state(decoded, obim_offset=image['source_offset'],
                                                        state_tag=tag, transparent_color=trns)
                    row.update(dimensions=[state['width'], state['height']],
                               indexed_sha256=state['indexed_sha256'], opacity_sha256=state['opacity_sha256'],
                               transparent_pixels=state['opacity'].count(0),
                               masks={t: sha256(m).hexdigest() for t, m in state['masks'].items()})
                    codecs.update(str(s['codec']) for s in state['strip_codecs'])
                    _, png, masks = decode_object_state(decoded, obim_offset=image['source_offset'],
                                                        state_tag=tag, palette=pal, transparent_color=trns)
                    with Image.open(BytesIO(png)) as im:
                        legacy = im.convert('RGBA').tobytes()
                    predicted = bytearray()
                    for idx, alpha in zip(state['pixels'], state['opacity']):
                        predicted.extend(pal[idx*3:idx*3+3]+b'\xff' if alpha else bytes(4))
                    rgba_errors = sum(a != b for a, b in zip(predicted, legacy))
                    if len(predicted) != len(legacy):
                        raise ValueError('RGBA buffer length disagreement')
                    mask_errors = 0
                    if set(masks) != set(state['masks']):
                        raise ValueError('Depth mask inventory disagreement')
                    for plane, png in masks.items():
                        with Image.open(BytesIO(png)) as im:
                            ref = im.tobytes()
                        native = state['masks'][plane]
                        if len(ref) != len(native):
                            raise ValueError('Depth mask length disagreement')
                        mask_errors += sum(a != b for a, b in zip(native, ref))
                    row.update(rgba_byte_errors=rgba_errors, mask_pixel_errors=mask_errors,
                               decoded_pixels=len(state['pixels']))
                    totals['rgba_byte_errors'] += rgba_errors
                    totals['mask_pixel_errors'] += mask_errors
                    totals['decoded_pixels'] += len(state['pixels'])
                    if rgba_errors or mask_errors:
                        raise ValueError('Native/legacy output assembly disagreement')
                    row['status'] = 'source_decode_consistent_not_runtime_verified'
                    totals['states_consistent'] += 1
                except Exception as exc:
                    row.update(code=getattr(exc, 'code', 'CORPUS_STATE_FAILED'),
                               message=f'{type(exc).__name__}: {exc}')
                    totals['states_failed'] += 1
                    failures[row['code']] += 1
    return dict(schema='scummbucket-native-object-corpus-audit/1',
                status='source_consistency_passed' if rows and not totals['states_failed'] else 'PARTIAL' if rows else 'NO_STATES',
                original_archives=inv['sources'], summary=dict(totals),
                strip_codecs=dict(sorted(codecs.items())), failures=dict(sorted(failures.items())),
                evidence='archive_decode_and_shared_decoder_regression_consistency',
                runtime_fidelity_verified=False, runtime_state_selection_verified=False, states=rows)


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--game', type=Path, required=True)
    p.add_argument('--output', type=Path, required=True)
    args = p.parse_args()
    if args.output.exists() or args.output.is_symlink():
        p.error('Output already exists')
    result = audit(args.game)
    with args.output.open('x', encoding='utf-8') as out:
        json.dump(result, out, indent=2)
    print(json.dumps({k: v for k, v in result.items() if k not in ('states', 'original_archives')}, indent=2))
    return 0 if result['status'] == 'source_consistency_passed' else 2


if __name__ == '__main__':
    raise SystemExit(main())
