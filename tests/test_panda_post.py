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
