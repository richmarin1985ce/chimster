import json
import subprocess
import sys
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

class DialogueGenerateCLITests(unittest.TestCase):
    def test_generate(self):
        with TemporaryDirectory() as d:
            root=Path(d)
            graph=root/"graph.json"
            ids=root/"ids.json"
            out=root/"02000800.xml"
            graph.write_text(json.dumps({"nodes":[{"id":"a","caption":"Start"}],"edges":[]}))
            ids.write_text(json.dumps({"a":"02000801"}))
            args=[sys.executable,"-m","chimster","dialogue-view-generate",str(graph),str(ids),str(out)]
            result=subprocess.run(args,capture_output=True,text=True)
            self.assertEqual(result.returncode,0,result.stderr)
            self.assertTrue(out.is_file())
            before=out.read_bytes()
            self.assertNotEqual(subprocess.run(args,capture_output=True).returncode,0)
            self.assertEqual(out.read_bytes(),before)
