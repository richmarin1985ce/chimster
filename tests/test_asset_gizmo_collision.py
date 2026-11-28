import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch
from chimster.flora import Mesh
from chimster.asset_forge import Session
from chimster.asset_gizmo import gesture
from chimster.asset_project import save,load

def square():
    return Mesh([(0,0,0),(1,0,0),(1,1,0),(0,1,0)],[(0,0),(1,0),(1,1),(0,1)],[((0,1,2),"a"),((0,2,3),"a")])

class GizmoCollisionTests(unittest.TestCase):
    def test_gizmo_and_undo(self):
        s=Session(square())
        s.gizmo("face",[0,1],"move",2,2)
        self.assertTrue(all(v[2]==2 for v in s.mesh.vertices))
        s.gizmo("face",[0,1],"rotate",2,90)
        self.assertAlmostEqual(s.mesh.vertices[0][0],1)
        self.assertAlmostEqual(s.mesh.vertices[0][1],0)
        s.gizmo("face",[0,1],"scale",0,2)
        self.assertAlmostEqual(s.mesh.vertices[0][0],1.5)
        s.undo();s.undo();s.undo()
        self.assertEqual(s.mesh,square())
        self.assertAlmostEqual(gesture("move",(0,0),(10,0),(5,0)),2)
        with self.assertRaises(ValueError):gesture("move",(0,0),(10,0),(0,0))
    def test_collision_review_and_native_export(self):
        s=Session(square())
        s.add_collision_box("face",[0,1],"floor","wood")
        self.assertFalse(s.collision_stale)
        self.assertEqual(s.collision["boxes"][0]["min"],[-.01,-.01,-.01])
        s.gizmo("face",[0,1],"move",2,1)
        self.assertTrue(s.collision_stale)
        with self.assertRaises(ValueError):
            s.export_nif("new.nif","newvegas",1,"helper",compound=True)
        s.undo()
        self.assertFalse(s.collision_stale)
        with patch("chimster.modern_nif.export") as exporter:
            s.export_nif("new.nif","newvegas",1,"helper",compound=True)
            self.assertEqual(exporter.call_args.kwargs["compound_collision"],s.collision)
        with self.assertRaises(ValueError):
            s.export_nif("new.nif","skyrim",1,"helper",compound=True)
        s.redo()
        self.assertTrue(s.collision_stale)
    def test_collision_persistence_and_legacy_schema(self):
        import json
        s=Session(square());s.add_collision_box("face",[0,1],"floor")
        s.gizmo("face",[0,1],"move",2,1)
        with TemporaryDirectory() as d:
            p=Path(d)/"a.casset";save(s,p);restored=load(p)
            self.assertEqual(restored.collision,s.collision)
            self.assertTrue(restored.collision_stale)
            data=json.loads(p.read_text());data["schema"]=1
            del data["collision"];del data["collision_stale"]
            q=Path(d)/"old.casset";q.write_text(json.dumps(data))
            self.assertIsNone(load(q).collision)
