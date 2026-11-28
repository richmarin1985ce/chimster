"""Read-only recursive master type index; no automatic file modification."""
from .native_parser import parse, subrecords
from .record_graph import Slots
from .loadorder import plugin_name
import struct

def index_masters(profile,directory,roots):
    files={}
    for p in directory.iterdir():
        if p.is_file() and p.suffix.lower() in (".esm",".esp",".esl"):
            name=plugin_name(p.name)
            if name in files:raise ValueError("Ambiguous master filename: "+name)
            files[name]=p
    types={}
    loaded=set()
    active=set()
    issues=[]
    def visit(name):
        name=plugin_name(name)
        if name in active:
            issues.append(("cycle",name));return
        if name in loaded:return
        if name not in files:
            issues.append(("missing-master",name));return
        active.add(name)
        try:
            nodes=parse(profile,files[name].read_bytes())
            if not nodes or nodes[0].signature!=b"TES4":
                raise ValueError("wrong header")
            masters=[raw.rstrip(b"\0").decode("cp1252") for tag,raw in subrecords(profile,nodes[0]) if tag==b"MAST"]
            slots=Slots(name,masters)
            for master in masters:visit(master)
            local={}
            def walk(records):
                for node in records:
                    if node.signature==b"GRUP":walk(node.children)
                    elif node.signature!=b"TES4":
                        key=slots.decode(struct.unpack_from("<I",node.header,12)[0])
                        if key is not None:
                            local[key]=None if struct.unpack_from("<I",node.header,8)[0]&0x20 else node.signature.decode("ascii")
            walk(nodes)
            types.update(local)
            loaded.add(name)
        except (OSError,ValueError,struct.error) as exc:
            issues.append(("unreadable-master",name,str(exc)))
        finally:active.remove(name)
    for name in roots:visit(name)
    return {k:v for k,v in types.items() if v is not None},{"loaded":sorted(loaded),"issues":issues}
