import unittest
from tempfile import TemporaryDirectory
from pathlib import Path
from chimster.flora import Recipe, generate, batch

class FloraTests(unittest.TestCase):
    def test_seed(self):
        self.assertEqual(generate(Recipe()),generate(Recipe()))
        self.assertNotEqual(generate(Recipe()),generate(Recipe(seed=43)))
    def test_lod(self):
        meshes=[generate(Recipe(),i) for i in range(4)]
        self.assertEqual([len(m.faces) for m in meshes],[980,396,176,4])
        for m in meshes:
            self.assertEqual(len(m.vertices),len(m.uv))
            self.assertTrue(all(0<=i<len(m.vertices) for f,_ in m.faces for i in f))
    def test_variants(self):
        for kind in ("tree","shrub","grass"):
            self.assertGreater(len(generate(Recipe(species=kind)).faces),0)
    def test_batch(self):
        with TemporaryDirectory() as d:
            report=batch([Recipe(),Recipe(seed=99)],Path(d)/"out")
            self.assertEqual(len(report["assets"]),8)
            self.assertEqual(len(report["groups"]["lod0:bark__opaque"]),2)
    def test_invalid(self):
        with self.assertRaises(ValueError):
            generate(Recipe(height=0))
        with self.assertRaises(ValueError):
            generate(Recipe(),4)
