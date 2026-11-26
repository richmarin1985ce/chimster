import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from chimster.ffdec import export_plan, import_plan
class BridgeTests(unittest.TestCase):
    def test_ffdec(self):
        with TemporaryDirectory() as d:
            p=Path(d);e=p/"ffdec-cli.exe";e.touch();s=p/"input.swf";s.touch()
            a=export_plan(e,s,p/"out")
            self.assertIn("-export",a)
            scripts=p/"scripts";scripts.mkdir()
            self.assertIn("-importScript",import_plan(e,s,p/"output.swf",scripts))
            with self.assertRaises(ValueError):import_plan(e,s,s,scripts)
