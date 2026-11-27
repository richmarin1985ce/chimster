"""Transactional alpha painting over the current FNV sparse layer representation.
Brush coordinates are terrain sample coordinates, south-to-north, shared at boundaries.
A stroke exceeding the conservative writer budget fails without changing the input."""
from math import hypot,isfinite
from .land_layers import encode_layers
from .land_paint import Paint
def key(s):return (*s["cell"],s["quadrant"])
def index(layers,cells):
    if not isinstance(layers,list):raise ValueError("invalid layer list")
    textures={s["texture"]:i+1 for i,s in enumerate(layers)}
    encode_layers(layers,textures,cells)
    result={}
    for s in sorted(layers,key=lambda s:(*key(s),s["layer"])):
        q=result.setdefault(key(s),[])
        if any(tex==s["texture"] for tex,_ in q):raise ValueError("duplicate quadrant texture")
        q.append((s["texture"],dict(s["vertices"])))
    return result
def flatten(groups):
    result=[]
    for (cx,cy,q),items in sorted(groups.items()):
        for i,(tex,vertices) in enumerate(items):
            result.append({"cell":[cx,cy],"quadrant":q,"layer":i,"texture":tex,"vertices":[[p,a] for p,a in sorted(vertices.items()) if a>0] or [[0,0.]]})
    return result
def stroke(paint,layers,x,y,radius,strength,texture,erase=False):
    cells=len(paint.rows)//2;paint.validate(cells)
    if not 1<=cells<=16 or not all(isfinite(v) for v in (x,y,radius,strength)) or not 0<=x<=cells*32 or not 0<=y<=cells*32 or not 0<radius<=512 or not 0<=strength<=1 or not isinstance(texture,str) or not texture or type(erase) is not bool:raise ValueError("invalid brush")
    groups=index(layers,cells)
    for qy in range(cells*2):
        for qx in range(cells*2):
            ox,oy=qx*16,qy*16
            if x+radius<ox or x-radius>ox+16 or y+radius<oy or y-radius>oy+16:continue
            hits={j*17+i:strength*max(0.,1-hypot(ox+i-x,oy+j-y)/radius)**2 for j in range(17) for i in range(17)}
            hits={p:w for p,w in hits.items() if w>0}
            if not hits:continue
            k=(qx//2,qy//2,(qy%2)*2+qx%2);items=groups.get(k,[])
            old=next((v for t,v in items if t==texture),None)
            if old is None:
                if erase:continue
                if paint.rows[qy][qx]==texture:raise ValueError("selected overlay equals base texture; choose a distinct overlay")
                if len(items)>=4:raise ValueError(f"quadrant {k} exceeds current four-overlay writer limit")
                old={};items.append((texture,old));groups[k]=items
            for p,w in hits.items():
                a=old.get(p,0.)
                old[p]=a*(1-w) if erase else a+(1-a)*w
    return flatten(groups)
def remove_layer(layers,cells,cell,quadrant,texture):
    """Explicit removal of an allocation, including zero-opacity slots."""
    groups=index(layers,cells);k=(*cell,quadrant)
    old=groups.get(k,[]);new=[(t,v) for t,v in old if t!=texture]
    if len(old)==len(new):raise ValueError("texture is not allocated")
    groups[k]=new;return flatten(groups)
def usage(layers,cells):
    groups=index(layers,cells)
    return [{"cell":[x,y],"quadrant":q,"allocated":1+len(items),"writer_remaining":4-len(items),"overlays":[{"texture":t,"mean_vertex_opacity":sum(v.values())/289} for t,v in items]} for (x,y,q),items in sorted(groups.items())]
