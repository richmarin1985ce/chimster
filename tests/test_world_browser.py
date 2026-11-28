import struct
import tempfile
import unittest
from pathlib import Path
from chimster.world_browser import Browser
from chimster.record_graph import Identity


def sub(tag, data):
    return struct.pack("<4sH", tag, len(data)) + data


def record(tag, fid, *parts, flags=0):
    data = b"".join(parts)
    return struct.pack("<4s5I", tag, len(data), flags, fid, 0, 0) + data


def group(kind, owner, *records):
    data = b"".join(records)
    return struct.pack("<4sIIiII", b"GRUP", 24+len(data), owner, kind, 0, 0) + data


def edid(name):
    return sub(b"EDID", name.encode("ascii")+b"\0")


class WorldBrowserTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.base = Path(self.tmp.name)/"Base.esm"
        self.patch = Path(self.tmp.name)/"Patch.esp"
        self.world = Identity("base.esm", 0x800)
        self.cell = Identity("base.esm", 0x801)
        self.ref = Identity("base.esm", 0x802)
        self.static = Identity("base.esm", 0x803)
        header = record(b"TES4", 0)
        base = record(b"STAT", 0x803, edid("RoadSign"))
        world = record(b"WRLD", 0x800, edid("TestWorld"))
        cell = record(b"CELL", 0x801, edid("NegativeCell"),
                      sub(b"XCLC", struct.pack("<ii", -2, 3)), sub(b"DATA", b"\0"))
        ref = record(b"REFR", 0x802, sub(b"NAME", struct.pack("<I",0x803)),
                     sub(b"DATA", struct.pack("<6f", -7000, 13000, 5, 0, 0, 1)))
        self.base.write_bytes(header + base + world + group(1,0x800,cell,
             group(6,0x801,group(9,0x801,ref))))

    def test_grid_and_reference_search(self):
        browser = Browser.open([self.base])
        self.assertEqual(browser.cell_rows(self.world)[0]["grid"], (-2,3))
        self.assertEqual(browser.coordinates[self.world,(-2,3)][0]["key"],self.cell)
        row = browser.object_rows(self.cell,"roadsign")[0]
        self.assertEqual(row["key"],self.ref)
        self.assertEqual(row["bucket"],9)
        self.assertEqual(browser.details(row)["base_name"],"RoadSign")

    def test_override_deletion_and_provenance(self):
        header = record(b"TES4",0,sub(b"MAST",b"Base.esm\0"))
        replacement = record(b"CELL",0x801,edid("Renamed"),sub(b"XCLC",struct.pack("<ii",-2,3)))
        deletion = record(b"REFR",0x802,flags=0x20)
        self.patch.write_bytes(header+group(1,0x800,replacement,group(6,0x801,group(9,0x801,deletion))))
        browser = Browser.open([self.base,self.patch])
        self.assertEqual(browser.name(browser.active[self.cell]),"Renamed")
        self.assertEqual(browser.history[self.cell],["base.esm","patch.esp"])
        self.assertEqual(browser.object_rows(self.cell),[])
        self.assertNotIn(self.ref,browser.active)
        with self.assertRaises(ValueError):
            Browser.open([self.patch,self.base])

    def test_interiors_and_conflicting_coordinates(self):
        header = record(b"TES4",0,sub(b"MAST",b"Base.esm\0"))
        duplicate = record(b"CELL",0x01000800,edid("Conflict"),sub(b"XCLC",struct.pack("<ii",-2,3)))
        interior = record(b"CELL",0x01000801,edid("Room"),sub(b"DATA",b"\1"))
        self.patch.write_bytes(header+interior+group(1,0x800,duplicate))
        browser = Browser.open([self.base,self.patch])
        self.assertEqual(len(browser.coordinates[self.world,(-2,3)]),2)
        self.assertTrue(any("Duplicate coordinates" in issue for issue in browser.issues))
        self.assertTrue(browser.cell_rows(None)[0]["interior"])


    def test_preview_origin_and_persistent_markers(self):
        from chimster.world_preview import preview
        header = record(b"TES4",0,sub(b"MAST",b"Base.esm\0"))
        persistent_cell = record(b"CELL",0x01000800,edid("Persistent"))
        persistent = record(b"REFR",0x01000801,
            sub(b"NAME",struct.pack("<I",0x803)),
            sub(b"DATA",struct.pack("<6f",-7000,13000,128,0,0,0)),flags=0x400)
        land = record(b"LAND",0x01000802,sub(b"VHGT",struct.pack("<f",2)+bytes(1092)))
        neighbor = record(b"CELL",0x01000803,sub(b"XCLC",struct.pack("<ii",-1,3)))
        self.patch.write_bytes(header+group(1,0x800,persistent_cell,
            group(6,0x01000800,group(8,0x01000800,persistent)),
            group(6,0x801,group(9,0x801,land)),neighbor))
        browser = Browser.open([self.base,self.patch])
        scene, report = preview(browser,self.cell,1)
        self.assertEqual(report["cells"],2)
        self.assertEqual(report["land_tiles"],1)
        self.assertEqual(report["proxy_references"],2)
        self.assertEqual(report["origin_game_units"],(-8192,12288,0))
        marker = next(i for i in scene.instances if i.id=="patch.esp:000801")
        self.assertAlmostEqual(marker.x,1192/128)
        self.assertAlmostEqual(marker.z,1)
        terrain = next(i for i in scene.instances if i.id.startswith("land:"))
        self.assertAlmostEqual(scene.assets[terrain.asset].vertices[0][2],16/128)
        with self.assertRaises(ValueError):
            preview(browser,self.cell,3)



    def test_draft_cell_and_placement(self):
        from chimster.world_draft import Draft
        browser=Browser.open([self.base])
        draft=Draft(browser)
        key=draft.create("NewCell",self.world,(-1,3))
        ref=draft.place(key,self.static,(-2048,14000,128))
        self.assertIn(ref,draft.index().active)
        self.assertNotIn(key,browser.active)
        with self.assertRaises(ValueError):
            draft.create("Duplicate",self.world,(-1,3))
        with self.assertRaises(ValueError):
            draft.place(key,self.static,(0,0,0))
        draft.rename(key,"RenamedCell")
        self.assertEqual(draft.index().active[key]["editor_id"],"RenamedCell")
        draft.undo()
        self.assertEqual(draft.index().active[key]["editor_id"],"NewCell")
        draft.redo()
        out=Path(self.tmp.name)/"draft.json"
        draft.export(out)
        import json
        self.assertFalse(json.loads(out.read_text())["native_plugin_written"])

    def test_loose_model_path_and_proxy_fallback(self):
        from chimster.world_models import resolve_model
        from chimster.world_preview import preview
        data=Path(self.tmp.name)/"Data"
        (data/"Meshes").mkdir(parents=True)
        model=data/"Meshes"/"SIGN.NIF"
        model.write_bytes(b"test")
        self.assertEqual(resolve_model(data,"sign.nif"),model)
        with self.assertRaises(ValueError):
            resolve_model(data,"../outside.nif")
        browser=Browser.open([self.base])
        browser.active[self.static]["model"]="sign.nif"
        from chimster.architecture import box_mesh
        scene, report=preview(browser,self.cell,models=lambda _:box_mesh((0,0,0),(1,1,1),"native"))
        self.assertEqual(report["model_references"],1)
        self.assertEqual(report["proxy_references"],0)
        def bad(_):raise ValueError("unsupported")
        scene,report=preview(browser,self.cell,models=bad)
        self.assertEqual(report["proxy_references"],1)
        self.assertEqual(len(report["issues"]),1)



    def test_native_draft_export_and_source_change(self):
        from chimster.world_draft import Draft
        from chimster.world_draft_native import export_esp
        # Canonical source: top-level STAT group; no malformed legacy fixture hierarchy.
        header=record(b"TES4",0,sub(b"HEDR",struct.pack("<fII",1.34,2,0x804)),flags=1)
        self.base.write_bytes(header+group(0,int.from_bytes(b"STAT","little"),
            record(b"STAT",0x803,edid("RoadSign"))))
        browser=Browser.open([self.base])
        draft=Draft(browser)
        key=draft.create("NewRoom")
        ref=draft.place(key,self.static,(100,200,300),scale=1.5)
        out=Path(self.tmp.name)/draft.name
        source=self.base.read_bytes()
        export_esp(draft,out)
        merged=Browser.open([self.base,out])
        self.assertEqual(merged.active[key]["editor_id"],"NewRoom")
        self.assertEqual(merged.active[ref]["base"],self.static)
        self.assertEqual(merged.active[ref]["scale"],1.5)
        self.assertEqual(self.base.read_bytes(),source)
        out.unlink()
        self.base.write_bytes(source+b"changed")
        with self.assertRaises(ValueError):export_esp(draft,out)
        self.assertFalse(out.exists())



    def test_neighborhood_crosses_negative_cell_boundary(self):
        from chimster.world_preview import Neighborhood
        header=record(b"TES4",0,sub(b"MAST",b"Base.esm\0"))
        neighbor=record(b"CELL",0x01000800,sub(b"XCLC",struct.pack("<ii",-1,3)))
        self.patch.write_bytes(header+group(1,0x800,neighbor))
        browser=Browser.open([self.base,self.patch])
        loader=Neighborhood(browser,self.cell,1)
        self.assertIsNone(loader.move(-8192,13000))
        scene,report=loader.move(-4096,13000)
        self.assertEqual(loader.grid,(-1,3))
        self.assertEqual(report["origin_game_units"],(-4096,12288,0))
        self.assertIsNone(loader.move(100000,100000))
        self.assertIsNone(loader.move(-1,13000))

    def test_oblivion_structural_browser(self):
        def rec(tag,fid,*parts):
            data=b"".join(parts)
            return struct.pack("<4s4I",tag,len(data),0,fid,0)+data
        def grp(kind,owner,*records):
            data=b"".join(records)
            return struct.pack("<4sIIiI",b"GRUP",20+len(data),owner,kind,0)+data
        self.base.write_bytes(rec(b"TES4",0)+grp(0,int.from_bytes(b"WRLD","little"),
            rec(b"WRLD",0x800,edid("World")),grp(1,0x800,
            rec(b"CELL",0x801,sub(b"XCLC",struct.pack("<ii",-1,2))))))
        browser=Browser.open([self.base],"oblivion")
        self.assertEqual(browser.profile,"oblivion")
        self.assertEqual(browser.cell_rows(self.world)[0]["grid"],(-1,2))

    def test_existing_reference_draft_transform(self):
        from chimster.world_draft import Draft
        browser=Browser.open([self.base])
        draft=Draft(browser)
        draft.transform(self.ref,(-7100,13000,10),yaw=.4,scale=1.2)
        self.assertEqual(draft.index().active[self.ref]["position"],(-7100,13000,10))
        self.assertNotEqual(browser.active[self.ref]["position"],(-7100,13000,10))
        draft.undo()
        self.assertEqual(draft.index().active[self.ref]["position"],browser.active[self.ref]["position"])



    def test_duplicate_static_cell_single_undo(self):
        from chimster.world_draft import Draft
        browser=Browser.open([self.base])
        draft=Draft(browser)
        key,report=draft.duplicate(self.cell,"Duplicated",(-1,3))
        self.assertEqual(report["copied"],1)
        children=draft.index().object_rows(key)
        self.assertEqual(len(children),1)
        self.assertEqual(children[0]["position"],(-2904,13000,5))
        self.assertNotEqual(children[0]["key"],self.ref)
        self.assertEqual(children[0]["base"],self.static)
        draft.undo()
        self.assertNotIn(key,draft.index().active)
        draft.redo()
        self.assertEqual(len(draft.index().object_rows(key)),1)
        with self.assertRaises(ValueError):
            draft.duplicate(self.cell,"Another",(-1,3))
        self.assertEqual(len(draft.index().object_rows(key)),1)

    def test_world_properties_draft(self):
        from chimster.world_draft import Draft
        browser=Browser.open([self.base])
        draft=Draft(browser)
        draft.world_properties(self.world,"RenamedWorld","New World Title")
        self.assertEqual(draft.index().worlds[self.world]["name"],"New World Title")
        self.assertEqual(draft.index().worlds[self.world]["editor_id"],"RenamedWorld")
        self.assertEqual(browser.worlds[self.world]["editor_id"],"TestWorld")
        draft.undo()
        self.assertEqual(draft.index().worlds[self.world]["editor_id"],"TestWorld")



if __name__ == "__main__":
    unittest.main()
