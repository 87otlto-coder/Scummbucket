"""Check the ordered live Woodtick-to-Bar trace and report the observed phase."""
import argparse
import json
import re
from pathlib import Path


def verify(log, expected_tag):
    records = []
    for line in log.splitlines():
        match = re.search(r'\bSBM (\w+)\s+(.*?)!?\s*$', line)
        if match:
            name, fields = match.groups()
            records.append((name, dict(re.findall(r'(\w+)=([^\s!]+)', fields))))
    cursor = 0

    def find(name, **required):
        nonlocal cursor
        for index in range(cursor, len(records)):
            event, fields = records[index]
            if event == name and all(fields.get(key) == str(value) for key, value in required.items()):
                cursor = index + 1
                return fields
        raise ValueError(f'missing ordered trace event {name} {required}')

    find('rendition', sound=101, tag=expected_tag)
    woodtick = find('sequence', sound=101, track=0)['parser']
    find('entry', room=7, script=200)
    find('script', id=96, **{'from': 7, 'to': 9})
    find('rendition', sound=103, tag=expected_tag)
    find('enqueue_trigger', sound=101, marker=0)
    find('enqueue_trigger', sound=101, marker=1)
    # Match the dispatch immediately upstream of the queued command release.
    release = find('release', marker=0, command=263, sound=101, a3=4, a4=400)
    source = next(fields for name, fields in reversed(records[:cursor - 1])
                  if name == 'dispatch' and fields.get('parser') == woodtick
                  and fields.get('opcode') == '64' and fields.get('operand') == '0')
    track = int(release['a2'])
    if not 1 <= track <= 5:
        raise ValueError(f'unexpected Woodtick transition track {track}')
    find('jump', sound=101, parser=woodtick, active_track=track, target_tick=1840, tick=1840)
    find('dispatch', parser=woodtick, opcode=64, operand=1, event_tick=1920)
    find('release', marker=1, command=9, sound=103)
    find('release', marker=1, command=8, sound=103)
    bar = find('sequence', sound=103, track=0, tick=0, reset=1)['parser']
    find('dispatch', parser=bar, opcode=48, event_tick=40140)
    find('hook', sound=103, track=0, hook=0, armed=0, target_track=0, beat=4, tick=300)
    find('jump', sound=103, parser=bar, active_track=0, target_tick=1740, tick=1740)
    return {'status': 'live_verified', 'rendition': expected_tag, 'woodtick_marker_0_tick': int(source['event_tick']),
            'transition_track': track, 'transition_tick': 1840, 'marker_1_tick': 1920,
            'bar_sound': 103, 'bar_start_tick': 0, 'bar_loop_from': 40140, 'bar_loop_to': 1740}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('log', type=Path)
    parser.add_argument('--tag', default='ADL', choices=('ADL', 'ROL'))
    args = parser.parse_args()
    print(json.dumps(verify(args.log.read_text(encoding='utf-8', errors='replace'), args.tag), indent=2))
