"""Apply a bounded, explicit list of Asset Forge edits to a private session."""
import json
import math

def apply_edits(session,edits_json):
    edits=json.loads(edits_json)
    if not isinstance(edits,list) or not 1<=len(edits)<=16:
        raise ValueError("expected 1–16 modeling edits")
    def vector(v,n):
        if not isinstance(v,list) or len(v)!=n or any(type(x) not in (int,float) or not math.isfinite(x) or abs(x)>10000 for x in v):
            raise ValueError("invalid vector")
        return v
    def indices(v):
        if not isinstance(v,list) or not 1<=len(v)<=4096 or any(type(x) is not int or not 0<=x<900000 for x in v):
            raise ValueError("invalid selection")
        return v
    def mode(v):
        if v not in ("vertex","edge","face"):raise ValueError("invalid selection mode")
        return v
    for e in edits:
        if not isinstance(e,dict):raise ValueError("invalid edit")
        op=e.get("op")
        fields={"move":{"mode","indices","delta"},"split":{"index"},"delete-faces":{"indices"},
                "assign-faces":{"indices","group"},"extrude":{"indices","delta"},
                "weld":{"indices","tolerance"},"planar-uv":{"indices","plane"},
                "transform-uv":{"mode","indices","scale","offset"}}
        if op not in fields or set(e)!=(fields[op]|{"op"}):raise ValueError("unsupported modeling operation or arguments")
        if op=="move":session.move_selection(mode(e["mode"]),indices(e["indices"]),vector(e["delta"],3))
        elif op=="split":
            if type(e["index"]) is not int:raise ValueError("edge index required")
            session.split_edge(e["index"])
        elif op=="delete-faces":session.delete_faces(indices(e["indices"]))
        elif op=="assign-faces":session.assign_faces(indices(e["indices"]),e["group"])
        elif op=="extrude":session.extrude_faces(indices(e["indices"]),vector(e["delta"],3))
        elif op=="weld":
            v=vector([e["tolerance"]],1)[0]
            if not 0<v<=10:raise ValueError("invalid weld tolerance")
            session.weld_vertices(indices(e["indices"]),v)
        elif op=="planar-uv":session.project_uv(indices(e["indices"]),e["plane"])
        else:session.transform_uv(mode(e["mode"]),indices(e["indices"]),vector(e["scale"],2),vector(e["offset"],2))
    return len(edits)
