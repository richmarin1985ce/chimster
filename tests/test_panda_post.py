import unittest
from chimster.panda_post import ManualTasks

class PostTests(unittest.TestCase):
    def test_task_lifecycle(self):
        import importlib.util
        if not importlib.util.find_spec("panda3d"):self.skipTest("Panda optional")
        t=ManualTasks();calls=[]
        t.add(lambda task:calls.append(task),"test")
        t.step();self.assertEqual(len(calls),1)
        t.remove();t.step();self.assertEqual(len(calls),1)
    def test_dependency_imports(self):
        import importlib.util
        if not importlib.util.find_spec("simplepbr"):self.skipTest("PBR optional")
        import simplepbr,gltf
        self.assertTrue(callable(simplepbr.Pipeline))
        self.assertTrue(callable(gltf.load_model))

    def test_pbr_framebuffer(self):
        import os
        if not os.environ.get("CHIMSTER_TEST_PANDA_GL"):self.skipTest("Optional framebuffer test")
        from panda3d.core import load_prc_file_data
        load_prc_file_data("chimster-test","load-display p3headlessgl\naudio-library-name null")
        from chimster.panda_viewport import Preview
        from chimster.gpu_viewport import make_demo
        from chimster.scene import Camera
        from chimster.render_effects import Effects
        scene,materials=make_demo()
        preview=Preview("pbr")
        try:
            pixels=preview.render(scene,Camera(zoom=4),96,72,materials,effects=Effects())
            self.assertIsNone(preview.post_error)
            self.assertIsNotNone(preview.post)
            self.assertEqual(len(pixels),96*72*4)
            self.assertGreater(len(set(pixels[::4])),3)
            resized=preview.render(scene,Camera(zoom=4),64,48,materials)
            self.assertEqual(len(resized),64*48*4)
            self.assertIsNone(preview.post_error)
        finally:preview.close()

    def test_embedded_glb_validation(self):
        import json,struct,tempfile
        from pathlib import Path
        from chimster.panda_gltf import validate_glb
        with tempfile.TemporaryDirectory() as directory:
            p=Path(directory)/"sample.glb"
            def write(data):
                raw=json.dumps(data).encode();raw+=b" "*(-len(raw)%4)
                p.write_bytes(struct.pack("<4sIIII",b"glTF",2,20+len(raw),len(raw),0x4e4f534a)+raw)
            write({"asset":{"version":"2.0"}})
            self.assertEqual(validate_glb(p),p.resolve())
            write({"asset":{"version":"2.0"},"images":[{"uri":"outside.png"}]})
            with self.assertRaises(ValueError):validate_glb(p)

    def test_tangent_frames(self):
        from chimster.flora import Mesh
        from chimster.gpu_viewport import vertex_data,ImageMap
        from chimster.panda_materials import tangents,normal_pixels
        m=Mesh([(0,0,0),(1,0,0),(0,1,0)],[(0,0),(1,0),(0,1)],[((0,1,2),"m")])
        raw,_=vertex_data(m)
        self.assertEqual(tangents(m,raw),[(1.,0.,0.,1.)]*3)
        image=ImageMap(1,1,bytes((128,220,220,255)))
        self.assertLess(normal_pixels(image,True,1).rgba[1],128)
        self.assertGreater(normal_pixels(image,False,1).rgba[1],128)

    def test_native_filter_fallback(self):
        import os
        if not os.environ.get("CHIMSTER_TEST_PANDA_GL"):self.skipTest("Optional framebuffer test")
        from panda3d.core import load_prc_file_data
        load_prc_file_data("chimster-test","load-display p3headlessgl\naudio-library-name null")
        from chimster.panda_viewport import Preview
        from chimster.gpu_viewport import make_demo
        from chimster.scene import Camera
        from chimster.render_effects import Effects
        scene,materials=make_demo();preview=Preview("filters")
        try:
            pixels=preview.render(scene,Camera(zoom=4),96,72,materials,effects=Effects(ao_strength=.4,scatter_strength=.4))
            self.assertEqual(len(pixels),96*72*4)
            self.assertIsNotNone(preview.post,preview.post_error)
        finally:preview.close()

    def test_glsl_filter_direct(self):
        import os
        if not os.environ.get("CHIMSTER_TEST_PANDA_GL"):self.skipTest("Optional framebuffer test")
        from panda3d.core import load_prc_file_data
        load_prc_file_data("chimster-test","load-display p3headlessgl\naudio-library-name null")
        from chimster.panda_viewport import Preview
        from chimster.gpu_viewport import make_demo
        from chimster.scene import Camera
        from chimster.render_effects import Effects
        from chimster.panda_glsl_filters import GLSLFilters
        scene,materials=make_demo();preview=Preview()
        try:
            cam=Camera(zoom=4);fx=Effects(ao_strength=.7)
            base=preview.render(scene,cam,96,72,materials,effects=fx)
            preview.post=GLSLFilters(preview,fx)
            preview.post.update()
            preview.engine.render_frame();preview.engine.sync_frame()
            self.assertEqual(len(preview.texture.get_ram_image_as("RGBA")),len(base))
        finally:preview.close()

    def test_water_framebuffer(self):
        import os
        if not os.environ.get("CHIMSTER_TEST_PANDA_GL"):self.skipTest("Optional framebuffer test")
        from panda3d.core import load_prc_file_data
        load_prc_file_data("chimster-test","load-display p3headlessgl\naudio-library-name null")
        from chimster.panda_viewport import Preview
        from chimster.gpu_viewport import make_demo
        from chimster.scene import Camera
        from chimster.render_effects import Effects
        scene,materials=make_demo();preview=Preview()
        try:
            fx=Effects(water_level=.3,reflection_size=128,refraction=True)
            cam=Camera(zoom=4,pitch=40)
            raw=preview.render(scene,cam,96,72,materials,effects=fx)
            self.assertEqual(len(raw),96*72*4)
            self.assertIsNone(preview.water_error)
            self.assertIsNotNone(preview.water_targets)
            self.assertEqual(len(preview.water_targets.buffers),2)
            raw2=preview.render(scene,Camera(zoom=4,pitch=-40),96,72,materials,effects=fx)
            self.assertEqual(len(raw2),len(raw))
            self.assertTrue(preview.underwater)
            self.assertIsNone(preview.water_targets)
        finally:preview.close()

    def test_environment_sky(self):
        from chimster.panda_environment import sky_bytes
        raw=sky_bytes(4,(.3,.4,.5),.6)
        self.assertEqual(len(raw),6*4*4*4)
        self.assertGreater(len(set(raw[::4])),1)
        import os
        if not os.environ.get("CHIMSTER_TEST_PANDA_GL"):return
        from chimster.panda_environment import environment
        env=environment((.3,.4,.5),.6)
        self.assertTrue(env.is_prepared.done())
