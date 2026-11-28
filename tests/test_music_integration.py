"""Music export through P1's verified DSOU links, using synthetic assets."""
import io
import json
import struct
import tempfile
import unittest
import wave
from pathlib import Path

from scummbucket.cli import main
from scummbucket.inspector import chunks
from scummbucket.music import parse_sbl
from test_inspector import chunk, index, make_zip, resource


def audio_chunk(tag, payload):
    return struct.pack('>4sI', tag, len(payload)) + payload


class MusicIntegrationTest(unittest.TestCase):
    def test_p1_links_and_exports_both_native_renditions(self):
        track = bytes.fromhex('00f0057d400001f7 00ff2f00')
        midi = audio_chunk(b'MThd', struct.pack('>HHH', 2, 1, 480)) + audio_chunk(b'MTrk', track)
        speaker = audio_chunk(b'SPK ', audio_chunk(b'MDhd', bytes(8)) + midi)
        pcm = bytes([4, 128, 252])
        voc = bytes([1, 5, 0, 0, 0xa5, 0]) + pcm + b'\0'
        sbl = audio_chunk(b'SBL ', audio_chunk(b'AUhd', b'\0\0\x80') + audio_chunk(b'AUdt', voc))
        sound = chunk('SOUN', audio_chunk(b'SOU ', speaker + sbl))
        base = resource()
        room = base[30:]
        archive = chunk('LECF', base[8:22] + chunk('LFLF', room + sound))
        directory = chunk('DSOU', struct.pack('<HBBII', 2, 0, 1, 0, len(room)))
        original = index()
        idx = b''.join(directory if p.tag == 'DSOU' else original[p.offset:p.end]
                       for p in chunks(original, 0, len(original), 'synthetic'))
        with tempfile.TemporaryDirectory() as folder:
            source = Path(folder) / 'mi2.zip'
            output = Path(folder) / 'new'
            make_zip(source, a=idx, b=archive)
            argv = ['music', str(source), '--output-dir', str(output), '--export', '1']
            self.assertEqual(main(argv), 0)
            self.assertEqual(main(argv), 1)
            report = json.loads((output / 'inventory.json').read_bytes())
            self.assertEqual(report['archive_status'], 'success')
            self.assertEqual(report['sounds'][0]['status'], 'empty_slot')
            self.assertEqual(report['sounds'][1]['offset'], 30 + len(room))
            self.assertEqual((output / '001.soun').read_bytes(), sound)
            self.assertEqual((output / '001_00.bin').read_bytes(), speaker)
            self.assertEqual((output / '001_00.mid').read_bytes(), midi)
            self.assertEqual((output / '001_01.bin').read_bytes(), sbl)
            events = json.loads((output / 'control_map.json').read_bytes())
            self.assertEqual(events[0]['events'][0]['imuse']['marker_ids'], [1])
            wav = (output / '001_01.wav').read_bytes()
            self.assertEqual(int.from_bytes(wav[4:8], 'little'), len(wav) - 8)
            with wave.open(io.BytesIO(wav)) as audio:
                self.assertEqual(audio.getframerate(), 11025)
                self.assertEqual(audio.readframes(audio.getnframes()), pcm)

    def test_unsupported_sound_blaster_codec(self):
        voc = bytes([1, 3, 0, 0, 0xa5, 1, 0x80])
        sbl = audio_chunk(b'SBL ', audio_chunk(b'AUhd', bytes(3)) + audio_chunk(b'AUdt', voc))
        with self.assertRaisesRegex(ValueError, 'unsupported SBL VOC codec'):
            parse_sbl(sbl, 0, len(sbl))
