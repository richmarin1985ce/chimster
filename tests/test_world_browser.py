import struct
import tempfile
import unittest
from pathlib import Path
from chimster.world_browser import Browser
from chimster.record_graph import Identity


def sub(tag, data):
    return struct.pack("<4sH", tag, len(data)) + data


def record(tag, fid, *parts, flags=0):
    data = b"".join(parts)
    return struct.pack("<4s5I", tag, len(data), flags, fid, 0, 0) + data


def group(kind, owner, *records):
    data = b"".join(records)
    return struct.pack("<4sIIiII", b"GRUP", 24+len(data), owner, kind, 0, 0) + data


def edid(name):
    return sub(b"EDID", name.encode("ascii")+b"\0")


class WorldBrowserTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.base = Path(self.tmp.name)/"Base.esm"
        self.patch = Path(self.tmp.name)/"Patch.esp"
        self.world = Identity("base.esm", 0x800)
        self.cell = Identity("base.esm", 0x801)
        self.ref = Identity("base.esm", 0x802)
        self.static = Identity("base.esm", 0x803)
        header = record(b"TES4", 0)
        base = record(b"STAT", 0x803, edid("RoadSign"))
        world = record(b"WRLD", 0x800, edid("TestWorld"))
        cell = record(b"CELL", 0x801, edid("NegativeCell"),
                      sub(b"XCLC", struct.pack("<ii", -2, 3)), sub(b"DATA", b"\0"))
        ref = record(b"REFR", 0x802, sub(b"NAME", struct.pack("<I",0x803)),
                     sub(b"DATA", struct.pack("<6f", -7000, 13000, 5, 0, 0, 1)))
        self.base.write_bytes(header + base + world + group(1,0x800,cell,
             group(6,0x801,group(9,0x801,ref))))

    def test_grid_and_reference_search(self):
        browser = Browser.open([self.base])
        self.assertEqual(browser.cell_rows(self.world)[0]["grid"], (-2,3))
        self.assertEqual(browser.coordinates[self.world,(-2,3)][0]["key"],self.cell)
        row = browser.object_rows(self.cell,"roadsign")[0]
        self.assertEqual(row["key"],self.ref)
        self.assertEqual(row["bucket"],9)
        self.assertEqual(browser.details(row)["base_name"],"RoadSign")

    def test_override_deletion_and_provenance(self):
        header = record(b"TES4",0,sub(b"MAST",b"Base.esm\0"))
        replacement = record(b"CELL",0x801,edid("Renamed"),sub(b"XCLC",struct.pack("<ii",-2,3)))
        deletion = record(b"REFR",0x802,flags=0x20)
        self.patch.write_bytes(header+group(1,0x800,replacement,group(6,0x801,group(9,0x801,deletion))))
        browser = Browser.open([self.base,self.patch])
        self.assertEqual(browser.name(browser.active[self.cell]),"Renamed")
        self.assertEqual(browser.history[self.cell],["base.esm","patch.esp"])
        self.assertEqual(browser.object_rows(self.cell),[])
        self.assertNotIn(self.ref,browser.active)
        with self.assertRaises(ValueError):
            Browser.open([self.patch,self.base])

    def test_interiors_and_conflicting_coordinates(self):
        header = record(b"TES4",0,sub(b"MAST",b"Base.esm\0"))
        duplicate = record(b"CELL",0x01000800,edid("Conflict"),sub(b"XCLC",struct.pack("<ii",-2,3)))
        interior = record(b"CELL",0x01000801,edid("Room"),sub(b"DATA",b"\1"))
        self.patch.write_bytes(header+interior+group(1,0x800,duplicate))
        browser = Browser.open([self.base,self.patch])
        self.assertEqual(len(browser.coordinates[self.world,(-2,3)]),2)
        self.assertTrue(any("Duplicate coordinates" in issue for issue in browser.issues))
        self.assertTrue(browser.cell_rows(None)[0]["interior"])


if __name__ == "__main__":
    unittest.main()
