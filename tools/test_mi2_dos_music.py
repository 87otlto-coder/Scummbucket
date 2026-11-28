import struct
import tempfile
import unittest
from pathlib import Path

import mi2_dos_music as music


def chunk(tag, payload):
    return struct.pack('>4sI', tag, len(payload)) + payload


def sysex(code, operands):
    encoded = bytes(nibble for byte in operands for nibble in (byte >> 4, byte & 15))
    return music.imuse(bytes([0x7d, code, 0]) + encoded + b'\xf7')


class MusicTests(unittest.TestCase):
    def test_jump_loop_and_unknown(self):
        jump = sysex(48, struct.pack('>BHHH', 1, 2, 4, 400))
        self.assertEqual((jump['hook_id'], jump['destination_track'],
                          jump['destination_absolute_tick']), (1, 2, 1840))
        loop = sysex(80, struct.pack('>HHHHH', 1000, 3, 200, 67, 160))
        self.assertEqual((loop['to_absolute_tick'], loop['from_absolute_tick']), (1160, 31840))
        self.assertEqual(music.imuse(bytes.fromhex('7d400001f7'))['marker_ids'], [1])
        self.assertEqual(sysex(100, bytes([42]))['decoded_hex'], '2a')

    def test_midi_ticks_tempo_running_status_and_byte_preservation(self):
        track = bytes.fromhex('00ff510306c06d 00903c40 83603c00 00ff2f00')
        midi = chunk(b'MThd', struct.pack('>HHH', 0, 1, 480)) + chunk(b'MTrk', track)
        rendition = chunk(b'ROL ', chunk(b'MDhd', bytes(8)) + midi)
        info, extracted, events = music.parse_rendition(rendition, 0, len(rendition))
        self.assertEqual((info['tracks'], info['ppqn']), (1, 480))
        self.assertEqual(extracted, midi)
        self.assertEqual([e['tick'] for e in events], [0, 0, 480, 480])
        self.assertEqual(events[2]['linear_microseconds'], 442477)
        self.assertEqual(bytes.fromhex(''.join(e['event_hex'] for e in events)), track)
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory) / 'example.mid'
            music.write_bytes(target, extracted)
            with self.assertRaises(FileExistsError):
                music.write_bytes(target, b'overwrite')
            self.assertEqual(target.read_bytes(), midi)

    def test_chunk_boundaries_and_truncated_events(self):
        with self.assertRaisesRegex(ValueError, 'invalid'):
            list(music.chunks(chunk(b'MTrk', b'123')[:-1], 0, 10))
        with self.assertRaisesRegex(ValueError, 'truncated MIDI VLQ'):
            list(music.midi_events(b'\x81', 0, 480, 0))
        with self.assertRaisesRegex(ValueError, 'truncated MIDI payload'):
            list(music.midi_events(bytes.fromhex('00f0047d02'), 0, 480, 0))


if __name__ == '__main__':
    unittest.main()
