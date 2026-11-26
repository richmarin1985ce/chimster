import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from chimster.lod_benchmark import summarize,compare
class TraceTests(unittest.TestCase):
    def test_summary(self):
        self.assertEqual(summarize([20]*10)["mean_fps"],50)
        with self.assertRaises(ValueError):summarize([0])
    def test_compare(self):
        with TemporaryDirectory() as d:
            a=Path(d)/"a.csv";b=Path(d)/"b.csv"
            a.write_text("frame_ms\n20\n20\n")
            b.write_text("frame_ms\n10\n10\n")
            self.assertEqual(compare(a,b)["fps_change_pct"],100)
