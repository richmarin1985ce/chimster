"""Editable Font Forge projects and quadratic outline geometry."""
import json
import re
import os
import tempfile
from pathlib import Path

MAX_PROJECT_BYTES = 16 * 1024 * 1024

def nodes(contour):
    """Legacy (x,y) is an on-curve point; (x,y,False) is a quadratic control."""
    if not isinstance(contour,(tuple,list)) or not 3 <= len(contour) <= 2048:
        raise ValueError("A contour needs 3–2048 points")
    result=[]
    for point in contour:
        if not isinstance(point,(tuple,list)) or len(point) not in (2,3):
            raise ValueError("Invalid outline point")
        x,y=point[:2]
        on=point[2] if len(point)==3 else True
        if any(type(v) is not int or not -1000<=v<=2000 for v in (x,y)) or type(on) is not bool:
            raise ValueError("Invalid outline point")
        result.append((x,y,on))
    if not result[0][2] or sum(p[2] for p in result)<2:
        raise ValueError("Start on the curve and use at least two on-curve points")
    return result

def segments(contour):
    """Yield start, optional control, endpoint; implied midpoints follow TrueType."""
    pts=nodes(contour)
    start=pts[0][:2]
    controls=[]
    for x,y,on in pts[1:]+pts[:1]:
        end=(x,y)
        if not on:
            controls.append(end)
            continue
        if not controls:
            if start!=end:
                yield start,None,end
        else:
            for i,control in enumerate(controls):
                nxt=controls[i+1] if i+1<len(controls) else None
                stop=((control[0]+nxt[0])/2,(control[1]+nxt[1])/2) if nxt else end
                yield start,control,stop
                start=stop
        start=end
        controls.clear()

def draw_outline(pen,contour):
    pts=nodes(contour)
    pen.moveTo(pts[0][:2])
    controls=[]
    for x,y,on in pts[1:]+pts[:1]:
        if not on:
            controls.append((x,y))
        elif controls:
            pen.qCurveTo(*controls,(x,y))
            controls.clear()
        else:
            pen.lineTo((x,y))
    pen.closePath()

def validate(family,glyphs,allow_empty=False):
    if not isinstance(family,str) or not re.fullmatch(r"[A-Za-z][A-Za-z0-9 ]{0,63}",family):
        raise ValueError("Invalid family")
    if not isinstance(glyphs,dict) or not (0 if allow_empty else 1)<=len(glyphs)<=4096:
        raise ValueError("Invalid glyph count")
    out={}
    for cp,contours in glyphs.items():
        if type(cp) is not int or not 33<=cp<=0x10ffff or 0xd800<=cp<=0xdfff:
            raise ValueError("Invalid codepoint")
        if not isinstance(contours,(tuple,list)) or not 1<=len(contours)<=128:
            raise ValueError("Invalid contour count")
        out[cp]=[nodes(c) for c in contours]
    return out

def save_project(path,family,glyphs,advances=None,kerning=None):
    from .font_metrics import validate_metrics
    glyphs=validate(family,glyphs,True)
    advances,kerning=validate_metrics(glyphs,advances,kerning)
    data=json.dumps({"version":2,"family":family,"glyphs":{str(k):v for k,v in glyphs.items()},"advances":{str(k):v for k,v in advances.items()},"kerning":[[a,b,v] for (a,b),v in sorted(kerning.items())]},ensure_ascii=False).encode("utf-8")
    if len(data)>MAX_PROJECT_BYTES:
        raise ValueError("Project exceeds size limit")
    path=Path(path)
    fd,name=tempfile.mkstemp(dir=path.parent,suffix=".tmp")
    try:
        with os.fdopen(fd,"wb") as stream:
            stream.write(data)
        os.replace(name,path)
    finally:
        Path(name).unlink(missing_ok=True)

def load_project(path,include_metrics=False):
    with Path(path).open("rb") as stream:
        data=stream.read(MAX_PROJECT_BYTES+1)
    if len(data)>MAX_PROJECT_BYTES:
        raise ValueError("Project exceeds size limit")
    obj=json.loads(data)
    if not isinstance(obj,dict) or obj.get("version") not in (1,2) or not isinstance(obj.get("glyphs"),dict):
        raise ValueError("Unsupported font project")
    glyphs={}
    for k,v in obj["glyphs"].items():
        if not re.fullmatch(r"[0-9]{1,7}",k) or str(int(k))!=k:
            raise ValueError("Invalid codepoint key")
        glyphs[int(k)]=v
    family=obj.get("family")
    glyphs=validate(family,glyphs,True)
    from .font_metrics import validate_metrics
    advances={};kerning={}
    if obj["version"]==2:
        raw=obj.get("advances",{});pairs=obj.get("kerning",[])
        if not isinstance(raw,dict) or not isinstance(pairs,list) or len(pairs)>10000:
            raise ValueError("Invalid metrics")
        for k,v in raw.items():
            if not re.fullmatch(r"[0-9]{1,7}",k) or str(int(k))!=k:raise ValueError("Invalid advance key")
            advances[int(k)]=v
        for p in pairs:
            if not isinstance(p,list) or len(p)!=3 or any(type(v) is not int for v in p):raise ValueError("Invalid kerning pair")
            key=tuple(p[:2])
            if key in kerning:raise ValueError("Duplicate kerning pair")
            kerning[key]=p[2]
    advances,kerning=validate_metrics(glyphs,advances,kerning)
    return (family,glyphs,advances,kerning) if include_metrics else (family,glyphs)
