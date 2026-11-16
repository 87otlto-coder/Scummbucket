"""Add read-only before/after COST tick observations to a pinned private overlay."""
from hashlib import sha256
import argparse
import json
from pathlib import Path

from tools.instrument_room7_navigation import replace_once

INPUT_SHA256 = '70843093326d5789823e3a3aab42bad1edf61ffe8be2f420f0912c0f1ec52945'


def transform(text):
    text = text.replace('\r\n','\n')
    signature = 'void Actor::animateCostume() {\n'
    if text.count(signature) != 1:
        raise ValueError('Unexpected animateCostume signature count')
    start = text.index(signature)
    end = text.index('\n}\n',start)+2
    method = text[start:end]
    logger = '''    // ScummBucket: paired actual animation-call boundaries, no forced update.
    auto sbAnimationSnapshot = [&](const char *phase) {
        extern Common::String sbCrossRoomDraws;
        if (_vm->_game.id == GID_MONKEY2 && _vm->_game.version == 5 &&
                (_room == 7 || _room == 12) && _room == _vm->_currentRoom) {
            sbCrossRoomDraws += Common::String::format("anim_step %s %d %u %u %u %u %u %u",
                phase, _number, _costume, _animProgress, _animSpeed, _cost.stopped,
                _cost.animCounter, _cost.soundCounter);
            for (int limb = 0; limb < 16; ++limb)
                sbCrossRoomDraws += Common::String::format(" %u %u %u %u",
                    _cost.curpos[limb], _cost.start[limb], _cost.end[limb], _cost.frame[limb]);
            sbCrossRoomDraws += "\\n";
        }
    };
    sbAnimationSnapshot("before");
'''
    method = replace_once(method,'\t_animProgress++;',logger+'\t_animProgress++;')
    method = method[:-1]+'    sbAnimationSnapshot("after");\n}'
    return text[:start]+method+text[end:]


def prepare(source,destination):
    source,destination = Path(source),Path(destination)
    raw = source.read_bytes()
    if sha256(raw).hexdigest() != INPUT_SHA256:
        raise ValueError('Actor-state overlay source fingerprint mismatch')
    output = transform(raw.decode('utf-8')).encode('utf-8')
    destination.mkdir(parents=True,exist_ok=False)
    with (destination/'actor.cpp').open('xb') as out:
        out.write(output)
    report = dict(schema='scummbucket-animation-step-overlay/1',input_sha256=INPUT_SHA256,
                  output_sha256=sha256(output).hexdigest(),
                  status='SOURCE_OVERLAY_ONLY',runtime_verified=False,
                  fields='phase; id costume progress speed stopped animation_counter sound_counter; 16*(cursor start end frame)',
                  boundary='actual animateCostume entry/exit, after draw, before external script/sound resets')
    with (destination/'overlay.json').open('x',encoding='utf-8') as out:
        json.dump(report,out,indent=2)
    return report


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('source',type=Path)
    p.add_argument('destination',type=Path)
    args = p.parse_args()
    print(json.dumps(prepare(args.source,args.destination),indent=2))
