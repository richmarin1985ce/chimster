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

    def test_explicit_master_set_change(self):
        from chimster.record_graph import Slots
        with TemporaryDirectory() as d:
            root=Path(d);a=root/"A.esp";b=root/"B.esp"
            row=lambda name:{"id":name,"type":"GLOB","fields":{"kind":"f","value":2.}}
            for name,path in (("One",a),("Two",b)):
                export({"schema":1,"records":[row(name)]},path)
            p=root/"Source.esp"
            spec={"schema":1,"records":[row("Local"),{"id":"List","type":"FLST",
                   "fields":{"entries":["Local",{"plugin":"A.esp","id":0x800}]}}]}
            export(spec,p,[a])
            stage=root/"add";stage.mkdir();q=stage/p.name
            with self.assertRaises(ValueError):
                reorder(p,q,[b,a])
            self.assertFalse(q.exists())
            report=reorder(p,q,[b,a],allow_set_change=True)
            self.assertEqual(report["added_masters"],["b.esp"])
            self.assertEqual(scan(q)["masters"],["B.esp","A.esp"])
            def refs(path):
                info=scan(path)
                slots=Slots(path.name,info["masters"])
                record=next(r for r in info["records"] if r["signature"]=="FLST")
                with path.open("rb") as stream:
                    stream.seek(record["offset"])
                    _,size,*_=HEADER.unpack(stream.read(24))
                    return [slots.decode(struct.unpack("<I",v)[0]) for k,v in subs(stream.read(size)) if k==b"LNAM"]
            self.assertEqual(refs(p),refs(q))
            stage=root/"remove";stage.mkdir();r=stage/p.name
            report=reorder(q,r,[a],allow_set_change=True)
            self.assertEqual(report["removed_masters"],["b.esp"])
            self.assertEqual(refs(p),refs(r))
            stage=root/"blocked";stage.mkdir();out=stage/p.name
            with self.assertRaises(ValueError):
                reorder(r,out,[],allow_set_change=True)
            self.assertFalse(out.exists())

    def test_remove_last_unused_master(self):
        with TemporaryDirectory() as d:
            root=Path(d);master=root/"A.esp";source=root/"Local.esp"
            spec={"schema":1,"records":[{"id":"Local","type":"GLOB",
                  "fields":{"kind":"f","value":2.}}]}
            export(spec,master);export(spec,source,[master])
            stage=root/"out";stage.mkdir();out=stage/source.name
            result=reorder(source,out,[],allow_set_change=True)
            self.assertEqual(result["removed_masters"],["a.esp"])
            self.assertEqual(scan(out)["masters"],[])
            self.assertEqual([(r["origin"],r["local_id"]) for r in scan(source)["records"]],
                             [(r["origin"],r["local_id"]) for r in scan(out)["records"]])
