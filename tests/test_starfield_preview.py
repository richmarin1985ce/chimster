import unittest,struct,tempfile
from pathlib import Path
from chimster.starfield_preview import Catalog,Plugin,light,water,parts
from chimster.record_graph import Identity

def sub(tag,raw):return struct.pack("<4sH",tag,len(raw))+raw
def rec(tag,fid,body,flags=0):return struct.pack("<4sIII IHH",tag,len(body),flags,fid,0,576,0)+body
def group(kind,owner,body):return struct.pack("<4sIIiII",b"GRUP",24+len(body),owner,kind,0,0)+body

class StarfieldPreviewTests(unittest.TestCase):
    def test_streaming_cell_and_light(self):
        with tempfile.TemporaryDirectory() as directory:
            p=Path(directory)/"test.esm"
            header=rec(b"TES4",0,sub(b"HEDR",struct.pack("<fII",.96,5,0x900)))
            dat=bytearray(76)
            struct.pack_into("<f",dat,4,20.)
            dat[8:12]=bytes((255,128,64,0));struct.pack_into("<f",dat,20,60.)
            struct.pack_into("<II",dat,48,5000,2000);dat[56]=1
            base=rec(b"LIGH",0x801,sub(b"DAT2",dat))
            wat=bytearray(165);wat[4:12]=bytes((10,20,30,0,5,10,15,0))
            struct.pack_into("<2f",wat,20,.4,.8);struct.pack_into("<f",wat,64,.5)
            waterrec=rec(b"WATR",0x802,sub(b"DNAM",wat))
            lighting=bytearray(108);lighting[:12]=bytes((64,64,64,0,255,255,255,0,10,20,30,0))
            struct.pack_into("<2f",lighting,12,0.,100.)
            cell=rec(b"CELL",0x800,sub(b"EDID",b"TestInterior\0")+sub(b"DATA",struct.pack("<I",3))+sub(b"XCLL",lighting)+sub(b"XCLW",struct.pack("<f",4.))+sub(b"XCWT",struct.pack("<I",0x802)))
            ref=rec(b"REFR",0x803,sub(b"NAME",struct.pack("<I",0x801))+sub(b"DATA",struct.pack("<6f",1.,2.,3.,0.,0.,0.)))
            p.write_bytes(header+group(0,int.from_bytes(b"LIGH","little"),base)+group(0,int.from_bytes(b"WATR","little"),waterrec)+group(0,int.from_bytes(b"CELL","little"),group(2,0,group(3,0,cell+group(6,0x800,group(9,0x800,ref))))))
            catalog=Catalog([p]);key=Identity("test.esm",0x800)
            self.assertEqual(catalog.choices("testinterior")[0][0],key)
            scene,report=catalog.preview(key)
            self.assertEqual(report["render_preview"]["water_level"],4.)
            self.assertAlmostEqual(report["render_preview"]["effects"]["water_opacity"],.6)
            local=report["render_preview"]["lights"][0]
            self.assertEqual(local["position"],(1.,2.,3.))
            self.assertEqual(local["radius"],20.)
            self.assertTrue(local["shadows"])
            self.assertEqual(local["intensity"],2.)
            self.assertEqual(len(scene.instances),1)
            self.assertEqual(light([(b"DAT2",b"short")]),None)
            self.assertEqual(water([(b"DNAM",b"short")],1),{})
            p.write_bytes(header)
            with self.assertRaises(ValueError):catalog.preview(key)
    def test_reject_master_classes(self):
        with tempfile.TemporaryDirectory() as directory:
            p=Path(directory)/"test.esm"
            for flag in (0x100,0x200,0x400):
                p.write_bytes(rec(b"TES4",0,sub(b"HEDR",struct.pack("<fII",.96,0,0x900)),flag))
                with self.assertRaises(ValueError):Plugin(p)
    def test_compressed_and_extended(self):
        import zlib
        raw=sub(b"XXXX",struct.pack("<I",3))+sub(b"DATA",b"abc")
        self.assertEqual(parts(struct.pack("<I",len(raw))+zlib.compress(raw),0x40000),[(b"DATA",b"abc")])

    def test_static_mesh_and_lod(self):
        from chimster.starfield_mesh import decode
        data=struct.pack("<II3HfII",1,3,0,1,2,2.,0,3)
        data+=struct.pack("<9h",0,0,0,32767,0,0,0,32767,0)
        data+=struct.pack("<I6e",3,0,0,1,0,0,1)
        data+=struct.pack("<5I",0,0,0,0,0)
        data+=struct.pack("<II3H",1,3,0,1,2)
        m,lods,report=decode(data)
        self.assertEqual(m.vertices[1],(2.,0.,0.))
        self.assertEqual(m.uv[2],(0.,0.))
        self.assertEqual(len(lods),1)
        self.assertEqual(report["version"],1)
        with self.assertRaises(ValueError):decode(data[:-1])
        broken=bytearray(data);struct.pack_into("<H",broken,8,99)
        with self.assertRaises(ValueError):decode(broken)

    def test_starfield_ba2_and_lz4(self):
        from chimster.starfield_assets import Sources,lz4_block
        from chimster.archive_reader import read
        import zlib
        self.assertEqual(lz4_block(b"\x32abc\x03\x00",9),b"abcabcabc")
        with self.assertRaises(ValueError):lz4_block(b"\x00\x00\x00",4)
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);p=root/"geometry.ba2";name=b"geometries/test.mesh";raw=b"mesh-fixture"
            packed=zlib.compress(raw)
            p.write_bytes(struct.pack("<4sI4sIQ",b"BTDX",2,b"GNRL",1,68+len(packed))+bytes(8)+struct.pack("<I4sIIQIII",0,b"mesh",0,0,68,len(packed),len(raw),0xBAADF00D)+packed+struct.pack("<H",len(name))+name)
            sources=Sources([p])
            self.assertEqual(sources.read("Geometries/Test.mesh"),raw)
            loose=root/"Data";(loose/"geometries").mkdir(parents=True);(loose/"geometries"/"test.mesh").write_bytes(b"loose")
            self.assertEqual(Sources([p],loose).read(name.decode()),b"loose")
            p=root/"textures.ba2";name=b"textures/test.dds";raw=b"12345678";packed=b"\x80"+raw
            offset=36+48
            p.write_bytes(struct.pack("<4sI4sIQ",b"BTDX",3,b"DX10",1,offset+len(packed))+bytes(12)+struct.pack("<I4sIBBHHHBBH",0,b"dds\0",0,0,1,24,4,4,1,71,0x800)+struct.pack("<QIIHHI",offset,len(packed),len(raw),0,0,0xBAADF00D)+packed+struct.pack("<H",len(name))+name)
            dds=read(p,name.decode())
            self.assertTrue(dds.startswith(b"DDS "))
            self.assertEqual(dds[148:],raw)

    def test_external_nif_graph(self):
        from chimster.starfield_nif import geometry,AutoMeshes
        def sized(s):return struct.pack("<I",len(s))+s
        def av(x):return struct.pack("<IIiI13fi",0xffffffff,0,-1,0,x,0,0,1,0,0,0,1,0,0,0,1,1,-1)
        shape=av(2)+bytes(40)+struct.pack("<3i",-1,-1,-1)+b"\x01"+struct.pack("<3I",3,3,0)+sized(b"test")+bytes(3)
        node=av(3)+struct.pack("<Ii",1,1)
        raw=b"Gamebryo File Format, Version 20.2.0.7\n"+struct.pack("<IBIII",0x14020007,1,12,2,172)+b"\x00"+bytes(4)+bytes(2)
        raw+=struct.pack("<H",2)+sized(b"NiNode")+sized(b"BSGeometry")+struct.pack("<2H2I3I",0,1,len(node),len(shape),0,0,0)+node+shape+struct.pack("<Ii",1,0)
        rows=geometry(raw);self.assertEqual(rows[0][1][0][0],"geometries/test.mesh")
        data=struct.pack("<II3HfII",0,3,0,1,2,2.,0,3)+struct.pack("<9h",0,0,0,32767,0,0,0,32767,0)+struct.pack("<6I",0,0,0,0,0,0)
        class Source:
            def read(self,path):return {"meshes/test.nif":raw,"geometries/test.mesh":data}[path]
        m,lods=AutoMeshes(Source())("test.nif")
        self.assertEqual(m.vertices[0],(5.,0.,0.))
        self.assertEqual(m.vertices[1],(7.,0.,0.))
        self.assertEqual(lods,[])
        with self.assertRaises(ValueError):geometry(raw[:-1])

    def test_material_mapping(self):
        from chimster.starfield_materials import PreviewMaterials,key
        from chimster.gpu_viewport import Material
        import json
        with tempfile.TemporaryDirectory() as directory:
            p=Path(directory)/"mat.json"
            p.write_text(json.dumps({"version":1,"materials":{"example.mat":{"tint":[.2,.3,.4],"roughness":.5,"metallic":.7}}}))
            m=PreviewMaterials(p,None)("materials/example.mat")
            self.assertEqual(m.tint,(.2,.3,.4))
            self.assertEqual(m.gloss,6.)
            self.assertEqual(m.metallic,.7)
            self.assertEqual(key("Example.MAT"),"materials/example.mat")
            with self.assertRaises(ValueError):Material(metallic=2.).validate()

    def test_embedded_mesh_and_bind_pose(self):
        from chimster.starfield_mesh import Reader,decode,decode_stream
        raw=struct.pack("<II3HfII",0,3,0,1,2,2.,0,3)+struct.pack("<9h",0,0,0,32767,0,0,0,32767,0)+struct.pack("<6I",0,0,0,0,0,0)
        r=Reader(raw+struct.pack("<II",0,0)+b"NEXT")
        m,lods,meta=decode_stream(r,embedded=True)
        self.assertEqual(bytes(r.take(4)),b"NEXT")
        self.assertEqual(meta["indices"],3)
        skinned=bytearray(raw)
        struct.pack_into("<I",skinned,18,1)
        struct.pack_into("<I",skinned,len(skinned)-4,3)
        skinned+=struct.pack("<6H",0,65535,0,65535,0,65535)
        with self.assertRaises(ValueError):decode(skinned)
        m,lods,meta=decode(skinned,bind_pose=True)
        self.assertTrue(meta["bind_pose"])
        self.assertEqual(len(m.vertices),3)
        with self.assertRaises(ValueError):decode(raw+struct.pack("<I",1))

    def test_native_json_mat(self):
        from chimster.starfield_materials import native_row
        import json
        def c(name,data,i=0):return {"Type":"BSMaterial::"+name,"Data":data,"Index":i}
        doc={"Version":1,"Objects":[
            {"Components":[c("LayerID",{"ID":"layer"}),c("AlphaSettingsComponent",{"HasOpacity":True,"AlphaTestThreshold":.4})]},
            {"ID":"layer","Components":[c("MaterialID",{"ID":"material"})]},
            {"ID":"material","Components":[c("TextureSetID",{"ID":"tex"}),c("Color",{"Value":{"Data":{"x":.2,"y":.3,"z":.4,"w":1.}}})]},
            {"ID":"tex","Components":[c("MRTextureFile",{"FileName":"test/color.dds"}),c("TextureFile",{"FileName":"test/normal.dds"},1),c("MaterialParamFloat",{"Value":.8})]}]}
        row=native_row(json.dumps(doc).encode())
        self.assertEqual(row["diffuse"],"textures/test/color.dds")
        self.assertEqual(row["normal"],"textures/test/normal.dds")
        self.assertEqual(row["tint"],(.2,.3,.4))
        self.assertEqual(row["cutout"],.4)
        self.assertEqual(row["normal_strength"],.8)
        doc["Objects"].pop()
        with self.assertRaises(ValueError):native_row(json.dumps(doc).encode())

    def test_native_preview_channel_maps(self):
        from chimster.starfield_materials import PreviewMaterials
        from chimster.gpu_viewport import ImageMap
        import json
        with tempfile.TemporaryDirectory() as directory:
            p=Path(directory)/"maps.json"
            p.write_text(json.dumps({"version":1,"materials":{"test.mat":{"diffuse":"textures/d.dds","opacity_map":"textures/a.dds","roughness_map":"textures/r.dds","metallic_map":"textures/m.dds"}}}))
            preview=PreviewMaterials(p,None)
            images={"textures/d.dds":ImageMap(2,1,bytes((10,20,30,255,40,50,60,128))),
                    "textures/a.dds":ImageMap(1,1,bytes((128,128,128,255))),
                    "textures/r.dds":ImageMap(1,1,bytes((64,64,64,255))),
                    "textures/m.dds":ImageMap(1,1,bytes((192,192,192,255)))}
            preview.image=lambda path:images[path]
            result=preview("test.mat")
            self.assertEqual(result.diffuse.rgba,bytes((10,20,30,128,40,50,60,64)))
            self.assertAlmostEqual(result.roughness,64/255)
            self.assertAlmostEqual(result.metallic,192/255)

    def test_planet_catalog_and_terrain(self):
        from chimster.starfield_planets import Planets,globe,terrain,direction_at
        from math import pi
        with tempfile.TemporaryDirectory() as directory:
            p=Path(directory)/"test.esm"
            header=rec(b"TES4",0,sub(b"HEDR",struct.pack("<fII",.96,3,0x900)))
            body=sub(b"EDID",b"TestPlanet\0")+sub(b"CNAM",struct.pack("<ddI",.2,.3,0x802))+sub(b"PPBD",struct.pack("<IfII",0x801,100.,0,0))+sub(b"BDST",b"")+sub(b"ANAM",b"Test planet\0")+sub(b"CNAM",b"\x02")+sub(b"FNAM",struct.pack("<d3fi",0.,5e24,6000.,1.,0))+sub(b"INAM",struct.pack("<I3f",0,.5,.2,.4))+sub(b"BDED",b"")+sub(b"RSCS",struct.pack("<i",42))
            biome=rec(b"BIOM",0x801,sub(b"EDID",b"Rock\0")+sub(b"BMC1",bytes((120,80,60,255))))
            world=rec(b"WRLD",0x802,sub(b"EDID",b"Landing\0"))
            p.write_bytes(header+rec(b"PNDT",0x800,body)+biome+world)
            catalog=Planets([p]);key=Identity("test.esm",0x800)
            self.assertEqual(catalog.planets[key]["radius_km"],6000.)
            self.assertEqual(catalog.sites(key)[0][3],"Landing")
            g,r=globe(catalog,key);self.assertEqual(len(g.instances),6)
            s,r=terrain(catalog,key,0,179.99,8,16)
            self.assertEqual(len(s.instances),9)
            self.assertEqual(len(s.assets),27)
            a=s.assets["planet-tile-0-0"].vertices[16];b=s.assets["planet-tile-1-0"].vertices[0]
            self.assertEqual((a[0]-32,a[1],a[2]),b)
            self.assertEqual(s.assets["planet-tile-0-0"].vertices[0],s.assets["planet-tile-0-0@lod1"].vertices[0])
            self.assertAlmostEqual(sum(x*x for x in direction_at(90,180,1,1,6000)),1.)
            self.assertEqual(r["planet_mode"],"landing")

    def test_planet_heightfield_and_skirts(self):
        from chimster.starfield_planets import Heightfield,terrain
        from types import SimpleNamespace
        key=Identity("test.esm",0x800)
        catalog=SimpleNamespace(planets={key:{"radius_km":6000.,"biomes":[]}},biomes={})
        hf=Heightfield([[0.,100.],[200.,300.]])
        self.assertEqual(hf.sample(.5,.5),150.)
        scene,report=terrain(catalog,key,0,0,9,16,heightfield=hf)
        self.assertEqual(report["height_source"],"imported meters")
        m=scene.assets["planet-tile-1-1"]
        self.assertGreater(len(m.vertices),17**2)
        self.assertAlmostEqual(m.vertices[8*17+8][2],150/report["meters_per_unit"])
        self.assertEqual(scene.instances[4].x,0)
        self.assertEqual(scene.instances[5].x,32)
        with self.assertRaises(ValueError):Heightfield([[float("nan"),0],[0,0]])

    def test_planet_streaming_reuses_overlap(self):
        from chimster.starfield_planets import LandingStream,surface_summary
        from types import SimpleNamespace
        key=Identity("test.esm",0x800)
        catalog=SimpleNamespace(planets={key:{"radius_km":6000.,"biomes":[]}},biomes={})
        stream=LandingStream(catalog,key,0,179.99,8,16)
        a,r=stream.update();self.assertIsNone(stream.update(1,1))
        b,s=stream.update(33,0)
        self.assertEqual(s["origin_game_units"],(32,0,0))
        self.assertIs(a.assets["planet-tile-1-1"],b.assets["planet-tile-1-1"])
        self.assertEqual(len(b.instances),9)
        for i in range(2,6):stream.update(i*32,0)
        self.assertLessEqual(len(stream.cache),54)
        summary=surface_summary({"signature":"SFPT","arrays":[("BNAM",struct.pack("<256I",*[0]*254,3,3))]})
        self.assertEqual(summary[0]["top"],[("00000003",2)])
        self.assertEqual(summary[0]["nonzero"],2)

    def test_planet_solar_and_climate(self):
        from chimster.starfield_planets import solar_preview,decode_climate
        from chimster.record_graph import Slots
        noon,n=solar_preview(0,12,atmosphere=(0,.5,.2,.4))
        midnight,m=solar_preview(0,0,atmosphere=(0,.5,.2,.4))
        self.assertAlmostEqual(noon[2],1.)
        self.assertAlmostEqual(midnight[2],-1.)
        self.assertGreater(n["sun_intensity"],m["sun_intensity"])
        self.assertGreater(n["scatter_strength"],m["scatter_strength"])
        row=decode_climate([(b"WLST",struct.pack("<IiI",0x801,100,0)),(b"TNAM",bytes((1,2,3,4,5)))],Slots("test.esm",[]))
        self.assertEqual(row["weather"][0][0],Identity("test.esm",0x801))
        self.assertEqual(row["timing_raw"],(1,2,3,4,5))

    def test_native_starfield_btd(self):
        from chimster.starfield_btd import BTD
        import zlib
        raw=struct.pack("<16384H",*([32768]*16384))+bytes(32768)
        packed=zlib.compress(raw)
        header=struct.pack("<4sI2f2I4iI",b"BTDB",6,-100.,100.,128,128,0,0,0,0,0)
        data=header+bytes(40)+struct.pack("<64H",*([65535]*64))+bytes(128)+struct.pack("<II",0,len(packed))*4+packed
        b=BTD(data)
        self.assertEqual(b.sample(0,0),32768)
        self.assertEqual(b.sample(0,0,4),65535)
        self.assertEqual(b.sample(0,0,texture=True),0)
        hf=b.heightfield(0,0,res=33,meters_per_height_unit=2)
        self.assertAlmostEqual(hf.rows[0][0],2*(-100+200*32768/65535))
        with self.assertRaises(ValueError):BTD(data[:50])
        with self.assertRaises(ValueError):BTD(data[:-2]).sample(0,0)

    def test_system_preview_and_raw_height_export(self):
        from chimster.starfield_planets import system_preview,system_bodies,Heightfield,export_heightfield
        from types import SimpleNamespace
        k=Identity("test.esm",0x800);m=Identity("test.esm",0x801)
        catalog=SimpleNamespace(planets={k:{"biomes":[],"system_ids":(1,2,3),"orbit_raw":(1.,1.,0.,0.,0.)},m:{"biomes":[],"system_ids":(1,2,4),"kind":3,"orbit_raw":(2.,2.,0.,0.,0.)}},biomes={})
        self.assertEqual(len(system_bodies(catalog,k)),2)
        scene,info=system_preview(catalog,k)
        self.assertEqual(len(scene.instances),5)
        self.assertEqual(info["planet_mode"],"system")
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder)/"test.r32"
            export_heightfield(path,Heightfield([[1.,2.],[3.,4.]]))
            self.assertEqual(struct.unpack("<4f",path.read_bytes()),(1.,2.,3.,4.))
            with self.assertRaises(FileExistsError):export_heightfield(path,Heightfield([[1.,2.],[3.,4.]]))

    def test_portable_height_edit_and_biome_materials(self):
        from chimster.starfield_planets import Heightfield,edit_heightfield,save_heightfield,palette_materials,material_at
        h=Heightfield([[0.]*3 for _ in range(3)])
        edited=edit_heightfield(h,.5,.5,.4,10)
        self.assertEqual(edited.rows[1][1],10)
        self.assertEqual(edited.rows[0][0],0)
        self.assertEqual(h.rows[1][1],0)
        colors={"a":(1.,(0.,0.,0.)),"b":(1.,(1.,1.,1.))}
        mats=palette_materials(colors)
        self.assertEqual(mats["a~b~2"].tint,(.5,.5,.5))
        self.assertIn(material_at((1.,0.,0.),0,colors),mats)
        with tempfile.TemporaryDirectory() as folder:
            dest=Path(folder)/"height.json";save_heightfield(dest,edited)
            self.assertEqual(Heightfield.load(dest).rows,edited.rows)

    def test_btd_native_texture_layers(self):
        from chimster.starfield_btd import BTD,layer_image,apply_layer_preview
        from chimster.starfield_planets import terrain
        from types import SimpleNamespace
        import zlib
        # Two LTEX IDs; slot 4 is first overlay, last slot is base.
        raw=bytes(32768)+struct.pack("<16384H",*([3<<12]*16384))
        packed=zlib.compress(raw)
        header=struct.pack("<4sI2f2I4iI",b"BTDB",6,0.,100.,128,128,0,0,0,0,2)
        sets=bytes((0,0,0,0,2,0,0,1))*4
        data=header+struct.pack("<2I",0x801,0x802)+bytes(8)+sets+bytes(256)+struct.pack("<II",0,len(packed))*4+packed
        b=BTD(data)
        self.assertAlmostEqual(b.layers(0,0)[0x801],3/7)
        self.assertAlmostEqual(b.layers(0,0)[0x802],4/7)
        colors={0x801:(1.,0.,0.),0x802:(0.,0.,1.)}
        image=layer_image(b,0,0,0,0,1,1,size=16,colors=colors)
        self.assertEqual(image.rgba[:4],bytes((109,0,146,255)))
        k=Identity("test.esm",0x800)
        catalog=SimpleNamespace(planets={k:{"radius_km":6000.,"biomes":[]}},biomes={})
        scene,report=terrain(catalog,k,0,0,8,16,heightfield=b.heightfield(0,0,res=33))
        apply_layer_preview(scene,report,b,0,0,colors=colors)
        self.assertEqual(len(report["preview_materials"]),9)
        self.assertEqual(scene.assets["planet-tile-0-0@lod2"].faces[0][1],"btd-layer-planet-tile-0-0")
