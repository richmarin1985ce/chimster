import unittest,json
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch
from chimster.knowledge import KnowledgeIndex
from chimster.local_ai import validate_plan,propose
class KnowledgeTests(unittest.TestCase):
    def test_search(self):
        with TemporaryDirectory() as d:
            p=Path(d);(p/"notes.md").write_text("Billboard terrain texture atlas")
            idx=KnowledgeIndex(p/"index.sqlite")
            try:
                self.assertEqual(idx.rebuild(p)["documents"],1)
                self.assertEqual(idx.search("texture atlas")[0]["source"],"notes.md")
                self.assertEqual(idx.search("unrelated"),[])
            finally:idx.close()
    def test_model(self):
        proposal={"summary":"Check assets","steps":[{"action":"build_lod","description":"Review the terrain levels."}]}
        with patch("chimster.local_ai.http.client.HTTPConnection") as c:
            response=c.return_value.getresponse.return_value
            response.status=200;response.read.return_value=json.dumps({"message":{"content":json.dumps(proposal)}}).encode()
            result=propose("local-model","newvegas","Make LOD")
            self.assertFalse(result["executed"])
            c.assert_called_once_with("127.0.0.1",11434,timeout=120)
        with self.assertRaises(ValueError):validate_plan({"summary":"bad","steps":[{"action":"shell","description":"run command"}]})
