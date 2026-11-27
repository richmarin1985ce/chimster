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
def remap(source,output,mapping,strict=True,positions=None):
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
    if positions is not None:move_nodes(root,positions)
    after=inspect(root)
    if positions is None and ([(n["id"],n["bounds"]) for n in before["nodes"]]!=[(n["id"],n["bounds"]) for n in after["nodes"]] or before["links"]!=after["links"]):raise ValueError("layout changed unexpectedly")
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

def move_nodes(root,positions):
    """Move existing topic/branch nodes by diagram ID, keeping link endpoints attached.
    Interior link points receive interpolated endpoint displacement; CK can reroute.
    Branch containers are not automatically resized."""
    before=inspect(root);known={n["id"]:n for n in before["nodes"]}
    if not isinstance(positions,dict) or not set(positions)<=known.keys():raise ValueError("unknown node position")
    delta={}
    for e in root.findall("./Nodes/Node"):
        id=e.get("Id");b=known[id]["bounds"]
        v=positions.get(id,b[:2])
        if not isinstance(v,(list,tuple)) or len(v)!=2 or any(type(x) not in (int,float) or not math.isfinite(x) or abs(x)>1e7 for x in v):raise ValueError("invalid node position")
        delta[id]=(v[0]-b[0],v[1]-b[1]);e.find("Bounds").text=fmt([*v,*b[2:]])
    for e in root.findall("./Links/Link"):
        a=delta[e.find("Origin").get("Id")];b=delta[e.find("Destination").get("Id")]
        points=e.findall("./Points/Point");n=len(points)
        if n<2:raise ValueError("unsupported link with fewer than two control points")
        new=[]
        for i,p in enumerate(points):
            t=i/(n-1);x,y=vec(p.text,2);v=[x+a[0]*(1-t)+b[0]*t,y+a[1]*(1-t)+b[1]*t]
            p.text=fmt(v);new.append(v)
        lo=[min(v[i] for v in new) for i in (0,1)];hi=[max(v[i] for v in new) for i in (0,1)]
        e.find("Bounds").text=fmt([*lo,hi[0]-lo[0],hi[1]-lo[1]])
    allbounds=[vec(e.findtext("Bounds"),4) for e in root.findall("./Nodes/Node")]
    lo=[min(b[i] for b in allbounds)-30 for i in (0,1)];hi=[max(b[i]+b[i+2] for b in allbounds)+30 for i in (0,1)]
    minimum=root.find("./Properties/MinBounds")
    if minimum is not None:minimum.text=fmt([*lo,hi[0]-lo[0],hi[1]-lo[1]])
    inspect(root)


def generate(output,nodes,edges):
    """Generate observed v12 layout subset from explicit native record identities.
    No runtime dialogue records are created; CK compatibility remains unverified.
    """
    q=Path(output)
    if q.suffix.lower()!=".xml" or not re.fullmatch(r"[0-9A-Fa-f]{8}",q.stem) or not int(q.stem,16):
        raise ValueError("expected nonzero FormID.xml filename")
    if q.exists() or q.is_symlink():raise ValueError("new staging XML required")
    if not isinstance(nodes,list) or not 1<=len(nodes)<=10000 or not isinstance(edges,list) or len(edges)>50000:
        raise ValueError("invalid diagram size")
    root=ET.Element("Diagram",Version="12")
    ns=ET.SubElement(root,"Nodes");ls=ET.SubElement(root,"Links")
    known={};forms=set()
    for i,row in enumerate(nodes):
        key=row["id"];form=row["form_id"];caption=row["caption"]
        if not isinstance(key,str) or not key or key in known:raise ValueError("duplicate or invalid node key")
        if not isinstance(form,str) or not re.fullmatch(r"[0-9A-Fa-f]{8}",form) or not int(form,16) or form.upper() in forms:raise ValueError("invalid or duplicate native identity")
        if not isinstance(caption,str) or len(caption)>4096:raise ValueError("invalid caption")
        forms.add(form.upper())
        kind=row.get("kind","topic")
        if kind not in ("topic","branch"):raise ValueError("unsupported node kind")
        bounds=row.get("bounds",[float(i%5)*240,float(i//5)*120,200,80])
        if not isinstance(bounds,(tuple,list)) or len(bounds)!=4 or any(type(x) not in (int,float) or not math.isfinite(x) or abs(x)>1e7 for x in bounds) or min(bounds[2:])<=0:raise ValueError("invalid bounds")
        e=ET.SubElement(ns,"Node",{"Class":"std:TableNode" if kind=="topic" else "std:ShapeNode","Id":str(i)})
        ET.SubElement(e,"Bounds").text=fmt(bounds)
        ET.SubElement(e,"ToolTip").text=form.upper()+" - "+caption
        ET.SubElement(e,"Caption" if kind=="topic" else "Text").text=caption
        known[key]=(str(i),bounds)
    seen=set()
    for i,pair in enumerate(edges):
        if not isinstance(pair,(tuple,list)) or len(pair)!=2 or any(not isinstance(k,str) or k not in known for k in pair):raise ValueError("unknown link endpoint")
        a,b=pair
        if (a,b) in seen:raise ValueError("duplicate link")
        seen.add((a,b))
        aid,x=known[a];bid,y=known[b]
        start=[x[0]+x[2],x[1]+x[3]/2];end=[y[0],y[1]+y[3]/2]
        e=ET.SubElement(ls,"Link",Id=str(len(nodes)+i))
        ET.SubElement(e,"Bounds").text=fmt([min(start[0],end[0]),min(start[1],end[1]),abs(start[0]-end[0]),abs(start[1]-end[1])])
        ET.SubElement(e,"Origin",Id=aid);ET.SubElement(e,"Destination",Id=bid)
        points=ET.SubElement(e,"Points")
        for p in (start,end):ET.SubElement(points,"Point").text=fmt(p)
    inspect(root)
    raw=ET.tostring(root,encoding="utf-8")
    if len(raw)>16*1024*1024:raise ValueError("diagram exceeds size limit")
    with q.open("xb") as f:f.write(raw)
    try:return inspect(parse(q))
    except Exception:q.unlink();raise


def generate_graph(output,graph,identities):
    """Adapt a portable directed graph to XML using explicit native bindings.
    Graph contract: nodes [{id, caption, kind?}], edges [{source,target}].
    No inferred FormIDs or runtime record creation.
    """
    if not isinstance(graph,dict) or not isinstance(identities,dict):
        raise ValueError("expected graph and native identity mapping")
    nodes=graph.get("nodes");edges=graph.get("edges")
    if not isinstance(nodes,list) or not isinstance(edges,list):
        raise ValueError("expected graph nodes and edges")
    keys=set()
    rows=[]
    for node in nodes:
        if not isinstance(node,dict) or not isinstance(node.get("id"),str):
            raise ValueError("invalid graph node")
        key=node["id"]
        if key in keys or key not in identities:raise ValueError("duplicate or unbound graph node")
        keys.add(key)
        rows.append({**node,"form_id":identities[key]})
    if keys!=set(identities):raise ValueError("unused native identity binding")
    links=[]
    for edge in edges:
        if not isinstance(edge,dict) or "source" not in edge or "target" not in edge:
            raise ValueError("invalid graph edge")
        links.append((edge["source"],edge["target"]))
    return generate(output,rows,links)
