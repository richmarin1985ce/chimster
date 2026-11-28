"""Read-only visibility metadata; raw fields retained, no inferred native geometry."""
import struct
from .native_parser import parse,subrecords
FIELDS={b"XRMR",b"XLRM",b"XPRM",b"XPOD",b"XPTL",b"XORD",b"XMBR",b"XMBO",b"XMBP",b"XRMK"}
PROFILES={"fallout3","newvegas","skyrim","skyrimse","fallout4"}
def inspect(profile,data):
    if profile not in PROFILES:raise ValueError("Visibility profile not supported")
    result=[]
    def walk(nodes,groups=()):
        for node in nodes:
            if node.signature==b"GRUP":
                walk(node.children,groups+((node.header[8:12].hex(),struct.unpack_from("<i",node.header,12)[0]),))
            elif node.signature==b"REFR":
                fields=list(subrecords(profile,node))
                found=[(k.decode(),v.hex()) for k,v in fields if k in FIELDS]
                if not found:continue
                flags,form=struct.unpack_from("<II",node.header,8)
                result.append({"form_id_raw":form,"flags":flags,"groups":groups,"visibility_fields":found,
                    "transform_fields":[v.hex() for k,v in fields if k==b"DATA"],
                    "base_fields":[v.hex() for k,v in fields if k==b"NAME"],
                    "status":"candidate metadata; geometry and master-relative links not decoded"})
    walk(parse(profile,data))
    return result
