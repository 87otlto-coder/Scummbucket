"""Inventory and preserve MI2 DOS VGA sound resources from the original pair."""
import argparse
import hashlib
import json
import struct
from collections import Counter
from pathlib import Path
from zipfile import ZipFile

XOR = bytes(value ^ 0x69 for value in range(256))
PAYLOAD_LENGTH_TAGS = {b'SOU ', b'MDhd', b'MThd', b'MTrk'}


def sha(data):
    return hashlib.sha256(data).hexdigest()


def chunks(data, start, end, *, payload_sizes=False):
    while start < end:
        if end - start < 8:
            raise ValueError(f'truncated chunk at {start}')
        tag, size = struct.unpack_from('>4sI', data, start)
        if payload_sizes or tag in PAYLOAD_LENGTH_TAGS:
            size += 8
        if not 8 <= size <= end - start:
            raise ValueError(f'invalid {tag!r} size {size} at {start}')
        yield tag, start, start + size
        start += size


def read_pair(path):
    names = ('MONKEY2.000', 'MONKEY2.001')
    if path.is_dir():
        return [(name, (path / name).read_bytes()) for name in names]
    with ZipFile(path) as archive:
        pairs = {}
        for entry in archive.infolist():
            folder, _, name = entry.filename.replace(chr(92), '/').rpartition('/')
            if name.upper() in names:
                matches = pairs.setdefault(folder.casefold(), {})
                if name.upper() in matches:
                    raise ValueError(f'duplicate archive member {entry.filename}')
                matches[name.upper()] = entry
        candidates = [pair for pair in pairs.values() if pair.keys() == set(names)]
        if len(candidates) != 1:
            raise ValueError('expected exactly one MONKEY2.000/.001 pair')
        return [(candidates[0][name].filename, archive.read(candidates[0][name]))
                for name in names]


def resources(index, data, directory, resource_tag):
    """Resolve directory offsets against bounded, immediate LFLF children."""
    _, start, end = next(chunk for chunk in chunks(index, 0, len(index))
                         if chunk[0] == directory)
    if end - start < 10:
        raise ValueError(f'truncated {directory!r} directory')
    count, = struct.unpack_from('<H', index, start + 8)
    if end != start + 10 + count * 5:
        raise ValueError(f'invalid {directory!r} directory length')
    room_ids = index[start + 10:start + 10 + count]
    offsets = struct.unpack_from(f'<{count}I', index, start + 10 + count)
    root, = chunks(data, 0, len(data))
    if root[0] != b'LECF':
        raise ValueError('expected XOR-0x69 LECF resource file')
    outer = list(chunks(data, 8, root[2]))
    _, loff, loff_end = next(chunk for chunk in outer if chunk[0] == b'LOFF')
    if loff_end < loff + 9 or loff_end != loff + 9 + 5 * data[loff + 8]:
        raise ValueError('invalid LOFF length')
    room_bases = dict(struct.iter_unpack('<BI', data[loff + 9:loff_end]))
    if len(room_bases) != data[loff + 8]:
        raise ValueError('duplicate LOFF room IDs')
    bounds = {start + 8: end for tag, start, end in outer if tag == b'LFLF'}
    resource_bounds = {}
    for base in room_bases.values():
        if base not in bounds:
            raise ValueError(f'LOFF target {base} is outside LFLF boundaries')
        resource_bounds[base] = {start: (tag, end)
                                 for tag, start, end in chunks(data, base, bounds[base])}
    for sound_id, (room, offset) in enumerate(zip(room_ids, offsets)):
        base = room_bases.get(room)
        if offset == 0xffffffff or (room == 0 and offset == 0):
            yield sound_id, room, None, None, 'empty_slot'
            continue
        start = base + offset if base is not None else None
        tag, end = resource_bounds.get(base, {}).get(start, (None, None))
        if tag != resource_tag:
            yield sound_id, room, start, None, 'unresolved_directory_entry'
        else:
            yield sound_id, room, start, end, 'ok'


def vlq(data, pos):
    value = 0
    for _ in range(4):
        if pos >= len(data):
            raise ValueError('truncated MIDI VLQ')
        byte = data[pos]
        pos += 1
        value = (value << 7) | (byte & 127)
        if byte < 128:
            return value, pos
    raise ValueError('MIDI VLQ exceeds four bytes')


def signed(value):
    return value - 256 if value >= 128 else value


def imuse(payload):
    if len(payload) < 3 or payload[0] != 0x7d or payload[-1] != 0xf7:
        return None
    code, operands = payload[1], payload[2:-1]
    result = {'opcode': code, 'operands_hex': operands.hex(), 'type': 'unknown'}
    if code == 64 and operands:
        return dict(result, type='marker', marker_ids=list(operands[1:]))
    if code == 81:
        return dict(result, type='end_loop')
    if code == 17 and len(operands) >= 3:
        encoded = operands[3:]
    elif code in (16, 33):
        encoded = operands[2:]
    else:
        encoded = operands[1:]
    if len(encoded) % 2 or any(byte > 15 for byte in encoded):
        return result
    decoded = bytes(a * 16 + b for a, b in zip(encoded[::2], encoded[1::2]))
    result['decoded_hex'] = decoded.hex()
    if code == 0 and len(decoded) == 8:
        return dict(result, type='part_setup', channel=operands[0] & 15,
                    on=bool(decoded[0] & 1), reverb=bool(decoded[0] & 2),
                    priority_adjustment=signed(decoded[1]), volume=decoded[2],
                    pan=signed(decoded[3]), transpose_or_percussion=decoded[4],
                    detune=signed(decoded[5]), pitch_bend_factor=decoded[6],
                    program=decoded[7])
    if code == 1 and len(operands) == 1:
        return dict(result, type='part_release', channel=operands[0])
    if code == 2:
        return dict(result, type='song_start')
    if code == 16 and len(operands) >= 2:
        return dict(result, type='part_instrument_definition',
                    channel=operands[0] & 15, hardware_type=operands[1])
    if code == 17 and len(operands) >= 3:
        return dict(result, type='global_instrument_definition',
                    hardware_type=operands[0], instrument_slot=operands[2])
    if code == 33 and len(decoded) == 4:
        parameter, value = struct.unpack('>HH', decoded)
        return dict(result, type='part_parameter', channel=operands[0] & 15,
                    hardware_type=operands[1], parameter=parameter, value=value)
    if code == 48 and len(decoded) == 7:
        hook, track, beat, tick = struct.unpack('>BHHH', decoded)
        return dict(result, type='jump_hook', hook_id=hook, destination_track=track,
                    destination_beat=beat, destination_tick_in_beat=tick,
                    destination_absolute_tick=(beat - 1) * 480 + tick)
    if code == 80 and len(decoded) == 10:
        count, to_beat, to_tick, from_beat, from_tick = struct.unpack('>5H', decoded)
        return dict(result, type='loop', count=count, to_beat=to_beat, to_tick=to_tick,
                    from_beat=from_beat, from_tick=from_tick,
                    to_absolute_tick=(max(to_beat, 1) - 1) * 480 + to_tick,
                    from_absolute_tick=(from_beat - 1) * 480 + from_tick)
    if code in (49, 53) and len(decoded) == 3:
        result.update(type='global_transpose_hook' if code == 49 else 'part_transpose_hook',
                      hook_id=decoded[0], relative=bool(decoded[1]), semitones=signed(decoded[2]))
        if code == 53:
            result['channel'] = operands[0] & 15
    if code in (50, 51, 52) and len(decoded) == 2:
        name = {50: 'part_on', 51: 'part_volume', 52: 'part_program'}[code]
        result.update(type=name + '_hook', hook_id=decoded[0], channel=operands[0] & 15)
        result[name] = decoded[1]
    if code == 96 and len(decoded) == 2:
        result.update(type='instrument', channel=operands[0] & 15,
                      encoded_instrument=int.from_bytes(decoded, 'big'))
    return result


def midi_events(data, track, division, base):
    pos = tick = elapsed = 0
    tempo = 500000
    running = None
    while pos < len(data):
        start = pos
        delta, pos = vlq(data, pos)
        tick += delta
        elapsed += delta * tempo
        if pos == len(data):
            raise ValueError('missing MIDI status')
        status = data[pos]
        if status < 128:
            if running is None:
                raise ValueError('MIDI running status without preceding channel event')
            status = running
        else:
            pos += 1
        event = {'track': track, 'offset': base + start, 'delta': delta, 'tick': tick,
                 'linear_microseconds': elapsed / division, 'status': status}
        if status in (0xf0, 0xf7, 0xff):
            running = None
            if status == 0xff:
                if pos == len(data):
                    raise ValueError('missing MIDI meta type')
                event['meta_type'] = data[pos]
                pos += 1
            length, pos = vlq(data, pos)
            payload = data[pos:pos + length]
            if len(payload) != length:
                raise ValueError('truncated MIDI payload')
            pos += length
            if status == 0xff:
                kind = {0x2f: 'end_of_track', 0x06: 'meta_marker', 0x51: 'tempo'}.get(
                    event['meta_type'], 'meta')
                event['type'] = kind
                if kind == 'tempo':
                    if length != 3 or not any(payload):
                        raise ValueError('invalid MIDI tempo')
                    tempo = int.from_bytes(payload, 'big')
                    event['microseconds_per_quarter'] = tempo
                if kind == 'end_of_track' and length:
                    raise ValueError('invalid EOT length')
                if kind == 'meta_marker':
                    event['text'] = payload.decode('ascii', errors='replace')
            else:
                event['type'] = 'sysex'
                control = imuse(payload) if status == 0xf0 else None
                if control is not None:
                    event['imuse'] = control
        elif 0x80 <= status < 0xf0:
            running = status
            kind = status >> 4
            width = 1 if kind in (12, 13) else 2
            operands = data[pos:pos + width]
            if len(operands) != width or any(byte >= 128 for byte in operands):
                raise ValueError('invalid MIDI channel event')
            pos += width
            event.update(type=('note_off', 'note_on', 'poly_pressure', 'control_change',
                               'program_change', 'channel_pressure', 'pitch_bend')[kind - 8],
                         channel=status & 15, operands=list(operands))
        else:
            raise ValueError(f'unsupported MIDI status {status:#04x}')
        event['event_hex'] = data[start:pos].hex()
        yield event


def parse_rendition(data, start, end):
    item = {}
    if data[start:start + 4] in (b'SPK ', b'SBL '):
        return {'status': 'native_only'}, None, []
    if data[start:start + 4] not in (b'ROL ', b'ADL ', b'AMI ', b'GMD ', b'MIDI'):
        return {'status': 'unsupported_rendition'}, None, []
    children = list(chunks(data, start + 8, end))
    item['chunks'] = [{'tag': tag.decode('ascii', errors='replace'), 'offset': at,
                       'bytes': stop - at} for tag, at, stop in children]
    for tag, a, b in children:
        if tag != b'MDhd':
            continue
        metadata = data[a + 8:b]
        item['mdhd_hex'] = metadata.hex()
        if len(metadata) == 8:
            item['mdhd'] = dict(priority=metadata[2], volume=metadata[3],
                                pan=signed(metadata[4]), transpose=signed(metadata[5]),
                                detune=signed(metadata[6]), speed=metadata[7])
    header = next(((at, stop) for tag, at, stop in children if tag == b'MThd'), None)
    if header is None:
        return dict(item, status='native_only'), None, []
    at, stop = header
    if stop - at != 14:
        raise ValueError('invalid MThd length')
    fmt, count, division = struct.unpack_from('>HHH', data, at + 8)
    tracks = [(a, b) for tag, a, b in children if tag == b'MTrk']
    if fmt not in (0, 1, 2) or not count or count != len(tracks) or not 0 < division < 32768:
        raise ValueError('unsupported MIDI header or inconsistent track count')
    if fmt == 0 and count != 1:
        raise ValueError('format 0 MIDI must have one track')
    if list(chunks(data, at, end)) != [(b'MThd', at, stop), *[
            (b'MTrk', a, b) for a, b in tracks]]:
        raise ValueError('noncontiguous Standard MIDI File')
    events = []
    for track, (a, b) in enumerate(tracks):
        track_events = list(midi_events(data[a + 8:b], track, division, a + 8))
        if not track_events or track_events[-1]['type'] != 'end_of_track':
            raise ValueError(f'track {track} lacks terminal EOT')
        if any(event['type'] == 'end_of_track' for event in track_events[:-1]):
            raise ValueError(f'track {track} has events after EOT')
        events.extend(track_events)
    if fmt == 1:
        # Format 1 has simultaneous tracks and a shared tempo map.
        previous_tick = elapsed = 0
        tempo = 500000
        for event in sorted(events, key=lambda e: (e['tick'], e['track'])):
            elapsed += (event['tick'] - previous_tick) * tempo
            previous_tick = event['tick']
            event['linear_microseconds'] = elapsed / division
            if event['type'] == 'tempo':
                tempo = event['microseconds_per_quarter']
    return dict(item, status='midi_parsed', format=fmt, tracks=count, ppqn=division,
                tempos=[{key: e[key] for key in ('track', 'tick', 'microseconds_per_quarter')}
                        for e in events if e['type'] == 'tempo']), data[at:end], events


def write_bytes(path, payload):
    with path.open('xb') as stream:
        stream.write(payload)
    if path.read_bytes() != payload:
        raise OSError(f'byte verification failed for {path}')


def woodtick_trace(index, data, control_map):
    """Reproduce one source-derived path using the supplied DOS edition's scripts."""
    _, room, start, end, _ = next(row for row in resources(index, data, b'DSCR', b'SCRP')
                                  if row[0] == 96)
    if (room, start, end) != (7, 475099, 475985):
        raise ValueError('Woodtick trace is scoped to the verified script 96 layout')
    if sha(data[start:end]) != '345737f45b8fbdb8d4d0f30b8a65975186a771c46701c37472247e0a2622c7dd':
        raise ValueError('unexpected script 96 digest')
    caller = bytes.fromhex('2a 60 01 07 00 01 09 00 ff')
    if any(data[offset:offset + len(caller)] != caller for offset in (470748, 470866)):
        raise ValueError('missing verified Woodtick doorway call sites')

    def command(offset, expected):
        if data[offset] != 0x4c:
            raise ValueError(f'expected soundKludge at {offset}')
        for n, value in enumerate(expected):
            mode, word = struct.unpack_from('<BH', data, offset + 1 + n * 3)
            if (mode, word) != value:
                raise ValueError(f'unexpected soundKludge operand at {offset}')
        if data[offset + 1 + 3 * len(expected)] != 0xff:
            raise ValueError(f'missing soundKludge terminator at {offset}')
        return {'offset': offset, 'operands': [
            word if mode == 1 else {'variable': word} for mode, word in expected]}

    commands = []
    for offset, values in (
        (475255, [270, 101, 0]), (475279, [271, 263, 101, (129, 100), 4, 400]),
        (475299, [271, 65535]), (475307, [270, 101, 1]),
        (475801, [271, 9, 103]), (475812, [271, 8, 103]), (475971, [271, 65535]),
    ):
        commands.append(command(offset, [value if isinstance(value, tuple) else (1, value)
                                         for value in values]))

    def find(sound, tag, track, tick, **operands):
        return next(event for rendition in control_map
                    if rendition['sound_id'] == sound and rendition['tag'] == tag
                    for event in rendition['events']
                    if event['track'] == track and event['tick'] == tick
                    and all(event.get('imuse', {}).get(key) == value
                            for key, value in operands.items()))

    renditions = {}
    for tag in ('ROL ', 'ADL '):
        renditions[tag] = {
            'woodtick_marker_0': find(101, tag, 0, 3760, marker_ids=[0]),
            'woodtick_exit_marker_1': find(101, tag, 1, 1920, marker_ids=[1]),
            'bar_unarmed_loop': find(103, tag, 0, 40140, hook_id=0,
                                     destination_track=0, destination_absolute_tick=1740),
            'bar_conditional_exit_example': find(103, tag, 0, 3760, hook_id=1,
                                                 destination_track=1,
                                                 destination_absolute_tick=1840),
        }
    return {'evidence': 'archive_and_scummvm_source_static_reconstruction',
            'conditions': {'entry_room': 7, 'destination_room': 9, 'active_sound': 101,
                           'active_track': 0, 'example_trigger_tick': 3760,
                           'example_script_variable_100': 1},
            'doorway_script_offsets': [470748, 470866],
            'global_script': {'id': 96, 'offset': start, 'bytes': end - start,
                              'sha256': sha(data[start:end])},
            'commands': commands,
            'handoff': [{'sound': 101, 'track': 0, 'tick': 3760, 'marker': 0},
                        {'sound': 101, 'track': 1, 'tick': 1840, 'command': 'queued_jump'},
                        {'sound': 101, 'track': 1, 'tick': 1920, 'marker': 1},
                        {'sound': 103, 'track': 0, 'tick': 0, 'command': 'queued_start'}],
            'renditions': renditions}


def inventory(path, output, selected, trace=False):
    pair = read_pair(path)
    index, data = [payload.translate(XOR) for _, payload in pair]
    report = {'input': str(path), 'xor_key': '0x69', 'files': [
        {'name': name, 'sha256': sha(payload), 'bytes': len(payload)}
        for name, payload in pair], 'sounds': []}
    output.mkdir(parents=True, exist_ok=False)
    control_map = []
    for sound_id, room, start, end, status in resources(index, data, b'DSOU', b'SOUN'):
        sound = {'id': sound_id, 'room': room, 'offset': start, 'status': status}
        report['sounds'].append(sound)
        if end is None:
            continue
        native = data[start:end]
        sound.update(bytes=len(native), sha256=sha(native), renditions=[])
        export = sound_id in selected
        if export:
            write_bytes(output / f'{sound_id:03}.soun', native)
        try:
            tag, wrapper, limit = next(chunks(data, start + 8, end))
            if tag == b'SOU ':
                sound['sou_declared_payload_bytes'] = limit - wrapper - 8
                if limit != end:
                    if limit != wrapper + 8:
                        raise ValueError('SOU size disagrees with SOUN boundary')
                    outer = list(chunks(data, limit, end, payload_sizes=True))
                    if outer != [(b'ADL ', limit, end)]:
                        raise ValueError('unrecognized data after zero-length SOU')
                    sound['status'] = 'zero_length_sou_recovered_from_soun'
                else:
                    outer = list(chunks(data, wrapper + 8, end, payload_sizes=True))
            else:
                outer = list(chunks(data, start + 8, end, payload_sizes=True))
        except (ValueError, StopIteration) as exc:
            sound.update(status='invalid_sound_container', error=str(exc))
            continue
        for number, (tag, at, stop) in enumerate(outer):
            rendition = {'tag': tag.decode('ascii', errors='replace'), 'offset': at,
                          'bytes': stop - at, 'sha256': sha(data[at:stop])}
            sound['renditions'].append(rendition)
            prefix = f'{sound_id:03}_{number:02}'
            if export:
                write_bytes(output / (prefix + '.bin'), data[at:stop])
            try:
                info, midi, events = parse_rendition(data, at, stop)
            except (ValueError, struct.error) as exc:
                rendition.update(status='invalid_or_unsupported_midi', error=str(exc))
                continue
            rendition.update(info)
            controls = [event for event in events
                        if event['type'] in ('sysex', 'meta_marker')]
            if controls:
                rendition['imuse_opcode_counts'] = dict(Counter(
                    event['imuse']['opcode'] for event in controls if 'imuse' in event))
                control_map.append(dict(sound_id=sound_id, rendition=number,
                                        tag=rendition['tag'], events=controls))
            if export and midi is not None:
                write_bytes(output / (prefix + '.mid'), midi)
                write_bytes(output / (prefix + '_events.json'),
                            json.dumps(events, separators=(',', ':')).encode('utf-8'))
    write_bytes(output / 'inventory.json', json.dumps(report, indent=2).encode('utf-8'))
    write_bytes(output / 'control_map.json',
                json.dumps(control_map, separators=(',', ':')).encode('utf-8'))
    if trace:
        write_bytes(output / 'woodtick_to_bar.json',
                    json.dumps(woodtick_trace(index, data, control_map), indent=2).encode('utf-8'))
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('input', type=Path, help='mi2.zip or directory with the original pair')
    parser.add_argument('output', type=Path, help='new output directory')
    parser.add_argument('--export', type=int, nargs='+', default=[], metavar='SOUND_ID')
    parser.add_argument('--woodtick-trace', action='store_true',
                        help='verify the static Woodtick-to-Bar case for the supplied edition')
    args = parser.parse_args()
    report = inventory(args.input, args.output, set(args.export), args.woodtick_trace)
    print(f"Wrote {len(report['sounds'])} sound slots to {args.output / 'inventory.json'}")


if __name__ == '__main__':
    main()
