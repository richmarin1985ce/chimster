import json,unittest,zipfile
from pathlib import Path
from tempfile import TemporaryDirectory
from chimster.tooling import discover_tools
from chimster.sdk import load_manifest
from chimster.modprofiles import install_zip,save_profile

class QuickCoreTests(unittest.TestCase):
    def test_tool_override(self):
        with TemporaryDirectory() as d:
            p=Path(d)/"git";p.touch()
            self.assertEqual(next(x for x in discover_tools({"Git":str(p)}) if x["name"]=="Git")["path"],str(p))
    def test_sdk(self):
        with TemporaryDirectory() as d:
            p=Path(d)/"manifest.json"
            p.write_text(json.dumps({"id":"demo","version":"1","api_version":1,"capabilities":["validator"]}))
            self.assertFalse(load_manifest(p)["execution_enabled"])
    def test_zip(self):
        with TemporaryDirectory() as d:
            root=Path(d);z=root/"mod.zip"
            with zipfile.ZipFile(z,"w") as f:f.writestr("meshes/test.nif",b"sample")
            dest=install_zip(root/"mods",z,"demo")
            self.assertEqual((dest/"meshes/test.nif").read_bytes(),b"sample")
            with self.assertRaises(FileExistsError):install_zip(root/"mods",z,"demo")
    def test_zip_traversal(self):
        with TemporaryDirectory() as d:
            root=Path(d);z=root/"mod.zip"
            with zipfile.ZipFile(z,"w") as f:f.writestr("../escape",b"sample")
            with self.assertRaises(ValueError):install_zip(root/"mods",z,"demo")
            self.assertFalse((root/"escape").exists())
    def test_profile(self):
        with TemporaryDirectory() as d:
            p=save_profile(d,"test","newvegas",["demo"],["Test.esp"])
            self.assertEqual(json.loads(p.read_text())["mods"],["demo"])
