"""Mixed LOD terrain tiles with full-resolution shared perimeter samples."""
from .flora import Mesh
from .lod import validate_mesh
def tile(terrain,x,y,step=1):
    terrain.validate()
    if type(step) is not int or step not in (1,2,4,8,16,32):raise ValueError("step must divide 32")
    heights=terrain.cell(x,y);m=Mesh();ids={}
    def vertex(a,b):
        if (a,b) not in ids:
            ids[a,b]=len(m.vertices)
            m.vertices.append(((x*32+a)*terrain.spacing_m,(y*32+b)*terrain.spacing_m,heights[b][a]-terrain.datum_m))
            m.uv.append((a/32,b/32))
        return ids[a,b]
    def face(a,b,c):m.faces.append(((vertex(*a),vertex(*b),vertex(*c)),"terrain"))
    for j in range(0,32,step):
        for i in range(0,32,step):
            a,b=i+step,j+step
            if step==1 or (i>0 and j>0 and a<32 and b<32):
                face((i,j),(a,j),(a,b));face((i,j),(a,b),(i,b));continue
            # Split only exterior edges; interior shared edges retain coarse endpoints.
            ring=[(u,j) for u in (range(i,a) if j==0 else (i,))]
            ring.extend((a,v) for v in (range(j,b) if a==32 else (j,)))
            ring.extend((u,b) for u in (range(a,i,-1) if b==32 else (a,)))
            ring.extend((i,v) for v in (range(b,j,-1) if i==0 else (b,)))
            center=(i+step//2,j+step//2)
            for k,p in enumerate(ring):face(center,p,ring[(k+1)%len(ring)])
    validate_mesh(m)
    return m
def edge(mesh,axis,value):
    return sorted({p for p in mesh.vertices if p[axis]==value})
