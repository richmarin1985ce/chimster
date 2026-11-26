import unittest,json,os
from pathlib import Path
from tempfile import TemporaryDirectory
from chimster.extension_runtime import approve,invoke
class ExtensionTests(unittest.TestCase):
    def test_approval(self):
        with TemporaryDirectory() as d:
            p=Path(d);m=p/"manifest.json";e=p/"tool";q=p/"trust.json"
            m.write_text(json.dumps({"api_version":1,"id":"test","version":"1","capabilities":["validator"]}))
            e.write_text("fixture");e.chmod(0o755)
            approve(m,e,q)
            with self.assertRaises(ValueError):invoke(q,"validator",{})
            with self.assertRaises(ValueError):invoke(q,"record-writer",{},execute=True)
            e.write_text("changed")
            with self.assertRaises(ValueError):invoke(q,"validator",{},execute=True)
    @unittest.skipIf(os.name=="nt","POSIX executable fixture")
    def test_protocol(self):
        import sys
        with TemporaryDirectory() as d:
            p=Path(d);m=p/"manifest.json";e=p/"tool";q=p/"trust.json"
            m.write_text(json.dumps({"api_version":1,"id":"test","version":"1","capabilities":["validator"]}))
            e.write_text("#!"+sys.executable+"\nimport sys,json\nr=json.load(open(sys.argv[1]))\njson.dump({'api_version':1,'ok':True,'result':r['payload']},open(sys.argv[2],'w'))\n");e.chmod(0o755)
            approve(m,e,q);self.assertEqual(invoke(q,"validator",{"a":1},execute=True)["result"],{"a":1})
