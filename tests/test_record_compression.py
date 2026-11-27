import unittest,struct,zlib
from pathlib import Path
from tempfile import TemporaryDirectory
from chimster.fnv_patch import sub,record
from chimster.fnv_world import group
from chimster.fnv_records import HEADER,scan,subs
from chimster.record_editor import inspect,edit_typed,unpack_payload
class CompressionTests(unittest.TestCase):
    def test_edit(self):
        with TemporaryDirectory() as d:
            p=Path(d)/"Test.esp";q=Path(d)/"stage";q.mkdir()
            body=sub(b"EDID",b"Test\0")+sub(b"FULL",b"Old\0")+sub(b"ZZZZ",b"unrecognized")
            payload=struct.pack("<I",len(body))+zlib.compress(body)
            raw=bytearray(record(b"FACT",payload,0x800));struct.pack_into("<I",raw,8,0x40000)
            p.write_bytes(record(b"TES4",sub(b"HEDR",struct.pack("<fII",1.34,2,0x801)))+group(0,b"FACT",raw))
            info=inspect(p,p.name,0x800);self.assertTrue(info["compressed"])
            edit_typed(p,q/p.name,p.name,0x800,"FULL","New",info["payload_sha256"])
            r=scan(q/p.name)["records"][0];self.assertEqual(r["flags"],0x40000)
            with (q/p.name).open("rb") as f:
                f.seek(r["offset"]);_,n,flags,*_=HEADER.unpack(f.read(24));parts=dict(subs(unpack_payload(f.read(n),flags)))
            self.assertEqual(parts[b"ZZZZ"],b"unrecognized");self.assertEqual(parts[b"FULL"],b"New\0")
    def test_invalid(self):
        for raw in (b"",struct.pack("<I",10)+zlib.compress(b"x"),struct.pack("<I",1)+zlib.compress(b"x")+b"x"):
            with self.assertRaises(ValueError):unpack_payload(raw,0x40000)
