import unittest,struct
from pathlib import Path
from tempfile import TemporaryDirectory
from chimster.fnv_records import scan,RecordIndex,HEADER
def sub(k,v):return struct.pack("<4sH",k,len(v))+v
def rec(k,body=b"",form=0,flags=0):return HEADER.pack(k,len(body),flags,form,0,15,0)+body
def make(path,master=None,value=1):
    h=sub(b"HEDR",struct.pack("<fII",1.34,2,0x800))
    if master:h+=sub(b"MAST",master.encode()+b"\0")+sub(b"DATA",bytes(8))
    r=rec(b"GMST",sub(b"EDID",b"iChimsterTest\0")+sub(b"DATA",struct.pack("<i",value)),0x800)
    g=struct.pack("<4sI4sIII",b"GRUP",len(r)+24,b"GMST",0,0,0)+r
    path.write_bytes(rec(b"TES4",h,flags=0 if master else 1)+g)
class FnvIndexTests(unittest.TestCase):
    def test_incremental(self):
        with TemporaryDirectory() as d:
            p=Path(d);a=p/"Base.esm";b=p/"Patch.esp";make(a);make(b,a.name,2)
            idx=RecordIndex(p/"cache.sqlite")
            try:
                self.assertEqual(idx.refresh([a,b])["reindexed"],[a.name,b.name])
                self.assertEqual(idx.refresh([a,b])["cache_hits"],2)
                self.assertEqual(idx.chain(a.name,0x800)[-1]["provider"],"patch.esp")
                make(b,a.name,3)
                self.assertEqual(idx.refresh([a,b])["reindexed"],[b.name])
                self.assertNotEqual(*[x["payload_sha256"] for x in idx.chain(a.name,0x800)])
                idx.refresh([a]);self.assertEqual(len(idx.chain(a.name,0x800)),1)
            finally:idx.close()
    def test_order(self):
        with TemporaryDirectory() as d:
            p=Path(d);a=p/"Base.esm";b=p/"Patch.esp";make(a);make(b,a.name)
            idx=RecordIndex(p/"cache.sqlite")
            try:
                with self.assertRaises(ValueError):idx.refresh([b,a])
            finally:idx.close()
