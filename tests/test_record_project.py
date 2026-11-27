import unittest,struct
from pathlib import Path
from tempfile import TemporaryDirectory
from chimster.record_project import export,remove
from chimster.formids import FormIDs
from chimster.master_remap import reorder
from chimster.fnv_records import scan,subs,HEADER
from chimster.record_editor import inspect,edit_typed
class ProjectTests(unittest.TestCase):
    def test_create_edit_remove_remap(self):
        with TemporaryDirectory() as d:
            root=Path(d);a=root/"A.esp";b=root/"B.esp"
            row=lambda id:{"id":id,"type":"GLOB","fields":{"kind":"f","value":2.}}
            export({"schema":1,"records":[row("One")]},a);export({"schema":1,"records":[row("Two")]},b)
            p=root/"Source.esp";project={"schema":1,"records":[row("Local"),{"id":"List","type":"FLST","fields":{"entries":["Local",{"plugin":"A.esp","id":0x800}]}}]}
            exported=export(project,p,[a,b]);local=exported["records"]["local"]&0xffffff
            with self.assertRaises(ValueError):remove(project,"Local")
            self.assertEqual(len(remove(project,"List")["records"]),1)
            folder=root/"new";folder.mkdir();q=folder/p.name
            report=reorder(p,q,[b,a]);self.assertEqual(report["changed_list_references"],1)
            self.assertEqual(scan(q)["masters"],["B.esp","A.esp"])
            rec=next(x for x in scan(q)["records"] if x["signature"]=="FLST")
            with q.open("rb") as f:
                f.seek(rec["offset"]);_,size,*_=HEADER.unpack(f.read(24));refs=[struct.unpack("<I",v)[0] for k,v in subs(f.read(size)) if k==b"LNAM"]
            self.assertEqual(refs,[0x02000000|local,0x01000800])
            folder2=root/"edit";folder2.mkdir();r=inspect(p,p.name,local)
            edit_typed(p,folder2/p.name,p.name,local,"FLTV",3.5,r["payload_sha256"])
            self.assertEqual(next(f["value"] for f in inspect(folder2/p.name,p.name,local)["fields"] if f["tag"]=="FLTV"),3.5)
