import unittest,struct,zlib
from tempfile import TemporaryDirectory
from pathlib import Path
from chimster.fnv_patch import sub,record
from chimster.fnv_world import group
from chimster.fnv_records import scan,HEADER,subs
from chimster.record_project import export
class TemplateTests(unittest.TestCase):
    def fixture(self,p):
        ed=sub(b"EDID",b"SourceNPC\0")+sub(b"FULL",b"Old\0")+sub(b"ACBS",struct.pack("<IHHhHHHfhH",0,100,20,1,0,0,100,0.,0,0))+sub(b"VTCK",struct.pack("<I",0x801))+sub(b"RNAM",struct.pack("<I",0x802))+sub(b"CNAM",struct.pack("<I",0x803))+sub(b"DATA",struct.pack("<i7B",20,*([5]*7)))+sub(b"ZZZZ",b"untouched")
        body=record(b"NPC_",ed,0x800)
        h=record(b"TES4",sub(b"HEDR",struct.pack("<fII",1.34,8,0x804)))
        p.write_bytes(h+group(0,b"VTYP",record(b"VTYP",sub(b"EDID",b"Voice\0"),0x801))+group(0,b"RACE",record(b"RACE",sub(b"EDID",b"Race\0"),0x802))+group(0,b"CLAS",record(b"CLAS",sub(b"EDID",b"Class\0"),0x803))+group(0,b"NPC_",body))
    def test_clone(self):
        with TemporaryDirectory() as d:
            a=Path(d)/"A.esp";self.fixture(a);p=Path(d)/"B.esp"
            spec={"schema":1,"records":[{"id":"Faction","type":"FACT","fields":{"title":"Traders"}},{"id":"Actor","type":"NPC_","fields":{"template":{"plugin":"A.esp","id":0x800},"title":"New","health":45,"level":3,"special":[6]*7,"factions":[{"ref":"Faction","rank":0}]}}]}
            r=export(spec,p,[a]);row=next(x for x in scan(p)["records"] if x["signature"]=="NPC_")
            with p.open("rb") as f:
                f.seek(row["offset"]);_,n,*_=HEADER.unpack(f.read(24));fields=dict(subs(f.read(n)))
            self.assertEqual(fields[b"ZZZZ"],b"untouched")
            self.assertEqual(fields[b"RNAM"],struct.pack("<I",0x802))
            self.assertEqual(struct.unpack("<i7B",fields[b"DATA"]),(45,*([6]*7)))
            self.assertEqual(struct.unpack_from("<h",fields[b"ACBS"],8)[0],3)
            self.assertEqual(struct.unpack("<IB3x",fields[b"SNAM"]),(r["records"]["faction"],0))
            c=Path(d)/"C.esp";self.fixture(c)
            with self.assertRaises(ValueError):export(spec,Path(d)/"Bad.esp",[c,a])
