import json
import struct
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch, MagicMock
from chimster.project import Project
from chimster.mcp_bridge import Bridge
from chimster.mcp_extended import native_session
from chimster.mcp_structure import sub
from chimster.native_parser import Node
from chimster.native_profiles import PROFILES
from chimster.native_serialization import serialize
from chimster.worldspace import Terrain
from chimster.fnv_world import build
from chimster.scene import Scene,Instance
from chimster.flora import Mesh

def fixture(profile):
    size=PROFILES[profile].record_header
    def rec(sig,body,form=0):
        header=struct.pack("<4sIIII",sig,len(body),0,form,0)+bytes(size-20)
        return Node(sig,header,body)
    head=rec(b"TES4",sub(b"HEDR",struct.pack("<fII",1.,2,0x801)))
    glob=rec(b"GLOB",sub(b"EDID",b"Original\0")+sub(b"FNAM",b"f")+sub(b"FLTV",struct.pack("<f",1.)),0x800)
    group=Node(b"GRUP",struct.pack("<4sI4siI",b"GRUP",size,b"GLOB",0,0)+bytes(size-20),b"",(glob,))
    return serialize(profile,(head,group))

class StructureTests(unittest.TestCase):
    def test_synthetic_profiles(self):
        for game,profile in (("oblivion","oblivion"),("fallout3","fallout3"),("newvegas","new-vegas"),("skyrim","skyrim"),("skyrimse","skyrim-se"),("fallout4","fallout4")):
            with self.subTest(game=game),tempfile.TemporaryDirectory() as d:
                root=Path(d);p=Project.create(root/"project","Demo",game)
                src=root/"Example.esp";src.write_bytes(fixture(profile))
                p.add("plugin","plugin",src,0)
                b=Bridge(p,allow_edit=True,allow_native=True)
                self.addCleanup(b.jobs.close)
                m,a,s,_=native_session(p,"plugin")
                ident=s.identity_token(next(iter(s.rows)))
                args=dict(id="plugin",identity=ident,operation="duplicate-global",revision=1,sha256=a["sha256"],new_edid="Copy")
                readonly=Bridge(p)
                self.addCleanup(readonly.jobs.close)
                self.assertIsNone(readonly.structure.preview(**args)["proposal_token"])
                q=b.structure.preview(**args)
                self.assertEqual(p.read()["revision"],1)
                b.structure.apply(q["proposal_token"])
                _,a,s,_=native_session(p,"plugin")
                self.assertEqual(len(s.rows),2)
                duplicate=q["summary"]["new_identity"]
                self.assertEqual(dict(s.rows[s.resolve_identity(duplicate)]["parts"])[b"EDID"],b"Copy\0")
                q=b.structure.preview(id="plugin",identity=duplicate,operation="set-global",revision=2,sha256=a["sha256"],value="3.5")
                b.structure.apply(q["proposal_token"])
                _,_,s,_=native_session(p,"plugin")
                self.assertEqual(struct.unpack("<f",dict(s.rows[s.resolve_identity(duplicate)]["parts"])[b"FLTV"])[0],3.5)
                b.creation.recover("undo",3)
                b.creation.recover("undo",4)
                self.assertEqual(p.object("plugin").read_bytes(),src.read_bytes())

    def test_exterior_relocation(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);p=Project.create(root/"project","Demo","newvegas")
            t=Terrain(tuple(tuple(0. for _ in range(65)) for _ in range(65)))
            src=root/"World.esp"
            build(t,src,origin=(0,0),content={"statics":[{"id":"Tree","model":"meshes/tree.nif","bounds":[0,0,0,1,1,1]}],
                 "placements":[{"id":"TreeA","base":"Tree","x_m":0,"y_m":0,"z_m":0}]})
            p.add("world","plugin",src,0)
            b=Bridge(p,allow_edit=True,allow_native=True)
            self.addCleanup(b.jobs.close)
            _,a,s,_=native_session(p,"world")
            ref=next(path for path in s.rows if s.node(path).signature==b"REFR")
            dest=next(path for path,row in s.rows.items() if s.node(path).signature==b"CELL" and any(k==b"XCLC" and struct.unpack_from("<ii",v)==(1,0) for k,v in row["parts"]))
            args=dict(id="world",identity=s.identity_token(ref),operation="relocate-reference",revision=1,
                      sha256=a["sha256"],destination=s.identity_token(dest),x=4100,y=10,z=0)
            with self.assertRaises(ValueError):b.structure.preview(**{**args,"x":10})
            q=b.structure.preview(**args)
            self.assertEqual(q["summary"]["after"],[4100,10,0])
            b.structure.apply(q["proposal_token"])
            _,_,after,_=native_session(p,"world")
            self.assertEqual(len(after.rows),len(s.rows))
            self.assertEqual(after.node(after.resolve_identity(args["identity"])[:-1]).header[8:12],s.node(dest).header[12:16])
            b.creation.recover("undo",2)
            self.assertEqual(p.object("world").read_bytes(),src.read_bytes())

    def test_scene_render_adapter(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);p=Project.create(root/"project","Demo","newvegas")
            mesh=Mesh([(0,0,0),(1,0,0),(0,0,1)],[(0,0),(1,0),(0,1)],[((0,1,2),"default")])
            src=root/"scene.json";Scene({"mesh":mesh},[Instance("one","mesh"),Instance("two","mesh",x=2)]).save(src)
            p.add("scene","scene",src,0)
            b=Bridge(p,allow_create=True)
            self.addCleanup(b.jobs.close)
            with patch("chimster.gpu_viewport.Renderer") as renderer:
                instance=renderer.return_value
                instance.render.return_value=(bytes(960*540*4),{"objects":2})
                q=b.production.preview("scene-render","scene","screenshot",1)
                self.assertEqual(q["summary"]["instances"],2)
                self.assertEqual(q["summary"]["triangles"],2)
                instance.close.assert_called_once()
            b.production.apply(q["proposal_token"])
            self.assertTrue(p.object("screenshot").read_bytes().startswith(b"\x89PNG\r\n\x1a\n"))

if __name__=="__main__":
    unittest.main()
