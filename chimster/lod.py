"""Original MIT LOD geometry, orthographic baking and tile planning.
Intermediate assets, not Bethesda BTT/BTR/BTO/BTT atlas formats."""
from pathlib import Path
from math import sin,cos,pi,isfinite,floor,ceil
from hashlib import sha256
import json, time
from .flora import Mesh, Recipe, generate, write_obj
from .atlas import Tile, pack, write_png

def validate_mesh(mesh):
    if not mesh.vertices or len(mesh.vertices)!=len(mesh.uv) or not mesh.faces:
        raise ValueError("empty or inconsistent geometry")
    if any(len(v)!=3 or not all(isfinite(x) for x in v) for v in mesh.vertices):
        raise ValueError("invalid vertex")
    if any(len(v)!=2 or not all(isfinite(x) for x in v) for v in mesh.uv):
        raise ValueError("invalid UV")
    for tri,mat in mesh.faces:
        if len(tri)!=3 or len(set(tri))!=3 or any(not isinstance(i,int) or not 0<=i<len(mesh.vertices) for i in tri) or not mat:
            raise ValueError("invalid triangle/material")
    return mesh.stats()

def bounds(mesh):
    return tuple((min(p[i] for p in mesh.vertices),max(p[i] for p in mesh.vertices)) for i in range(3))

def bake(mesh, angle=0, size=128, palette=None, extent=None):
    """Flat-color z-buffer render of actual triangles, transparent background.
    Does not sample alpha textures; use for original prototype foliage only."""
    validate_mesh(mesh)
    if not 16<=size<=512 or not isfinite(angle):raise ValueError("invalid bake size/angle")
    palette=palette or {}
    c,s=cos(angle),sin(angle)
    projected=[(c*x+s*y,z,-s*x+c*y) for x,y,z in mesh.vertices]
    if extent is None:
        lo=min(p[0] for p in projected);hi=max(p[0] for p in projected)
        bottom=min(p[1] for p in projected);top=max(p[1] for p in projected)
    else:lo,hi,bottom,top=extent
    span=max(hi-lo,top-bottom,1e-9)
    center=(lo+hi)/2;mid=(bottom+top)/2;scale=(size-4)/span
    pts=[((x-center)*scale+size/2,(mid-y)*scale+size/2,z) for x,y,z in projected]
    depth=[float("-inf")]*(size*size);pixels=bytearray(size*size*4)
    for tri,mat in mesh.faces:
        color=palette.get(mat,(104,76,49,255) if mat.endswith("__opaque") else (75,121,63,255))
        if len(color)!=4 or any(not isinstance(v,int) or not 0<=v<=255 for v in color):raise ValueError("invalid palette")
        a,b,d=[pts[i] for i in tri]
        den=(b[1]-d[1])*(a[0]-d[0])+(d[0]-b[0])*(a[1]-d[1])
        if abs(den)<1e-9:continue
        for y in range(max(0,floor(min(a[1],b[1],d[1]))),min(size,ceil(max(a[1],b[1],d[1]))+1)):
            for x in range(max(0,floor(min(a[0],b[0],d[0]))),min(size,ceil(max(a[0],b[0],d[0]))+1)):
                px,py=x+.5,y+.5
                u=((b[1]-d[1])*(px-d[0])+(d[0]-b[0])*(py-d[1]))/den
                v=((d[1]-a[1])*(px-d[0])+(a[0]-d[0])*(py-d[1]))/den
                w=1-u-v
                if min(u,v,w)<-1e-8:continue
                z=u*a[2]+v*b[2]+w*d[2];i=y*size+x
                if z>depth[i]:depth[i]=z;pixels[i*4:i*4+4]=bytes(color)
    return bytes(pixels),{"span":span*size/(size-4),"center":center,"mid":mid,"coverage":sum(pixels[i]>0 for i in range(3,len(pixels),4))/(size*size)}

def billboard(mesh,views=2,size=128):
    if views not in (1,2,4):raise ValueError("views must be 1,2 or 4")
    out=Mesh();tiles=[]
    for i in range(views):
        a=pi*i/views
        rgba,info=bake(mesh,a,size)
        mat="view_"+str(i);tiles.append(Tile(mat,size,size,rgba))
        w=info["span"]/2;d=info["center"];z=info["mid"]
        def v(x,h):return (cos(a)*x,sin(a)*x,h)
        out.add([v(d-w,z-w),v(d+w,z-w),v(d+w,z+w),v(d-w,z+w)],[(0,1),(1,1),(1,0),(0,0)],[(0,1,2),(0,2,3)],mat)
    # Orientations are baked into separate tiles, not one texture for every plane.
    return out,tiles

def atlas_billboard(mesh,views=2,size=128):
    proxy,tiles=billboard(mesh,views,size)
    gutter=2; side=1
    while side<ceil(views**.5)*(size+2*gutter):side*=2
    rgba,layout=pack(tiles,side,side,gutter)
    from .atlas import remap_uv
    for face,mat in proxy.faces[::2]:
        # Each independent quad owns four contiguous vertices.
        for i in range(face[0],face[0]+4):proxy.uv[i]=remap_uv(*proxy.uv[i],layout[mat])
    proxy.faces=[(face,"tree_atlas__cutout") for face,_ in proxy.faces]
    return proxy,rgba,side,layout

def terrain_grid(heights,step=1,spacing=1.0,origin=(0,0)):
    """Shared-edge regular heightfield mesh; adjacent tiles must use identical edge samples/step."""
    n=len(heights)
    if n<2 or n>1025 or any(len(row)!=n for row in heights) or any(not isfinite(x) for row in heights for x in row):raise ValueError("invalid square heightfield")
    if not isinstance(step,int) or step<1 or (n-1)%step or not isfinite(spacing) or spacing<=0:raise ValueError("step must divide grid intervals")
    ids=list(range(0,n,step));k=len(ids);v=[];uv=[];tris=[]
    for y in ids:
        for x in ids:
            v.append((origin[0]+x*spacing,origin[1]+y*spacing,heights[y][x]));uv.append((x/(n-1),y/(n-1)))
    for y in range(k-1):
        for x in range(k-1):
            a=y*k+x;tris.extend(((a,a+1,a+k),(a+1,a+k+1,a+k)))
    m=Mesh();m.add(v,uv,tris,"terrain__opaque");return m

def tile_groups(objects,tile_size):
    """Placement grouping only, no geometry merging or game-specific tile coordinate assumption."""
    if not isfinite(tile_size) or tile_size<=0:raise ValueError("invalid tile size")
    result={}
    for o in objects:
        x,y=o["x"],o["y"]
        if not isfinite(x) or not isfinite(y):raise ValueError("invalid position")
        kind=o["kind"]
        if kind not in ("tree","object","terrain"):raise ValueError("invalid LOD class")
        key=(kind,floor(x/tile_size),floor(y/tile_size),o["material_set"])
        result.setdefault(key,[]).append(o["id"])
    return [{"kind":k[0],"tile":[k[1],k[2]],"material_set":k[3],"objects":sorted(v)} for k,v in sorted(result.items())]

def build_key(inputs):
    return sha256(json.dumps(inputs,sort_keys=True,separators=(",",":"),allow_nan=False).encode()).hexdigest()

def dirty_tiles(previous,current):
    return sorted(k for k in set(previous)|set(current) if previous.get(k)!=current.get(k))

def benchmark(count=10,size=64):
    if not 1<=count<=100:raise ValueError("count must be 1..100")
    start=time.perf_counter();counts=[0]*4;coverage=[];hashes=[]
    for seed in range(count):
        r=Recipe(seed=seed)
        for level in range(4):
            m=generate(r,level);validate_mesh(m);counts[level]+=len(m.faces)
        rgba,info=bake(generate(r),size=size);coverage.append(info["coverage"]);hashes.append(sha256(rgba).hexdigest())
    return {"trees":count,"triangles":counts,"coverage_mean":sum(coverage)/count,"unique_bakes":len(set(hashes)),"seconds":time.perf_counter()-start,"scope":"CPU synthetic geometry and flat-color bake, not FPS"}

def build_tree(recipe,output,size=128,views=2):
    out=Path(output);out.mkdir(parents=True,exist_ok=False)
    near=generate(recipe);stats=[]
    for level in range(3):
        m=generate(recipe,level);stats.append(validate_mesh(m));write_obj(m,out/f"tree_lod{level}.obj")
    proxy,rgba,side,layout=atlas_billboard(near,views,size)
    write_obj(proxy,out/"tree_lod3.obj");write_png(out/"tree_atlas.png",side,side,rgba)
    # OBJ V follows bottom-left; this file's baked UVs are top-left, so flip for OBJ readers.
    p=out/"tree_lod3.obj"
    lines=p.read_text(encoding="utf-8").splitlines()
    p.write_text("\n".join(f"vt {line.split()[1]} {1-float(line.split()[2]):.7f}" if line.startswith("vt ") else line for line in lines)+"\n",encoding="utf-8")
    with p.open("a",encoding="utf-8"):pass
    # Attach an MTL so the intermediate billboard can be previewed in OBJ viewers.
    p.write_text("mtllib tree_atlas.mtl\n"+p.read_text(encoding="utf-8"),encoding="utf-8")
    (out/"tree_atlas.mtl").write_text("newmtl tree_atlas__cutout\nKd 1 1 1\nmap_Kd tree_atlas.png\nmap_d tree_atlas.png\n",encoding="utf-8")
    report={"recipe":vars(recipe),"lods":stats+[validate_mesh(proxy)],"atlas_size":side,"atlas_layout":layout,"status":"intermediate OBJ/PNG; flat color bake; no game-native LOD files"}
    (out/"manifest.json").write_text(json.dumps(report,indent=2)+"\n",encoding="utf-8")
    return report
