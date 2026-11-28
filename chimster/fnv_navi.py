"""Read-only FNV NAVI indexing. Unknown NVMI suffix and NVCI stay opaque."""
import struct

def inspect(parts):
    version=None;rows=[];opaque=[];edges=[];seen=set();connections=[];connection_ids=set()
    for i,(tag,raw) in enumerate(parts):
        if tag==b"EDID":
            if not raw or raw[-1:]!=b"\0":raise ValueError("invalid NAVI editor ID")
        elif tag==b"NVER":
            if version is not None or len(raw)!=4:raise ValueError("invalid NAVI version")
            version=struct.unpack("<I",raw)[0]
        elif tag==b"NVMI":
            if len(raw)<16:raise ValueError("truncated NVMI prefix")
            prefix,mesh,location,x,y=struct.unpack_from("<4sIIhh",raw)
            if not mesh or not location or mesh in seen:raise ValueError("invalid or duplicate NAVI entry")
            seen.add(mesh);rows.append({"mesh":mesh,"location":location,"grid":[x,y],"prefix_hex":prefix.hex(),"suffix_bytes":len(raw)-16})
            edges.extend(((i,4,("NAVM",)),(i,8,("CELL","WRLD"))))
            if len(raw)>16:opaque.append(i)
        elif tag==b"NVCI":
            from .fnv_navi_generate import connection
            try:row=connection(raw)
            except ValueError:opaque.append(i);continue
            if row["mesh"] in connection_ids:raise ValueError("duplicate NAVI connection owner")
            connection_ids.add(row["mesh"]);connections.append(row)
            edges.append((i,0,("NAVM",)))
            pos=4
            for key,kinds in (("standard",("NAVM",)),("preferred",("NAVM",)),("doors",("REFR",))):
                pos+=4
                for _ in row[key]:edges.append((i,pos,kinds));pos+=4
        else:opaque.append(i)
    if version is None:raise ValueError("missing NAVI version")
    return {"version":version,"entries":rows,"connections":connections,"opaque":opaque},edges
