"""Creation Kit DialogueViews XML v12: preserve diagram resources and native link IDs.

Only edit observed fields, and never confuse diagram node IDs with plugin FormIDs.
No DTD/entities, no network resolution, no implicit master-slot guesses.
"""
from pathlib import Path
import xml.etree.ElementTree as ET
import re,math
HEX=re.compile(r"^([0-9A-Fa-f]{8})(?=\s|$)")
def vec(raw,n):
    try:v=[float(x.strip()) for x in raw.split(",")]
    except (ValueError,AttributeError) as e:raise ValueError("invalid diagram coordinates") from e
    if len(v)!=n or any(not math.isfinite(x) or abs(x)>1e7 for x in v):raise ValueError("invalid diagram coordinates")
    return v
def fmt(v):return ", ".join(f"{x:.6f}" for x in v)
def parse(path):
    p=Path(path)
    if p.stat().st_size>16*1024*1024:raise ValueError("diagram exceeds size limit")
    raw=p.read_bytes()
    if b"\0" in raw:raise ValueError("expected UTF-8 XML")
    if re.search(br"<!\s*(DOCTYPE|ENTITY)",raw,re.I):raise ValueError("DTD/entities forbidden")
    try:root=ET.fromstring(raw,parser=ET.XMLParser(target=ET.TreeBuilder(insert_comments=True,insert_pis=True)))
    except ET.ParseError as e:raise ValueError("invalid diagram XML") from e
    if root.tag!="Diagram" or root.get("Version")!="12":raise ValueError("unsupported dialogue diagram version")
    return root
def inspect(root):
    nodes={};links=[];forms=set();linkids=set()
    for e in root.findall("./Nodes/Node"):
        id=e.get("Id")
        if id is None or id in nodes:raise ValueError("invalid or duplicate diagram node ID")
        kind=e.get("Class");bounds=vec(e.findtext("Bounds"),4)
        if bounds[2]<=0 or bounds[3]<=0:raise ValueError("invalid node size")
        tooltip=e.findtext("ToolTip","");m=HEX.match(tooltip)
        form=m.group(1).upper() if m else None
        if form and kind in {"std:ShapeNode","std:TableNode"}:
            if form in forms:raise ValueError("ambiguous duplicate record tooltip")
            forms.add(form)
        nodes[id]={"id":id,"class":kind,"form_id":form,"bounds":bounds,"caption":e.findtext("Caption",e.findtext("Text",""))}
    if not nodes:raise ValueError("empty dialogue diagram")
    for e in root.findall("./Links/Link"):
        id=e.get("Id");a=e.find("Origin");b=e.find("Destination")
        if id is None or id in linkids or id in nodes or a is None or b is None or a.get("Id") not in nodes or b.get("Id") not in nodes:raise ValueError("invalid diagram link")
        linkids.add(id)
        points=[vec(p.text,2) for p in e.findall("./Points/Point")]
        links.append({"id":id,"origin":a.get("Id"),"destination":b.get("Id"),"points":points})
    return {"version":12,"nodes":list(nodes.values()),"links":links,"record_form_ids":sorted(forms),"scope":"editor layout metadata; not dialogue runtime records"}
def remap(source,output,mapping,strict=True):
    """Exact eight-digit FormID mapping in record tooltips and the view filename.
    Preserve node IDs, bounds, links, resources and all unrecognized XML fields."""
    p=Path(source);q=Path(output);root=parse(p);before=inspect(root)
    if not re.fullmatch(r"[0-9A-Fa-f]{8}",p.stem):raise ValueError("expected FormID.xml source filename")
    def normalize(v):
        if not isinstance(v,str) or re.fullmatch(r"[0-9A-Fa-f]{8}",v) is None or int(v,16)==0:raise ValueError("expected nonzero eight-digit FormID")
        return v.upper()
    if not isinstance(mapping,dict):raise ValueError("invalid mapping")
    m={normalize(a):normalize(b) for a,b in mapping.items()}
    if len(m)!=len(mapping) or len(set(m.values()))!=len(m):raise ValueError("ambiguous FormID mapping")
    required=set(before["record_form_ids"])|{p.stem.upper()}
    if strict and not required<=m.keys():raise ValueError("incomplete explicit FormID mapping")
    if q.stem.upper()!=m.get(p.stem.upper(),p.stem.upper()) or q.suffix.lower()!=".xml":raise ValueError("output filename must match mapped view FormID")
    if q.exists() or q.is_symlink() or q.resolve()==p.resolve():raise ValueError("new staging XML required")
    for e in root.findall("./Nodes/Node"):
        if e.get("Class") not in {"std:ShapeNode","std:TableNode"}:continue
        t=e.find("ToolTip")
        if t is not None and t.text:
            hit=HEX.match(t.text)
            if hit:t.text=m.get(hit.group(1).upper(),hit.group(1))+t.text[8:]
    after=inspect(root)
    if [(n["id"],n["bounds"]) for n in before["nodes"]]!=[(n["id"],n["bounds"]) for n in after["nodes"]] or before["links"]!=after["links"]:raise ValueError("layout changed unexpectedly")
    with q.open("xb") as f:ET.ElementTree(root).write(f,encoding="utf-8",xml_declaration=False)
    try:inspect(parse(q))
    except Exception:q.unlink();raise
    return {"output":str(q),"view_form_id":q.stem.upper(),"mapped":sorted(required&m.keys()),"nodes":len(after["nodes"]),"links":len(after["links"]),"scope":"observed v12 XML fields only; verify in Creation Kit"}
def slot_mapping(path,old,new):
    """Explicit old/new file slot for a full plugin; ESL compact IDs not supported."""
    if type(old) is not int or type(new) is not int or not 0<=old<=253 or not 0<=new<=253:raise ValueError("full-plugin slots only")
    p=Path(path);report=inspect(parse(p));ids=set(report["record_form_ids"])|{p.stem.upper()}
    if any(not re.fullmatch(r"[0-9A-F]{8}",v) or int(v[:2],16)>=254 for v in ids):raise ValueError("unsupported light or temporary ID")
    return {v:f"{new:02X}"+v[2:] if int(v[:2],16)==old else v for v in ids}
