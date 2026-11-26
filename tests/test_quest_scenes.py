import unittest
from chimster.quest_scenes import validate,timeline
class ScenesTests(unittest.TestCase):
    def test_scene(self):
        p={"schema":1,"id":"Quest","aliases":[{"id":"Trader","kind":"actor","binding":{"plugin":"Actors.esp","id":2048}}],"scenes":[{"id":"Opening","phases":[{"index":0,"actions":[{"id":"Line","actor":"Trader","kind":"dialogue","start":0,"duration":2,"text":"Welcome"}]},{"index":1,"actions":[{"id":"Pause","actor":"Trader","kind":"wait","start":1,"duration":1}]}]}]}
        self.assertEqual(validate(p)["lines"][0]["id"],"Quest.Opening.0.Line")
        self.assertEqual(timeline(p,"Opening")["duration"],4)
        p["scenes"][0]["phases"][0]["actions"].append({"id":"Overlap","actor":"Trader","kind":"wait","start":1,"duration":1})
        with self.assertRaises(ValueError):validate(p)
