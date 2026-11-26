import unittest
from chimster.quest_states import analyze
class StateTests(unittest.TestCase):
    def project(self):
        return {"schema":1,"id":"Test","start":"A","nodes":[{"id":"A","text":"Start","choices":[{"id":"Go","text":"Go","target":"B","sets":{"Token":True}}]},{"id":"B","text":"Gate","choices":[{"id":"Pass","text":"Pass","target":"C","requires":{"Token":True}}]},{"id":"C","text":"End"}]}
    def test_exact(self):
        p=self.project();self.assertTrue(analyze(p)["valid"])
        p["nodes"][0]["choices"][0]["sets"]={}
        r=analyze(p);self.assertFalse(r["valid"]);self.assertEqual(r["deadlocks"][0]["stage"],"B")
    def test_bounded(self):
        r=analyze(self.project(),1);self.assertFalse(r["complete"]);self.assertIsNone(r["no_exit_count"])
