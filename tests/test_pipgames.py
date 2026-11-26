import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from chimster.pipgames import validate,load,export,preview
class PipGameTests(unittest.TestCase):
    def test_example(self):
        p=load(Path(__file__).resolve().parents[1]/"examples/flagstaff/pipgame.json")
        with TemporaryDirectory() as d:
            target=Path(d)/"game";export(p,target)
            self.assertTrue((target/"play.html").is_file())
            self.assertEqual(load(target/"game.json"),p)
    def test_invalid(self):
        with self.assertRaises(ValueError):validate({"schema":1,"id":"Test","title":"Test","map":["S#E","###","..."]})
    def test_escape(self):
        p={"schema":1,"id":"Test","title":"</script><script>","map":["SCE","...","..."]}
        self.assertNotIn("</script><script>",preview(p))
