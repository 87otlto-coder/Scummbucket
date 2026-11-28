"""Patch a disposable copy of the pinned CrossRoom ScummVM source."""
import argparse
from pathlib import Path

def prepare(root):
    if not root.name.startswith('ScummVM-MI2-iMUSE-Trace-'):
        raise ValueError('expected dedicated probe copy')
    changes = {}

    def insert(file, anchor, snippet, before=False):
        path = root / file
        text = changes.get(path) or path.read_text(encoding='utf-8')
        if text.count(anchor) != 1 or snippet in text:
            raise ValueError(f'unexpected source anchor in {file}: {anchor}')
        changes[path] = text.replace(anchor, snippet + anchor if before else anchor + snippet)

    insert('engines/scumm/scumm.cpp', '\tscummLoop_handleSound();\n\n\tcamera._last', '''
    static uint32 probeStart = 0;
    static bool probeDoor = false;
    if (_game.id == GID_MONKEY2 && _currentRoom == 7 && !probeDoor) {
        if (!probeStart) {
            probeStart = _system->getMillis();
            if (!_sound->isSoundRunning(101)) {
                warning("SBM fixture_start sound=101");
                _sound->startSound(101);
            }
        } else if (_system->getMillis() - probeStart >= 1000 && _sound->isSoundRunning(101)) {
            probeDoor = true;
            warning("SBM entry room=7 script=200");
            runScript(200, 0, 0, nullptr);
        }
    }
''', before=True)
    insert('engines/scumm/script_v5.cpp',
           '\top = _opcode;\n\tscript = getVarOrDirectByte(PARAM_1);\n\n\tgetWordVararg(data);', '''
    if (_game.id == GID_MONKEY2 && script == 96)
        warning("SBM script id=96 from=%d to=%d", data[0], data[1]);''')
    insert('engines/scumm/sound.cpp', '\t\t\t_fileHandle->read(ptr, best_size);', '''
            if (_game.id == GID_MONKEY2 && (idx == 101 || idx == 103))
                warning("SBM rendition sound=%u tag=%c%c%c%c", idx, ptr[0], ptr[1], ptr[2], ptr[3]);''')
    insert('engines/scumm/imuse/imuse.cpp',
           '\t\tdoCommand_internal(p[1], p[2], p[3], p[4], p[5], p[6], p[7], 0);', '''
        if (id == 101)
            warning("SBM release marker=%u command=%u sound=%u a2=%u a3=%u a4=%u", data, p[1], p[2], p[3], p[4], p[5]);
''', before=True)
    insert('engines/scumm/imuse/imuse.cpp', 'int IMuseInternal::enqueue_trigger(int sound, int marker) {', '''
    if (sound == 101 || sound == 103)
        warning("SBM enqueue_trigger sound=%d marker=%d", sound, marker);''')
    insert('engines/scumm/imuse/imuse_player.cpp', '\t_parser->setTrack(_track_index);', '''
    if (sound == 101 || sound == 103)
        warning("SBM sequence sound=%d player=%p parser=%p track=%u tick=%u reset=%d",
                sound, (void *)this, (void *)_parser, _track_index, _parser->getTick(), reset_vars);''')
    insert('engines/scumm/imuse/imuse_player.cpp',
           "\t// Is this the hook I'm waiting for?\n\tif (cmd && _hook._jump[0] != cmd)", '''
    if (_id == 101 || _id == 103)
        warning("SBM hook sound=%u track=%u hook=%u armed=%u target_track=%u beat=%u tick=%u",
                _id, _track_index, cmd, _hook._jump[0], track, beat, tick);
''', before=True)
    insert('engines/scumm/imuse/imuse_player.cpp',
           '\tturn_off_pedals();\n\treturn true;\n}\n\nbool Player::setLoop', '''
    if (_id == 101 || _id == 103)
        warning("SBM jump sound=%u parser=%p active_track=%u target_tick=%u tick=%u",
                _id, (void *)_parser, _track_index, (beat - 1) * TICKS_PER_BEAT + tick, _parser->getTick());
''', before=True)
    insert('audio/midiparser.cpp', '\t\t\tbool ret = processEvent(info);', '''
            if (info.event == 0xF0 && info.length > 3 && info.ext.data[0] == 0x7D &&
                    (info.ext.data[1] == 48 || info.ext.data[1] == 64))
                warning("SBM dispatch parser=%p event_tick=%u opcode=%u operand=%u",
                        (void *)this, eventTick, info.ext.data[1], info.ext.data[3]);
''', before=True)
    for path, text in changes.items():
        path.write_text(text, encoding='utf-8', newline='\n')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('copy', type=Path)
    prepare(parser.parse_args().copy)
