import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from chimster.releases import package
from chimster.localization import TranslationMemory

class ReleaseTests(unittest.TestCase):
    def test_reproducible(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            staging = root / "staging"
            staging.mkdir()
            (staging / "example.esp").write_bytes(b"synthetic")
            package(staging, root / "a.zip")
            package(staging, root / "b.zip")
            self.assertEqual((root / "a.zip").read_bytes(), (root / "b.zip").read_bytes())
    def test_memory(self):
        with TemporaryDirectory() as tmp:
            memory = TranslationMemory(Path(tmp) / "memory.sqlite")
            try:
                memory.remember("en","de","weapon","Bow","Bogen")
                self.assertEqual(memory.lookup("en","de","weapon","Bow"), "Bogen")
                self.assertIsNone(memory.lookup("en","de","gesture","Bow"))
            finally:
                memory.close()
