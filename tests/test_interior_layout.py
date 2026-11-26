import unittest
from chimster.interior_layout import validate,candidates
class InteriorTests(unittest.TestCase):
    def layout(self):
        return {"schema":1,"rooms":[{"id":"A","min":[0,0,0],"max":[4,4,3]},{"id":"B","min":[4,0,0],"max":[8,4,3]},{"id":"C","min":[20,0,0],"max":[24,4,3]}],"portals":[{"id":"Door","rooms":["A","B"],"corners":[[4,1,0],[4,2,0],[4,2,2],[4,1,2]]}],"triggers":[{"id":"Arrival","room":"A","min":[1,1,0],"max":[2,2,2],"event":"Arrive"}],"nodes":[{"id":"One","room":"A","position":[1,1,1],"links":["Two"]},{"id":"Two","room":"B","position":[5,1,1]}]}
    def test_visibility(self):
        p=self.layout();self.assertTrue(validate(p)["valid"])
        self.assertEqual(candidates(p,"A")["visible_candidates"],["A","B"])
        self.assertEqual(candidates(p,"A",["Door"])["culled_disconnected"],["B","C"])
    def test_bad_portal(self):
        p=self.layout();p["portals"][0]["corners"][0]=[3,1,0]
        self.assertFalse(validate(p)["valid"])
