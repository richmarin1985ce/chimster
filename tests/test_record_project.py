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

    def test_generated_world_master_insertion(self):
        from chimster.fnv_world import build
        from chimster.worldspace import Terrain
        from chimster.native_parser import parse,subrecords
        from chimster.record_graph import Slots
        with TemporaryDirectory() as d:
            root=Path(d);a=root/"A.esp";source=root/"World.esp"
            export({"schema":1,"records":[{"id":"Global","type":"GLOB",
                   "fields":{"kind":"f","value":1.}}]},a)
            terrain=Terrain(tuple(tuple(0. for _ in range(33)) for _ in range(33)),4,0)
            content={"statics":[{"id":"Rock","bounds":[-1,-1,0,1,1,2],"model":"meshes/rock.nif"}],
                     "placements":[{"base":"Rock","x_m":5,"y_m":5,"z_m":0}]}
            build(terrain,source,origin=(0,0),content=content)
            folder=root/"stage";folder.mkdir();dest=folder/source.name
            result=reorder(source,dest,[a],allow_set_change=True)
            self.assertGreater(result["changed_group_owners"],0)
            self.assertEqual(result["changed_embedded_references"],1)
            def inspect_world(path):
                report=scan(path);slots=Slots(path.name,report["masters"])
                owners=[(g["type"],g.get("owner")) for g in report["groups"]]
                def walk(nodes):
                    for node in nodes:
                        if node.signature==b"REFR":
                            ref=dict(subrecords("new-vegas",node))[b"NAME"]
                            yield slots.decode(struct.unpack("<I",ref)[0])
                        yield from walk(node.children)
                return owners,list(walk(parse("new-vegas",path.read_bytes())))
            self.assertEqual(inspect_world(source),inspect_world(dest))

    def test_compressed_master_remap(self):
        import zlib
        from dataclasses import replace
        from chimster.native_parser import parse,subrecords
        from chimster.native_serialization import serialize
        with TemporaryDirectory() as d:
            root=Path(d);a=root/"A.esp";source=root/"Compressed.esp"
            spec={"schema":1,"records":[{"id":"Global","type":"GLOB",
                   "fields":{"kind":"f","value":1.}},
                   {"id":"List","type":"FLST","fields":{"entries":["Global"]}}]}
            export(spec,source);export({"schema":1,"records":spec["records"][:1]},a)
            def compress(nodes):
                result=[]
                for node in nodes:
                    if node.signature==b"FLST":
                        header=bytearray(node.header)
                        struct.pack_into("<I",header,8,0x40000)
                        node=replace(node,header=bytes(header),payload=struct.pack("<I",len(node.payload))+zlib.compress(node.payload))
                    elif node.children:node=replace(node,children=compress(node.children))
                    result.append(node)
                return tuple(result)
            source.write_bytes(serialize("new-vegas",compress(parse("new-vegas",source.read_bytes()))))
            folder=root/"stage";folder.mkdir();dest=folder/source.name
            result=reorder(source,dest,[a],allow_set_change=True)
            self.assertEqual(result["compressed_records"],1)
            records=scan(dest)["records"];row=next(r for r in records if r["signature"]=="FLST")
            self.assertTrue(row["flags"]&0x40000)
            def visit(nodes):
                for node in nodes:
                    if node.signature==b"FLST":yield dict(subrecords("new-vegas",node))[b"LNAM"]
                    yield from visit(node.children)
            global_id=next(r["local_id"] for r in records if r["signature"]=="GLOB")
            self.assertEqual(list(visit(parse("new-vegas",dest.read_bytes()))),[struct.pack("<I",0x01000000|global_id)])
