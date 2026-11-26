import unittest,struct,zlib
from pathlib import Path
from tempfile import TemporaryDirectory
from chimster.world_validator import validate
from chimster.fnv_world import build,group,cell_record
from chimster.fnv_patch import sub,record
from chimster.worldspace import Terrain

def header(master=None):
    data=sub(b"HEDR",struct.pack("<fII",1.34,10,0x900))
    if master:data+=sub(b"MAST",master.encode()+b"\0")+sub(b"DATA",bytes(8))
    return record(b"TES4",data)
def patch(path,master,cell,coord=(-1,-1),new=False,base=0x802):
    x,y=coord
    # World override, matching master slot; optionally new cell with own slot.
    fid=0x01000880 if new else cell
    ref=record(b"REFR",sub(b"NAME",struct.pack("<I",base))+sub(b"DATA",struct.pack("<6f",x*4096+4,y*4096+4,0,0,0,0)),0x01000881)
    c=cell_record(fid,x,y)+group(6,fid,group(9,fid,ref))
    data=group(0,b"WRLD",record(b"WRLD",sub(b"EDID",b"TestWorld\0"),0x800)+group(1,0x800,group(4,struct.pack("<hh",y//32,x//32),group(5,struct.pack("<hh",y//8,x//8),c))))
    path.write_bytes(header(master)+data)

class ValidatorTests(unittest.TestCase):
    def fixture(self,p):
        t=Terrain(tuple(tuple(0. for _ in range(65)) for _ in range(65)),4,0)
        build(t,p,origin=(-1,-1),editor_id="TestWorld",content={"statics":[{"id":"TestMarker","model":"test.nif","bounds":[0,0,0,1,1,1]}]})
    def test_clean(self):
        with TemporaryDirectory() as d:
            p=Path(d)/"Base.esm";self.fixture(p)
            r=validate([p])
            self.assertTrue(r["valid"],r["issues"])
            self.assertEqual((r["exterior_cells"],r["persistent_cells"],r["land_records"]),(4,1,4))
    def test_corrupt_group_label(self):
        with TemporaryDirectory() as d:
            p=Path(d)/"Base.esm";self.fixture(p);data=bytearray(p.read_bytes())
            for i in range(len(data)-24):
                if data[i:i+4]==b"GRUP" and struct.unpack_from("<I",data,i+12)[0]==5:
                    struct.pack_into("<hh",data,i+8,55,55);break
            p.write_bytes(data)
            codes={x["code"] for x in validate([p])["issues"]}
            self.assertTrue({"subblock-coordinate","cell-grid"}<=codes)
    def test_merge_conflict(self):
        with TemporaryDirectory() as d:
            p=Path(d)/"Base.esm";self.fixture(p);q=Path(d)/"Patch.esp"
            patch(q,p.name,0x803,new=True,base=0x123456)
            r=validate([p,q]);codes={x["code"] for x in r["issues"]}
            self.assertIn("duplicate-cell-coordinate",codes)
            self.assertIn("unresolved-base-object",codes)
            self.assertIn("master-order",{x["code"] for x in validate([q,p])["issues"]})
    def test_valid_override(self):
        with TemporaryDirectory() as d:
            p=Path(d)/"Base.esm";self.fixture(p);q=Path(d)/"Patch.esp"
            patch(q,p.name,0x803)
            r=validate([p,q]);self.assertTrue(r["valid"],r["issues"])
            self.assertEqual(r["exterior_cells"],4)
    def test_truncated(self):
        with TemporaryDirectory() as d:
            p=Path(d)/"Base.esm";self.fixture(p);p.write_bytes(p.read_bytes()[:-1])
            r=validate([p]);self.assertFalse(r["valid"]);self.assertFalse(r["complete"])
