import unittest,os
from pathlib import Path
from tempfile import TemporaryDirectory
from chimster.dependencies import pin,report
class DependencyTests(unittest.TestCase):
    def test_pin(self):
        with TemporaryDirectory() as d:
            p=Path(d)/"tool";p.write_text("fixture");p.chmod(0o755);q=Path(d)/"dependencies.json"
            pin(q,"NIF bridge",p)
            self.assertTrue(report(q)["capabilities"]["native_mesh"]["ready"])
            p.write_text("changed")
            self.assertFalse(report(q)["capabilities"]["native_mesh"]["ready"])
