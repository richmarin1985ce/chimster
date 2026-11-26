import unittest
from chimster.interior_runtime import Triggers,visible
class InteriorRuntimeTests(unittest.TestCase):
    def fixture(self):
        return {"schema":1,"rooms":[{"id":"A","min":[0,0,0],"max":[4,4,3]},{"id":"B","min":[4,0,0],"max":[8,4,3]}],"portals":[{"id":"Door","rooms":["A","B"],"corners":[[4,1,0],[4,2,0],[4,2,2],[4,1,2]]}],"triggers":[{"id":"Arrival","room":"A","min":[1,1,0],"max":[2,2,2],"event":"Arrive"}]}
    def test_triggers(self):
        s=Triggers(self.fixture());self.assertEqual(s.update((0,0,0)),[])
        self.assertEqual(s.update((1.5,1.5,1))[0]["phase"],"enter")
        self.assertEqual(s.update((1.5,1.5,1)),[])
        self.assertEqual(s.update((3,3,1))[0]["phase"],"exit")
    def test_frustum(self):
        p=self.fixture();self.assertEqual(visible(p,"A",[])["visible_candidates"],["A","B"])
        self.assertEqual(visible(p,"A",[(-1,0,0,3)])["culled"],["B"])
