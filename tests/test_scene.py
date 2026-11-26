import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from chimster.scene import demo_scene,Scene,Instance,Camera,frame,load_obj
from chimster.flora import write_obj
class SceneTests(unittest.TestCase):
    def test_edit(self):
        s=demo_scene();s.add(Instance("new","tree",1,2,3));s.update("new",x=5)
        self.assertEqual(s.instances[-1].x,5);s.undo();self.assertEqual(s.instances[-1].x,1);s.redo();self.assertEqual(s.instances[-1].x,5)
        with self.assertRaises(ValueError):s.add(Instance("new","tree"))
    def test_save(self):
        s=demo_scene()
        with TemporaryDirectory() as d:
            p=Path(d)/"scene.json";s.save(p);t=Scene.load(p)
            self.assertEqual(s.instances,t.instances);self.assertEqual(s.assets,t.assets)
            p=Path(d)/"tree.obj";write_obj(s.assets["tree"],p)
            self.assertEqual(len(load_obj(p).faces),len(s.assets["tree"].faces))
    def test_view(self):
        s=demo_scene();a=frame(s,Camera(),640,480)
        self.assertGreater(len(a),0);self.assertNotEqual(a,frame(s,Camera(yaw=75),640,480))
        self.assertEqual([r[0] for r in a],sorted(r[0] for r in a))
