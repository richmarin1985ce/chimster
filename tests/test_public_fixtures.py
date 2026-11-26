"""Opt-in tests against the pinned MIT-licensed Ortham fixture repository."""
import os, unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from chimster.core import inspect_plugin
from chimster.loadorder import HeaderCache, scan_profile

ROOT=os.environ.get("CHIMSTER_PUBLIC_FIXTURES")
@unittest.skipUnless(ROOT,"set CHIMSTER_PUBLIC_FIXTURES to pinned Ortham/testing-plugins checkout")
class PublicFixtureTests(unittest.TestCase):
    def test_real_format_headers(self):
        root=Path(ROOT)
        cases=[
            ("morrowind","Morrowind/Data Files/Blank.esm"),
            ("oblivion","Oblivion/Data/Blank.esm"),
            ("fallout3","Skyrim/Data/Blank.esm"),
            ("newvegas","Skyrim/Data/Blank.esm"),
            ("skyrim","Skyrim/Data/Blank.esm"),
            ("skyrimse","SkyrimSE/Data/Blank.esl"),
            ("fallout4","Fallout 4/Data/Blank.esp"),
            ("starfield","Starfield/Data/Blank.full.esm"),
            ("starfield","Starfield/Data/Blank.medium.esm"),
            ("starfield","Starfield/Data/Blank.small.esm"),
        ]
        for game,rel in cases:
            with self.subTest(game=game,path=rel):
                p=root/rel
                result=inspect_plugin(p,game)
                self.assertEqual(result["file"],p.name)
                self.assertEqual(result["bytes"],p.stat().st_size)
                self.assertEqual(result["record_counts"]["TES3" if game=="morrowind" else "TES4"],1)

    def test_master_order_and_cache(self):
        root=Path(ROOT)
        for game,folder in [("morrowind","Morrowind/Data Files"),("oblivion","Oblivion/Data"),("skyrim","Skyrim/Data")]:
            with self.subTest(game=game), TemporaryDirectory() as d:
                base=root/folder
                cache=HeaderCache(Path(d)/"headers.sqlite")
                try:
                    names=["Blank - Master Dependent.esm","Blank.esm"]
                    first=scan_profile(game,[base],names,cache)
                    self.assertEqual(first["proposed_order"],list(reversed(names)))
                    self.assertEqual(first["cache_hits"],0)
                    self.assertEqual(scan_profile(game,[base],names,cache)["cache_hits"],2)
                finally:
                    cache.close()
