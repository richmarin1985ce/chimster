import unittest
import struct
from pathlib import Path
from tempfile import TemporaryDirectory
from chimster.vmad import parse, edit
from chimster.vmad_plugin import inspect, stage

def string(s):
    v=s.encode("utf-8")
    return struct.pack("<H",len(v))+v
def prop(name,typ,data):
    return string(name)+bytes([typ,1])+data
def fixture(tail=b""):
    properties=prop("Count",3,struct.pack("<i",3))+prop("Label",2,string("Old"))
    properties+=prop("Target",1,struct.pack("<HHI",0,65535,0x1234))
    properties+=prop("Enabled",5,b"\x01")
    properties+=prop("Numbers",13,struct.pack("<Iii",2,1,2))
    return struct.pack("<HHH",5,2,1)+string("Example")+struct.pack("<BH",0,5)+properties+tail

def sub(sig,data):return sig+struct.pack("<H",len(data))+data
def record(sig,body,form=0):
    return struct.pack("<4sIIIIHH",sig,len(body),0,form,0,44,0)+body
def group(body):
    return struct.pack("<4sI4siII",b"GRUP",24+len(body),b"ACTI",0,0,0)+body

class VMADTests(unittest.TestCase):
    def test_read(self):
        r=parse(fixture(),"skyrimse")
        p=r["scripts"][0]["properties"]
        self.assertEqual(p[2]["value"]["disk_form_id"],0x1234)
        self.assertEqual(p[4]["value"],[1,2])
    def test_edit(self):
        raw=fixture()
        r=parse(raw,"skyrim")
        changed=edit(raw,"skyrim","example","Label","New longer text",r["sha256"])
        p=r["scripts"][0]["properties"][1]
        self.assertEqual(changed,raw[:p["start"]]+string("New longer text")+raw[p["end"]:])
        self.assertEqual(parse(changed,"skyrim")["scripts"][0]["properties"][1]["value"],"New longer text")
    def test_fail_closed(self):
        raw=fixture(b"opaque")
        r=parse(raw,"skyrim")
        self.assertEqual(r["opaque_tail_bytes"],6)
        with self.assertRaises(ValueError):edit(raw,"skyrim","Example","Count",4,r["sha256"])
        with self.assertRaises(ValueError):parse(fixture()[:-1],"skyrim")
        with self.assertRaises(ValueError):parse(fixture(),"fallout4")
        raw=fixture();h=parse(raw,"skyrim")["sha256"]
        with self.assertRaises(ValueError):edit(raw,"skyrim","Example","Count",True,h)
        with self.assertRaises(ValueError):edit(raw,"skyrim","Example","Target",1,h)
        with self.assertRaises(ValueError):edit(raw,"skyrim","Example","Count",4,"stale")
    def test_plugin_stage(self):
        with TemporaryDirectory() as d:
            root=Path(d);out=root/"out";out.mkdir()
            p=root/"Test.esp";q=out/p.name
            hdr=record(b"TES4",sub(b"HEDR",struct.pack("<fII",1.7,2,0x801)))
            other=sub(b"EDID",b"Fixture\0")
            body=other+sub(b"VMAD",fixture())+sub(b"FULL",b"Unchanged\0")
            sibling=record(b"ACTI",other,0x801)
            original=hdr+group(record(b"ACTI",body,0x800)+sibling)
            p.write_bytes(original)
            r=inspect(p,"skyrimse",0x800)
            result=stage(p,q,"skyrimse",0x800,"Example","Label","New label",r["plugin_sha256"],r["sha256"])
            self.assertEqual(result["scripts"][0]["properties"][1]["value"],"New label")
            self.assertEqual(p.read_bytes(),original)
            self.assertTrue(q.read_bytes().endswith(sibling))
            self.assertIn(sub(b"FULL",b"Unchanged\0"),q.read_bytes())


    def test_typed_mutations(self):
        from chimster.vmad import mutate
        raw=fixture()
        def change(action,script,**kw):
            nonlocal raw
            raw=mutate(raw,"skyrimse",action,script,parse(raw,"skyrimse")["sha256"],**kw)
        change("attach","Second")
        change("add-property","Second",property_name="Values",type_id=13,value=[7,9])
        change("add-property","Second",property_name="Target",type_id=1,value=0x800,validate_form=lambda fid:fid==0x800)
        props=parse(raw,"skyrimse")["scripts"][1]["properties"]
        self.assertEqual(props[0]["value"],[7,9])
        self.assertEqual(props[1]["value"]["disk_form_id"],0x800)
        with self.assertRaises(ValueError):change("set-property","Second",property_name="Target",value=0x999)
        change("remove-property","Second",property_name="Values")
        change("detach","Second")
        self.assertEqual(raw,fixture())
    def test_new_vmad_plugin_attachment(self):
        from chimster.vmad_plugin import stage_mutation
        with TemporaryDirectory() as d:
            root=Path(d);out=root/"out";out.mkdir()
            p=root/"Test.esp";q=out/p.name
            hdr=record(b"TES4",sub(b"HEDR",struct.pack("<fII",1.7,2,0x801)))
            body=sub(b"EDID",b"Fixture\0")+sub(b"FULL",b"Unchanged\0")
            original=hdr+group(record(b"ACTI",body,0x800))
            p.write_bytes(original)
            pex=root/"Example.pex"
            pex.write_bytes(struct.pack(">IBBHQ",0xFA57C0DE,3,2,1,0)+b"\0\0"*4)
            r=inspect(p,"skyrimse",0x800)
            self.assertFalse(r["vmad_present"])
            result=stage_mutation(p,q,"skyrimse",0x800,"attach","Example",r["plugin_sha256"],r["sha256"],pex=pex)
            self.assertEqual(result["scripts"][0]["name"],"Example")
            self.assertIn(sub(b"FULL",b"Unchanged\0"),q.read_bytes())
            self.assertEqual(p.read_bytes(),original)
