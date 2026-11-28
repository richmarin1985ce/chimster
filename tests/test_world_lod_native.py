import tempfile
import unittest
from pathlib import Path
from chimster.world_lod_native import audit
from chimster.world_lod_objects import sibling

class WorldLODTests(unittest.TestCase):
    def test_sibling_path(self):
        self.assertEqual(sibling(r"Architecture\Tower.NIF"),"meshes/Architecture/Tower_lod.nif")
        with self.assertRaises(ValueError):sibling("../outside.nif")

    def test_audit_world_filter_and_bad_headers(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder)
            mesh=root/"meshes/landscape/lod/TestWorld/TestWorld.level4.x-4.y0.nif"
            mesh.parent.mkdir(parents=True)
            mesh.write_bytes(b"Gamebryo File Format, Version 20.2.0.7\n"+bytes(128))
            tex=root/"textures/landscape/lod/TestWorld/diffuse/TestWorld.level4.x-4.y0.dds"
            tex.parent.mkdir(parents=True)
            tex.write_bytes(b"DDS "+bytes(124))
            report=audit(root,"TestWorld","newvegas")
            self.assertTrue(report["valid_headers"])
            self.assertFalse(report["engine_verified"])
            self.assertEqual({r["kind"] for r in report["files"]},{"terrain","texture"})
            self.assertEqual({r["level"] for r in report["files"]},{4})
            tex.write_bytes(b"invalid")
            self.assertFalse(audit(root,"TestWorld","newvegas")["valid_headers"])
            self.assertFalse(audit(root,"OtherWorld","newvegas")["valid_headers"])
