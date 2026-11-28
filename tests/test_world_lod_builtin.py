import unittest,tempfile
from pathlib import Path
from chimster.lod import terrain_grid
from chimster.fnv_lod_nif import encode,encode_groups,check,read_static,blocks
from chimster.world_lod_builtin import macro_mesh,export
from chimster.world_lod_metadata import fnv_settings,read_fnv_settings
from chimster.world_browser import Browser
from chimster.world_draft import Draft

class BuiltinLODTests(unittest.TestCase):
    def test_nif_roundtrip(self):
        mesh=terrain_grid([[1.,2.],[2.,3.]])
        textures=("textures/lod/a.dds","textures/lod/a_n.dds")
        raw=encode(mesh,*textures,"companion")
        info=check(raw,2)
        self.assertEqual(info["vertices"],4)
        decoded,material=read_static(raw)
        self.assertEqual(material,textures)
        self.assertEqual(decoded.vertices,mesh.vertices)
        self.assertEqual([f for f,_ in decoded.faces],[f for f,_ in mesh.faces])
        with self.assertRaises(ValueError):blocks(raw[:-1])
        object_raw=encode_groups([(mesh,*textures),(mesh,"textures/lod/b.dds","textures/lod/b_n.dds")],"object",16384)
        self.assertEqual(check(object_raw,4)["triangles"],4)
        self.assertEqual([t for t,b in blocks(object_raw)].count("BSSegmentedTriShape"),2)
    def test_settings(self):
        raw=fnv_settings([(-4,-1),(7,8)])
        self.assertEqual(len(raw),24)
        self.assertEqual(read_fnv_settings(raw)["min_cell"],(-4,-1))
        self.assertEqual(read_fnv_settings(raw)["max_cell"],(7,8))
    def test_terrain_shared_edge(self):
        grid=[[0.]*33 for _ in range(33)]
        mesh=macro_mesh({(-4,0):grid,(-3,0):grid},-4,0,4)
        self.assertEqual(len(mesh.vertices),33*17)
        self.assertEqual(len(mesh.faces),2*16*16*2)
        changed=[[1.]*33 for _ in range(33)]
        with self.assertRaises(ValueError):macro_mesh({(-4,0):grid,(-3,0):changed},-4,0,4)
    def test_world_package_without_external_tools(self):
        draft=Draft(Browser.open([]))
        world=draft.create_world("LODDemo","LOD Demo",(0,0),(1,1))
        with tempfile.TemporaryDirectory() as d:
            output=Path(d)/"lod"
            manifest=export(draft.index(),world,output,levels=(4,),size=64)
            self.assertFalse(manifest["external_tools"])
            self.assertFalse(manifest["native_runtime_assets"])
            self.assertEqual(len(manifest["tiles"]),1)
            self.assertTrue((output/"LODSettings/LODDemo.dlodsettings").exists())
            for path in manifest["tiles"][0]["files"]:self.assertTrue((output/path).is_file())
