import tempfile,unittest
from pathlib import Path
from chimster.archive_packaging import package_assets
from chimster.archive_external_validation import compare

class ExternalValidationTests(unittest.TestCase):
    def test_reference(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);ref=root/"reference";ref.mkdir()
            (ref/"meshes").mkdir()
            asset=ref/"meshes"/"a.nif";asset.write_bytes(b"abc")
            archive=root/"Test.ba2"
            package_assets(archive,[("meshes/a.nif",b"abc")])
            self.assertTrue(compare(archive,ref)["reference_match"])
            self.assertFalse(compare(archive,ref,total_limit=2)["reference_match"])
            asset.write_bytes(b"xyz")
            self.assertFalse(compare(archive,ref)["reference_match"])
            asset.unlink()
            self.assertEqual(compare(archive,ref)["extra"],["meshes/a.nif"])
