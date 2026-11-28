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

    def test_dds_source_decode_and_alpha(self):
        from chimster.lod_dds import decode
        from chimster.lod_assets import dds_rgba
        from chimster.texture_processing import dds
        from chimster.world_lod_materials import alpha
        raw=bytes((255,0,0,255))*16
        self.assertEqual(decode(dds_rgba(4,4,raw)),(4,4,raw))
        for kind in ("BC1","BC3"):
            w,h,pixels=decode(dds(4,4,raw,kind=kind,mips=False))
            self.assertEqual((w,h),(4,4))
            self.assertTrue(all(pixels[i]>240 for i in range(0,len(pixels),4)))
        self.assertAlmostEqual(alpha({0:1,1:0,17:0,18:0},.5,.5),.25)

    def test_skirts_and_incremental(self):
        grid=[[float(x) for x in range(33)] for _ in range(33)]
        flat=macro_mesh({(0,0):grid},0,0,4)
        skirt=macro_mesh({(0,0):grid},0,0,4,256)
        self.assertGreater(len(skirt.faces),len(flat.faces))
        self.assertEqual(skirt.vertices[:len(flat.vertices)],flat.vertices)
        draft=Draft(Browser.open([]))
        world=draft.create_world("CacheWorld","Cache World",(0,0),(1,1))
        with tempfile.TemporaryDirectory() as d:
            a,b,c=(Path(d)/p for p in ("first","second","third"))
            initial=export(draft.index(),world,a,levels=(4,),size=64)
            repeat=export(draft.index(),world,b,levels=(4,),size=64,previous=a)
            self.assertEqual(repeat["reused_tiles"],1)
            self.assertEqual(repeat["rebuilt_tiles"],0)
            (a/next(iter(initial["tiles"][0]["files"]))).write_bytes(b"damaged")
            repaired=export(draft.index(),world,c,levels=(4,),size=64,previous=a)
            self.assertEqual(repaired["rebuilt_tiles"],1)

    def test_paired_object_atlas(self):
        from chimster.world_lod_atlas import build
        from chimster.lod_assets import dds_rgba
        mesh=terrain_grid([[0.,0.],[0.,0.]])
        class Assets:
            def get(self,path):
                return dds_rgba(4,4,bytes((128,128,255,255))*16)
        active=[(mesh,"textures/a.dds","textures/a_n.dds"),(mesh,"textures/b.dds","textures/b_n.dds")]
        result,remaining,issues=build(active,Assets(),size=32,maximum=256)
        self.assertEqual(len(result["mesh"].faces),4)
        self.assertEqual(result["groups"],2)
        self.assertEqual(remaining,[])
        self.assertEqual(issues,[])
        self.assertEqual(len(result["diffuse"]),result["size"]**2*4)
        self.assertNotEqual(result["mesh"].uv[:4],result["mesh"].uv[4:])
        self.assertEqual(mesh.uv,[(0.,0.),(1.,0.),(0.,1.),(1.,1.)])

    def test_grouped_reader(self):
        from chimster.fnv_lod_nif import read_static_groups
        mesh=terrain_grid([[1.,2.],[2.,3.]])
        raw=encode_groups([(mesh,"textures/a.dds","textures/a_n.dds"),(mesh,"textures/b.dds","textures/b_n.dds")],"companion")
        groups=read_static_groups(raw)
        self.assertEqual(len(groups),2)
        self.assertEqual(sum(len(m.faces) for m,_,_ in groups),4)
        self.assertEqual(groups[0][0].vertices,mesh.vertices)
        with self.assertRaises(ValueError):read_static(raw)

    def test_native_vegetation_candidate(self):
        from chimster.world_lod_vegetation import build
        from chimster.flora import Recipe
        with tempfile.TemporaryDirectory() as d:
            out=Path(d)/"tree"
            result=build(Recipe(seed=42,branches=4,leaves=12),out,size=64,views=2)
            self.assertEqual(result["billboard_triangles"],8)
            self.assertFalse(result["external_tools"])
            self.assertFalse(result["native_tree_tiles"])
            for path in result["files"]:self.assertTrue((out/path).is_file())
            nif=next(p for p in result["files"] if p.endswith(".nif"))
            self.assertIn("NiAlphaProperty",check((out/nif).read_bytes(),8)["block_types"])

    def test_skyrim_tree_binary_layout(self):
        from chimster.world_lod_tree_tiles import encode_types,decode_types,encode_tile,decode_tile
        from chimster.world_lod_metadata import skyrim_settings,read_skyrim_settings
        rows=[(0,128.,256.,0.,0.,.5,.5,0)]
        raw=encode_types(rows)
        self.assertEqual(len(raw),36)
        self.assertEqual(decode_types(raw),rows)
        group={0:[(-100.,200.,300.,0.,1.,0x01001234,0,0)]}
        raw=encode_tile(group)
        self.assertEqual(len(raw),44)
        self.assertEqual(decode_tile(raw),group)
        with self.assertRaises(ValueError):decode_tile(raw[:-1])
        with self.assertRaises(ValueError):encode_tile({0:group[0]*2})
        settings=read_skyrim_settings(skyrim_settings([(-5,-2),(20,33)]))
        self.assertEqual(settings["southwest"],(-32,-32))
        self.assertEqual(settings["stride"],128)

    def test_shared_fine_macro_perimeters(self):
        # The two edge heights are identical but deliberately non-linear.
        grid=[[float((y%7)**2) for x in range(33)] for y in range(33)]
        coarse=macro_mesh({(7,0):grid},0,0,8,stitch=True)
        fine=macro_mesh({(8,0):grid},8,0,4,stitch=True)
        a=sorted((y,z) for x,y,z in coarse.vertices if x==8*4096)
        b=sorted((y,z) for x,y,z in fine.vertices if x==0)
        self.assertEqual(a,b)
        self.assertEqual(len(a),17)

    def test_cutout_nif_roundtrip(self):
        from chimster.fnv_lod_nif import read_static_groups
        mesh=terrain_grid([[0.,0.],[0.,0.]])
        raw=encode(mesh,"textures/tree.dds","textures/tree_n.dds","companion",cutout=True)
        self.assertIn("NiAlphaProperty",check(raw,2)["block_types"])
        groups=read_static_groups(raw,include_cutout=True)
        self.assertEqual(groups[0][1:],("textures/tree.dds","textures/tree_n.dds",True))
        with self.assertRaises(ValueError):read_static_groups(raw)

    def test_modern_candidate_streams(self):
        from chimster.modern_lod_codec import encode_groups,inspect,export_tile
        mesh=terrain_grid([[1.,2.],[2.,3.]])
        for game,stream in (("skyrim",83),("skyrim-se",100),("fallout4",130)):
            raw=encode_groups([(mesh,"textures/a.dds","textures/a_n.dds")],game)
            info=inspect(raw,game)
            self.assertEqual(info["stream"],stream)
            self.assertEqual(info["triangles"],2)
            self.assertEqual(info["vertices"],4)
            self.assertFalse(info["runtime_verified"])
            with self.assertRaises(ValueError):inspect(raw[:-1],game)
            with tempfile.TemporaryDirectory() as d:
                result=export_tile(game,"object","TestWorld",4,-4,0,mesh,"textures/a.dds","textures/a_n.dds",d,True)
                self.assertTrue(Path(result["path"]).is_file())
                self.assertTrue(result["path"].endswith(".bto"))
                self.assertIn("NiAlphaProperty",result["block_types"])
                with self.assertRaises(FileExistsError):
                    export_tile(game,"object","TestWorld",4,-4,0,mesh,"textures/a.dds","textures/a_n.dds",d,True)
