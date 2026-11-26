import unittest
from chimster.collision_materials import MATERIALS,material_id,exchange,validate
from chimster.architecture import Building,generate
class MaterialTests(unittest.TestCase):
    def test_materials(self):
        self.assertEqual(set(MATERIALS.values()),set(range(128)))
        for name,i in [("stone",0),("wood",9),("sheet_metal",17),("wood_platform",41),("metal_stairs",69),("wood_stairs_platform",105)]:
            self.assertEqual(material_id(name,"newvegas"),i)
        for value in ("unknown",128,-1,True):
            with self.assertRaises(ValueError):material_id(value,"newvegas")
        with self.assertRaises(ValueError):material_id("stone","skyrim")
    def test_building_recipe(self):
        _,boxes=generate(Building())
        s={"kind":"compound_aabb","boxes":boxes,"list_material":"stone"}
        raw,root,ids=exchange(s,"newvegas",10)
        self.assertTrue(raw.startswith("CHIMSTER_COLLISION_1 8 0\n"))
        self.assertEqual(ids,[9,17,0,0,0,0,0,0])
        _,rows=validate(s,"newvegas",10)
        self.assertEqual(rows[0]["max"],(80,60,0))
        self.assertEqual(root,0)
    def test_bad_recipe(self):
        b={"id":"wall","min":[0,0,0],"max":[1,1,1],"material":"metal"}
        for boxes in ([b,b],[{**b,"max":[0,1,1]}],[{**b,"material":128}],[]):
            with self.assertRaises(ValueError):validate({"kind":"compound_aabb","boxes":boxes},"newvegas")
