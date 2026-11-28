import unittest,struct,tempfile
from pathlib import Path
from chimster.speedtree import parse,edit_scalars,tree_fields,model_path
from chimster.speedtree_lod import prepare,export
from chimster.lod_assets import dds_rgba

def tag(n,body=b""):return struct.pack("<I",n)+body
def text(n,value):return tag(n,struct.pack("<I",len(value))+value)
def fixture():
    return (text(1000,b"__IdvSpt_02_")+tag(1002)+text(2000,b"bark.dds")+
            tag(2005,struct.pack("<I",42))+tag(2006,struct.pack("<f",100))+
            tag(2001,struct.pack("<f",10000))+tag(2003,struct.pack("<f",1000))+
            tag(1003)+tag(1001)+tag(10000)+tag(10003,struct.pack("<I8f",1,0,0,1,0,1,1,0,1))+tag(10001))

class SpeedTreeTests(unittest.TestCase):
    def test_parse_and_lossless_edit(self):
        raw=fixture();info=parse(raw)
        self.assertTrue(info["complete"])
        self.assertEqual(info["fields"]["seed"],42)
        self.assertEqual(len(info["billboard_uvs"]),1)
        modified=edit_scalars(raw,{"seed":123,"size":200})
        self.assertEqual(parse(modified)["fields"]["seed"],123)
        self.assertEqual(parse(modified)["fields"]["size"],200)
        changed={t["payload"]+i for t in info["tokens"] if t["tag"] in (2005,2006) for i in range(4)}
        self.assertTrue(all(a==b for i,(a,b) in enumerate(zip(raw,modified)) if i not in changed))
        partial=raw+tag(999999,b"unparsed")
        self.assertFalse(parse(partial)["complete"])
        self.assertEqual(parse(partial)["unknown"]["offset"],len(raw))
        with self.assertRaises(ValueError):edit_scalars(partial,{"seed":1})
        with self.assertRaises(ValueError):parse(raw[:-1])
        with self.assertRaises(ValueError):edit_scalars(raw,{"near_distance":20000})
        with self.assertRaises(ValueError):model_path("../tree.spt")

    def test_tree_metadata(self):
        row=tree_fields({b"ICON":b"Leaves.dds\0",b"SNAM":struct.pack("<2I",42,11),b"BNAM":struct.pack("<2f",64,128),b"CNAM":struct.pack("<5fi2f",2,5,85,.5,.7,10,1,1)})
        self.assertEqual(row["seeds"],[42,11])
        self.assertEqual(row["billboard_dimensions"],(64.,128.))
        self.assertEqual(row["parameters"]["rock_speed"],1.)
        self.assertEqual(row["leaf_texture"],"Leaves.dds")

    def test_billboard_conversion(self):
        class Assets:
            def get(self,p):
                if p=="trees/Oak.spt":return fixture()
                if p=="textures/trees/billboards/Oak.dds":return dds_rgba(2,2,bytes((100,120,30,255,0,0,0,0))*2)
                raise FileNotFoundError(p)
        group,files,info=prepare(Assets(),"Oak.spt",(64,128))
        mesh,d,n,cut=group
        self.assertEqual(len(mesh.faces),8)
        self.assertEqual(max(v[2] for v in mesh.vertices),128)
        self.assertTrue(cut)
        self.assertEqual(set(files),{d,n})
        self.assertTrue(info["spt_complete"])
        with tempfile.TemporaryDirectory() as tmp:
            out=Path(tmp)/"out"
            report=export("new-vegas",Assets(),"Oak.spt",(64,128),out)
            self.assertTrue((out/report["mesh"]).is_file())
            self.assertFalse(report["native_spt_generated"])
        class Missing(Assets):
            def get(self,p):
                if p.endswith(".spt"):return fixture()
                raise FileNotFoundError(p)
        with self.assertRaises(ValueError):prepare(Missing(),"Oak.spt",(64,128))

    def test_project_lossless_and_relink(self):
        import json
        from chimster.speedtree_project import import_bytes,export_project,inspect_source,relink
        raw=fixture()
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);project=root/"tree"
            meta=import_bytes(raw,project,"Oak.spt")
            self.assertTrue(meta["parse_complete"])
            self.assertEqual(meta["textures"][0]["index"],0)
            result=export_project(project,root/"original.spt")
            self.assertTrue(result["byte_identical"])
            self.assertEqual((root/"original.spt").read_bytes(),raw)
            (project/"edits.json").write_text(json.dumps({"scalars":{"seed":44},"textures":{"0":"Bark/NewBark.dds"}}))
            result=export_project(project,root/"edited.spt")
            self.assertFalse(result["byte_identical"])
            edited=inspect_source((root/"edited.spt").read_bytes())
            self.assertEqual(edited["fields"]["seed"],44)
            self.assertEqual(edited["textures"][0]["value"],"Bark/NewBark.dds")
            self.assertEqual((project/"source.spt").read_bytes(),raw)
            with self.assertRaises(FileExistsError):export_project(project,root/"edited.spt")
            (project/"source.spt").write_bytes(raw+b"x")
            with self.assertRaises(ValueError):export_project(project,root/"bad.spt")
        with self.assertRaises(ValueError):relink(raw,{"0":"../escape.dds"})

    def test_opaque_variant_roundtrip(self):
        import json
        from chimster.speedtree_project import import_bytes,export_project
        unknown=fixture()+tag(987654,b"opaque payload")
        variant=fixture().replace(b"__IdvSpt_02_",b"__IdvSpt_99_")
        for raw in (unknown,variant):
            with tempfile.TemporaryDirectory() as tmp:
                root=Path(tmp);project=root/"tree"
                meta=import_bytes(raw,project)
                self.assertFalse(meta["parse_complete"])
                result=export_project(project,root/"copy.spt")
                self.assertTrue(result["byte_identical"])
                self.assertEqual((root/"copy.spt").read_bytes(),raw)
                (project/"edits.json").write_text(json.dumps({"scalars":{"seed":1},"textures":{}}))
                with self.assertRaises(ValueError):export_project(project,root/"edited.spt")

    def test_texture_indices_include_empty_slots(self):
        from chimster.speedtree_project import inspect_source,relink
        raw=fixture()+tag(70000)+text(70002,b"")+text(70004,b"normal.dds\0")+tag(70001)
        info=inspect_source(raw)
        self.assertEqual([r["value"] for r in info["textures"]],["bark.dds","","normal.dds"])
        edited=relink(raw,{"1":"Leaf.dds","2":"LongerNormal.dds"})
        self.assertEqual([r["value"] for r in inspect_source(edited)["textures"]],["bark.dds","Leaf.dds","LongerNormal.dds"])
        self.assertIn(b"LongerNormal.dds\0",edited)
