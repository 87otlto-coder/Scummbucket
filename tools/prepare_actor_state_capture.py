"""Pinned read-only actor-state overlay before the redraw early return.

No rendering calls or flag/cursor changes are added. Rows are process-order
pre-draw state snapshots, NOT assertions that the actor was drawn that tick.
Keep patched third-party files in private TOOLS, not this repository.
"""
from hashlib import sha256
import json
from pathlib import Path

from tools.instrument_room7_navigation import replace_once


ACTOR_SHA256 = '0c9e75724d42d2d0ead63a31cfecd42e3ca091281848d9de031d49cd9a091c3b'
STATE_FIELDS = ['id', 'world_x', 'world_y', 'elevation', 'screen_x', 'draw_y',
                'room', 'visible', 'need_redraw', 'need_bg_reset', 'scale_x', 'scale_y',
                'facing', 'costume', 'logical_frame', 'walkbox', 'force_clip', 'never_clip',
                'layer', 'anim_progress', 'anim_speed', 'stopped', 'plane', 'draw_to_back',
                'shadow_mode', 'top', 'bottom']


def transform(text):
    text = text.replace('\r\n', '\n')
    anchor = 'void Actor::drawActorCostume(bool hitTestMode) {\n'
    insertion = '''    // ScummBucket: observed sorted-actor state, before the redraw gate.
    extern Common::String sbCrossRoomDraws;
    if (!hitTestMode && _vm->_game.id == GID_MONKEY2 && _vm->_game.version == 5 &&
            (_room == 7 || _room == 12) && _room == _vm->_currentRoom) {
        int sbPlane = _forceClip ? _forceClip :
            (isInClass(kObjectClassNeverClip) ? 0 : _vm->getMaskFromBox(_walkbox));
        if (!_forceClip && sbPlane > _vm->_gdi->_numZBuffer - 1)
            sbPlane = _vm->_gdi->_numZBuffer - 1;
        sbCrossRoomDraws += Common::String::format(
            "state_actor %d %d %d %d %d %d %u %u %u %u %u %u %d %u %u %u %u %u %d %u %u %u %d %u %u %d %d",
            _number, _pos.x, _pos.y, _elevation,
            _pos.x - _vm->_virtscr[kMainVirtScreen].xstart, _pos.y - _elevation,
            _room, _visible, _needRedraw, _needBgReset, _scalex, _scaley,
            getFacing(), _costume, _frame, _walkbox, _forceClip,
            isInClass(kObjectClassNeverClip), _layer, _animProgress, _animSpeed,
            _cost.stopped, sbPlane, _drawToBackBuf, _shadowMode, _top, _bottom);
        for (int limb = 0; limb < 16; ++limb)
            sbCrossRoomDraws += Common::String::format(" %u", _cost.curpos[limb]);
        for (int slot = 0; slot < 32; ++slot)
            sbCrossRoomDraws += Common::String::format(" %u", _palette[slot]);
        sbCrossRoomDraws += "\\n";
    }
'''
    return replace_once(text, anchor, anchor+insertion)


def prepare(source, destination):
    source, destination = Path(source), Path(destination)
    raw = (source/'engines/scumm/actor.cpp').read_bytes()
    if sha256(raw).hexdigest() != ACTOR_SHA256:
        raise ValueError('Cross-room actor source fingerprint mismatch')
    result = transform(raw.decode('utf-8')).encode('utf-8')
    destination.mkdir(parents=True, exist_ok=False)
    path = destination/'actor.cpp'
    with path.open('xb') as out:
        out.write(result)
    report = dict(schema='scummbucket-actor-state-overlay/1',
                  status='SOURCE_OVERLAY_ONLY', input_sha256=ACTOR_SHA256,
                  output_sha256=sha256(result).hexdigest(), source_path=str(path),
                  fields=STATE_FIELDS+['16 cursors', '32 palette overrides'],
                  phase='sorted processActors call before redraw early return and before animateCostume',
                  snapshot_is_draw_operation=False, linked=False, runtime_verified=False)
    with (destination/'overlay.json').open('x', encoding='utf-8') as out:
        json.dump(report, out, indent=2)
    return report


if __name__ == '__main__':
    import argparse
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('source', type=Path)
    p.add_argument('destination', type=Path)
    args = p.parse_args()
    print(json.dumps(prepare(args.source, args.destination), indent=2))
