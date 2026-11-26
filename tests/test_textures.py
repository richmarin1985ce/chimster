import unittest,struct,os
from chimster.textures import normal_map,specular_map,cube_from_panorama,cube_dds,direction,FACES
class TextureTests(unittest.TestCase):
    def test_flat(self):
        self.assertEqual(normal_map(2,2,bytes([127])*4),bytes([128,128,255,255])*4)
    def test_green_flip(self):
        h=bytes([0,0,128,128,255,255]);dx=normal_map(2,3,h);gl=normal_map(2,3,h,convention="opengl")
        self.assertLess(dx[9],128);self.assertGreater(gl[9],128)
        self.assertEqual(dx[9]+gl[9],255)
    def test_mask(self):
        s=specular_map(2,1,bytes([0,255]),0,1)
        self.assertEqual(s,bytes([0,0,0,255,255,255,255,255]))
        n=normal_map(2,1,bytes(2),alpha=s[::4])
        self.assertEqual(n[3::4],bytes([0,255]))
    def test_cube(self):
        f=cube_from_panorama(4,2,bytes([10,20,30,255])*8,2)
        self.assertEqual(tuple(f),FACES)
        self.assertTrue(all(v==bytes([10,20,30,255])*4 for v in f.values()))
        d=cube_dds(2,f);self.assertEqual(len(d),128+6*16)
        self.assertEqual(struct.unpack_from("<II",d,108),(0x1008,0xfe00))
        self.assertEqual(d[128:132],bytes([30,20,10,255]))
    def test_face_orientation(self):
        self.assertEqual(direction("+Y",0,0),(0,1,0))
        self.assertEqual(direction("-Z",0,0),(0,0,-1))
        self.assertEqual(direction("+X",-1,0),direction("+Z",1,0))
    def test_invalid(self):
        with self.assertRaises(ValueError):cube_from_panorama(3,2,bytes(24))
        with self.assertRaises(ValueError):normal_map(1,1,b"\x00",convention="unknown")

    def test_mips(self):
        from chimster.textures import mip_chain,mip_dds
        n=normal_map(5,3,bytes([100])*15)
        levels=mip_chain(5,3,n,normal=True)
        self.assertEqual([(w,h) for w,h,_ in levels],[(5,3),(2,1),(1,1)])
        self.assertEqual(levels[-1][2],bytes([128,128,255,255]))
        d=mip_dds(5,3,n,normal=True)
        self.assertEqual(struct.unpack_from("<I",d,28)[0],3)
        self.assertEqual(len(d),128+4*(15+2+1))

    @unittest.skipUnless(os.environ.get("CHIMSTER_TEST_PILLOW"),"optional image decoder")
    def test_real_files(self):
        from tempfile import TemporaryDirectory
        from pathlib import Path
        from PIL import Image
        from chimster.textures import build_material,build_cube
        with TemporaryDirectory() as d:
            p=Path(d)
            Image.new("L",(8,8),127).save(p/"height.png")
            Image.new("L",(8,8),255).save(p/"mask.png")
            build_material(p/"height.png",p/"mask.png",p/"material",pack_alpha=True)
            with Image.open(p/"material/material_n.dds") as im:
                self.assertEqual(im.size,(8,8))
                self.assertEqual(im.convert("RGBA").getpixel((0,0)),(128,128,255,128))
            Image.new("RGBA",(16,8),(12,34,56,255)).save(p/"panorama.png")
            build_cube(p/"panorama.png",p/"cube",8)
            with Image.open(p/"cube/environment.dds") as im:
                self.assertEqual(im.size,(8,8))
                self.assertEqual(im.convert("RGBA").getpixel((0,0)),(12,34,56,255))
