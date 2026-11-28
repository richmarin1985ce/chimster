import unittest
from chimster.lod_tools import workflow,openmw_settings

class LodToolTests(unittest.TestCase):
    def test_internal_workflow(self):
        steps=workflow("newvegas")
        self.assertIn("build native terrain NIF/DDS and LODSettings candidates",steps)
        self.assertNotIn("xlodgen"," ".join(steps).casefold())
        self.assertIn("native LOD writer pending",workflow("skyrimse")[-1])
    def test_paging(self):
        self.assertIn("object paging = true",openmw_settings())
        with self.assertRaises(ValueError):openmw_settings(-1)
