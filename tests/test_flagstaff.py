import unittest,json
from tempfile import TemporaryDirectory
from pathlib import Path
from chimster.flagstaff import load_recipe,build,regions_and_placements
class FlagstaffTests(unittest.TestCase):
    def recipe(self):
        r=load_recipe(Path(__file__).resolve().parents[1]/"examples/flagstaff/recipe.json")
        r.update(samples=33,flora_variants=1,billboard_size=32)
        return r
    def test_determinism(self):
        r=self.recipe();g=[[2100+x+y for x in range(33)] for y in range(33)]
        self.assertEqual(regions_and_placements(g,r),regions_and_placements(g,r))
    def test_demo(self):
        r=self.recipe();g=[[2100+x+y for x in range(33)] for y in range(33)]
        with TemporaryDirectory() as d:
            p=Path(d)/"demo";report=build(r,g,{"source":"synthetic fixture only"},p)
            self.assertEqual(report["elevation_m"]["min"],2100)
            self.assertEqual(report["terrain_lods"][0]["triangles"],2048)
            self.assertEqual(json.loads((p/"elevation-meters.json").read_text()),g)
            self.assertTrue((p/"preview.html").is_file())
            self.assertTrue((p/"flora/tree-0/tree_atlas.dds").is_file())
