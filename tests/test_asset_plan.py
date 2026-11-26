import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from chimster.asset_plan import static_proposal

class AssetPlanTests(unittest.TestCase):
    def test_exact_material_group(self):
        with TemporaryDirectory() as d:
            root=Path(d)
            (root/"meshes").mkdir()
            (root/"textures").mkdir()
            (root/"meshes/a.nif").write_bytes(b"fixture only")
            (root/"meshes/b.nif").write_bytes(b"fixture only")
            (root/"textures/a.dds").write_bytes(b"fixture only")
            m={"shader":"test","alpha":"cutout","tiling":False,"textures":{"diffuse":"textures/a.dds"}}
            a=[{"editor_id":"TreeA","model":"meshes/a.nif","materials":[m]},
               {"editor_id":"TreeB","model":"meshes/b.nif","materials":[m]}]
            r=static_proposal("newvegas",root,a)
            self.assertEqual(r["material_groups"][0]["editor_ids"],["TreeA","TreeB"])
            self.assertFalse(r["writes_plugin"])
    def test_obj_rejected(self):
        with TemporaryDirectory() as d:
            with self.assertRaises(ValueError):
                static_proposal("newvegas",d,[{"editor_id":"TreeA","model":"meshes/a.obj"}])
