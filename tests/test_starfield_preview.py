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
