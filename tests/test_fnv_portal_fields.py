import struct,unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from chimster.fnv_portal_fields import inspect,rewrite
from chimster.fnv_interior import export
from chimster.fnv_patch import sub,record
from chimster.fnv_content import static
from chimster.fnv_world import group
from chimster.fnv_records import scan
from chimster.master_remap import reorder
from chimster.world_validator import validate
from chimster.record_graph import Slots
from chimster.native_world import world_records

class NativePortalTests(unittest.TestCase):
    def test_multi_offset_codec(self):
        parts=[(b"XPOD",struct.pack("<2I",0x800,0x801)),
               (b"XPTL",struct.pack("<9f",2,3,4,2,1,0,0,0,1))]
        info,edges=inspect(parts)
        self.assertEqual(info["portal_rooms"],(0x800,0x801))
        self.assertEqual([offset for _,offset,_ in edges],[0,4])
        result,count=rewrite(parts,lambda v,k:v|0x1000000)
        self.assertEqual(count,2)
        self.assertEqual(result[1],parts[1])
        self.assertEqual(inspect(result)[0]["portal_rooms"],(0x1000800,0x1000801))
        with self.assertRaises(ValueError):inspect([(b"XPOD",bytes(8)),parts[1]])
        with self.assertRaises(ValueError):inspect([(b"XRMR",struct.pack("<H2s",1,b"xy"))])
        with self.assertRaises(ValueError):inspect([(b"XPTL",bytes(36))])

    def test_native_marker_fixture(self):
        # Synthetic marker bases are not distributed retail assets.
        with TemporaryDirectory() as d:
            root=Path(d);base=root/"Markers.esp"
            records=b"".join(static(0x800+i,{"id":name,"bounds":[-1,-1,-1,1,1,1],
                            "model":"meshes/synthetic.nif"}) for i,name in enumerate(("RoomMarker","PortalMarker")))
            base.write_bytes(record(b"TES4",sub(b"HEDR",struct.pack("<fII",1.34,3,0x802))+
                                  sub(b"CNAM",b"Test\0"))+group(0,b"STAT",records))
            layout={"schema":1,"rooms":[{"id":"A","min":[0,0,0],"max":[4,4,4]},
                                        {"id":"B","min":[4,0,0],"max":[8,4,4]}],
                    "portals":[{"id":"P","rooms":["A","B"],"corners":[[4,1,0],[4,3,0],[4,3,3],[4,1,3]]}]}
            def primitive(kind):return struct.pack("<6f4sI",2,2,2,1,0,0,b"test",kind).hex()
            rooms=[{"kind":"room","id":name,"base":{"plugin":base.name,"id":0x800},
                    "position":[x,2,2],"rotation":[0,0,0],"primitive_hex":primitive(1),
                    "header_tail_hex":"1234","linked_rooms":[other]} for name,x,other in (("A",2,"B"),("B",6,"A"))]
            portal={"kind":"portal","id":"P","base":{"plugin":base.name,"id":0x801},
                    "position":[4,2,1.5],"rotation":[0,0,0],"primitive_hex":primitive(3),
                    "collision_layer":18,"rooms":["A","B"],
                    "geometry_hex":struct.pack("<9f",2,3,4,2,1.5,0,0,0,1).hex()}
            spec={"schema":1,"cells":[{"id":"Interior","title":"Interior","layout":layout,
                                      "native_markers":rooms+[portal]}]}
            path=root/"Interior.esp";out=export(spec,path,[base])
            self.assertEqual(len(out["native_marker_bindings"]),3)
            report=validate([base,path])
            self.assertTrue(report["valid"],report["issues"])
            self.assertEqual((report["room_markers"],report["portal_markers"]),(2,1))
            extra=root/"Extra.esp"
            extra.write_bytes(record(b"TES4",sub(b"HEDR",struct.pack("<fII",1.34,0,0x800))+sub(b"CNAM",b"Test\0")))
            folder=root/"stage";folder.mkdir();dest=folder/path.name
            reorder(path,dest,[extra,base],allow_set_change=True)
            def rows(p):
                slots=Slots(p.name,scan(p)["masters"])
                return [(r["key"],r["edges"]) for r in world_records("new-vegas",p.read_bytes(),slots)]
            self.assertEqual(rows(path),rows(dest))
            self.assertEqual(validate([extra,base,dest])["portal_markers"],1)
            portal["rooms"]=["A","A"]
            with self.assertRaisesRegex(ValueError,"endpoints"):
                export(spec,root/"Bad.esp",[base])
