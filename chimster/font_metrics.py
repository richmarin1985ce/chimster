"""Font metrics and a restricted, non-destructive outline import adapter."""
from io import BytesIO
from .font_library import read_font
from .font_project import nodes

def validate_metrics(glyphs,advances=None,kerning=None):
    advances={} if advances is None else advances
    kerning={} if kerning is None else kerning
    if not isinstance(advances,dict) or not isinstance(kerning,dict) or len(kerning)>10000:
        raise ValueError("Invalid font metrics")
    allowed=set(glyphs)|{32}
    for cp,width in advances.items():
        if type(cp) is not int or cp not in allowed or type(width) is not int or not 0<=width<=4000:
            raise ValueError("Invalid advance width")
    for pair,value in kerning.items():
        if not isinstance(pair,tuple) or len(pair)!=2 or any(type(cp) is not int or cp not in allowed for cp in pair) or type(value) is not int or not -1000<=value<=1000:
            raise ValueError("Invalid kerning pair")
    return dict(advances),dict(kerning)

def import_outline(source,character,permission=False):
    """Copy one outline into an original 1000-em project; never rewrite source."""
    if not permission:raise ValueError("Confirm permission to modify the font")
    if not isinstance(character,str) or len(character)!=1 or ord(character)<33:
        raise ValueError("Choose one non-space character")
    from fontTools.ttLib import TTFont
    data,info=read_font(source)
    if info["embedding_flags"] is None or info["embedding_flags"] & 2:
        raise ValueError("Embedding rights are restricted or unknown")
    with TTFont(BytesIO(data)) as f:
        if "glyf" not in f or "fvar" in f:
            raise ValueError("Outline import currently supports static TrueType only")
        name=(f.getBestCmap() or {}).get(ord(character))
        if not name:raise ValueError("Character is not present")
        table=f["glyf"]
        coords,ends,flags=table[name].getCoordinates(table)
        if not ends or len(coords)>100000:raise ValueError("Empty or oversized outline")
        scale=1000/f["head"].unitsPerEm
        contours=[];start=0
        for end in ends:
            pts=[(round(coords[i][0]*scale),round(coords[i][1]*scale),bool(flags[i]&1)) for i in range(start,end+1)]
            start=end+1
            if not pts[0][2]:
                if pts[-1][2]:pts=[pts[-1]]+pts[:-1]
                else:
                    a,b=pts[-1],pts[0]
                    pts.insert(0,(round((a[0]+b[0])/2),round((a[1]+b[1])/2),True))
            if sum(p[2] for p in pts)<2:
                expanded=[]
                for i,p in enumerate(pts):
                    expanded.append(p)
                    q=pts[(i+1)%len(pts)]
                    if not p[2] and not q[2]:expanded.append((round((p[0]+q[0])/2),round((p[1]+q[1])/2),True))
                pts=expanded
            contours.append(nodes(pts))
        width=round(f["hmtx"][name][0]*scale)
        validate_metrics({ord(character):contours},{ord(character):width})
        return contours,width
