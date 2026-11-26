import unittest
from chimster.quest_editor import validate,Preview
class QuestTests(unittest.TestCase):
    def project(self):
        return {"schema":1,"id":"Test","start":"A","nodes":[{"id":"A","text":"Start","choices":[{"id":"Get","text":"Get token","target":"B","sets":{"Token":True}}]},{"id":"B","text":"Gate","choices":[{"id":"Pass","text":"Pass","target":"C","requires":{"Token":True}}]},{"id":"C","text":"End"}]}
    def test_preview(self):
        p=self.project();self.assertTrue(validate(p)["valid"])
        s=Preview(p);s.choose("Get");self.assertTrue(s.flags["Token"]);s.choose("Pass");self.assertEqual(s.stage,"C");s.undo();self.assertEqual(s.stage,"B")
    def test_graph(self):
        p=self.project();p["nodes"].append({"id":"D","text":"Unreachable"})
        self.assertEqual(validate(p)["unreachable"],["D"])
        p=self.project();p["nodes"][1]["choices"][0]["target"]="A"
        self.assertFalse(validate(p)["valid"])
