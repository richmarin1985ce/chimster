import unittest,os
from chimster.gpu_viewport import Settings,basis,visible,lod_index,make_demo,Renderer,Material,ImageMap,vertex_data
from chimster.scene import Camera,Scene,Instance
from chimster.flora import Mesh
class ViewportTests(unittest.TestCase):
    def test_math(self):
        s=Settings();v=basis(Camera(yaw=0,pitch=0,zoom=10),100,100,s)
        self.assertTrue(visible((0,0,0),1,v,s))
        self.assertFalse(visible((10000,0,0),1,v,s))
        self.assertEqual([lod_index(x,s.lod_distances) for x in (0,22,45,90)],[0,1,2,3])
        with self.assertRaises(ValueError):Settings(lod_distances=(10,5,20)).validate()
    def test_demo(self):
        s,m=make_demo()
        self.assertEqual([len(s.assets[k].faces) for k in ("tree","tree@lod1","tree@lod2","tree@lod3")],[980,396,176,4])
        self.assertTrue(m["leaves__cutout"].cutout)
        data,groups=vertex_data(s.assets["tree"])
        self.assertEqual(len(data),8*len(s.assets["tree"].vertices))
    @unittest.skipUnless(os.environ.get("CHIMSTER_TEST_GL"),"optional GL context")
    def test_depth_pick_and_cutout(self):
        m=Mesh([(-2,0,-2),(2,0,-2),(2,0,2),(-2,0,2)],[(0,0),(1,0),(1,1),(0,1)],[((0,1,2),"front"),((0,2,3),"front")])
        n=Mesh(m.vertices[:],m.uv[:],[(t,"back") for t,_ in m.faces])
        scene=Scene({"a":m,"b":n},[Instance("near","a",y=2),Instance("far","b",y=0),Instance("outside","a",x=10000)])
        renderer=Renderer(backend="egl")
        try:
            cam=Camera(yaw=0,pitch=0,zoom=16)
            opaque={"front":Material(tint=(1,0,0)),"back":Material(tint=(0,1,0))}
            raw,stats=renderer.render(scene,cam,128,128,opaque)
            self.assertEqual(renderer.pick(64,64),"near")
            self.assertIsNone(renderer.pick(0,0))
            self.assertEqual(stats["culled"],1)
            self.assertEqual(stats["triangles"],4)
            opaque["front"]=Material(ImageMap(1,1,b"\xff\xff\xff\x00"),cutout=.5)
            raw2,_=renderer.render(scene,cam,128,128,opaque)
            self.assertEqual(renderer.pick(64,64),"far")
            self.assertNotEqual(raw,raw2)
        finally:renderer.close()
    @unittest.skipUnless(os.environ.get("CHIMSTER_TEST_GL"),"optional GL context")
    def test_lod_and_normal(self):
        s,m=make_demo();r=Renderer(backend="egl")
        try:
            cam=Camera(zoom=4)
            a,near=r.render(s,cam,192,128,m,Settings(lod_distances=(500,1000,1500)))
            b,far=r.render(s,cam,192,128,m,Settings(lod_distances=(1,2,3)))
            self.assertLess(far["triangles"],near["triangles"])
            self.assertGreater(far["lod_counts"][3],0)
            self.assertNotEqual(a,b)
            from dataclasses import replace
            m["bark__opaque"]=replace(m["bark__opaque"],normal_strength=0)
            c,_=r.render(s,cam,192,128,m,Settings(lod_distances=(500,1000,1500)))
            self.assertNotEqual(a,c)
        finally:r.close()

    @unittest.skipUnless(os.environ.get("CHIMSTER_TEST_GL"),"optional GL context")
    def test_instancing_preserves_pixels_and_picking(self):
        from dataclasses import replace
        m=Mesh([(-1,0,-1),(1,0,-1),(1,0,1),(-1,0,1)],[(0,0),(1,0),(1,1),(0,1)],[((0,1,2),"quad"),((0,2,3),"quad")])
        scene=Scene({"quad":m},[Instance("left","quad",x=-2),Instance("right","quad",x=2),Instance("offscreen","quad",x=10000)])
        r=Renderer(backend="egl")
        try:
            cam=Camera(yaw=0,pitch=0,zoom=16)
            settings=Settings()
            a,base=r.render(scene,cam,128,128,settings=replace(settings,instancing=False,hierarchy=False),selected="left")
            b,fast=r.render(scene,cam,128,128,settings=settings,selected="left")
            self.assertEqual(a,b)
            self.assertEqual(base["triangles"],fast["triangles"])
            self.assertEqual(base["draw_calls"],2)
            self.assertEqual(fast["draw_calls"],1)
            self.assertEqual(r.pick(32,64),"left")
            self.assertEqual(r.pick(96,64),"right")
            scene.update("right",x=10000)
            _,changed=r.render(scene,cam,128,128,settings=settings)
            self.assertEqual(changed["visible"],1)
            self.assertIsNone(r.pick(96,64))
        finally:r.close()
