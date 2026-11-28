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
