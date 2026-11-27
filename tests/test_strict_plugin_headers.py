import struct
import tempfile
import unittest
from pathlib import Path
from chimster.core import inspect_plugin

def record(sig, data=b'', hs=24):
    return struct.pack('<4sI',sig,len(data))+bytes(hs-8)+data

class StrictPluginHeaders(unittest.TestCase):
    def scan(self, data, game='newvegas'):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'Test.esp'
            p.write_bytes(data)
            return inspect_plugin(p,game)

    def test_layouts(self):
        for game,magic,hs in [('morrowind',b'TES3',16),('oblivion',b'TES4',20),('newvegas',b'TES4',24),('starfield',b'TES4',24)]:
            with self.subTest(game=game):
                self.assertEqual(self.scan(record(magic,hs=hs),game)['record_counts'],{magic.decode():1})

    def test_duplicate_header(self):
        with self.assertRaises(ValueError):
            self.scan(record(b'TES4')*2)

    def test_invalid_signature(self):
        with self.assertRaises(ValueError):
            self.scan(record(b'TES4')+record(b'\x00ABC'))

    def test_dangling_extended_size(self):
        marker=struct.pack('<4sHI',b'XXXX',4,8)
        with self.assertRaises(ValueError):
            self.scan(record(b'TES4',marker))

    def test_extended_subrecord(self):
        marker=struct.pack('<4sHI',b'XXXX',4,8)
        sub=struct.pack('<4sH',b'UNKN',0)+b'12345678'
        self.assertEqual(self.scan(record(b'TES4',marker+sub))['record_counts'],{'TES4':1})
