"""MIT procedural mesh prototype; game-neutral, Z-up, units unspecified."""
from dataclasses import dataclass, field
from math import sin, cos, pi, sqrt, isfinite
from random import Random
from pathlib import Path
import json

@dataclass(frozen=True)
class Recipe:
    species: str = 'tree'
    seed: int = 42
    height: float = 8.0
    radius: float = .22
    branches: int = 24
    leaves: int = 240
    bark: str = 'bark'
    foliage: str = 'leaves'
    def validate(self):
        if self.species not in ('tree','shrub','grass'): raise ValueError('unknown species')
        if not (isfinite(self.height) and isfinite(self.radius) and 0 < self.height <= 10000 and 0 < self.radius <= self.height): raise ValueError('invalid dimensions')
        if not (0 <= self.branches <= 200 and 0 <= self.leaves <= 10000): raise ValueError('invalid geometry budget')
        if any(not s or not s.isascii() or not all(c.isalnum() or c in '_-' for c in s) for s in (self.bark,self.foliage)): raise ValueError('invalid material ID')

@dataclass
class Mesh:
    vertices: list = field(default_factory=list)
    uv: list = field(default_factory=list)
    faces: list = field(default_factory=list)
    colors: list = field(default_factory=list)  # optional normalized RGBA vertex channel
    def add(self, verts, uv, triangles, material):
        base=len(self.vertices); self.vertices.extend(verts); self.uv.extend(uv)
        if self.colors:self.colors.extend([(1.,1.,1.,1.)]*(len(self.vertices)-base))
        self.faces.extend((tuple(base+i for i in f), material) for f in triangles)
    def stats(self):
        return {'vertices':len(self.vertices),'triangles':len(self.faces),'material_groups':len({m for _,m in self.faces})}

def unit(v):
    n=sqrt(sum(x*x for x in v)); return tuple(x/n for x in v)
def cross(a,b): return (a[1]*b[2]-a[2]*b[1],a[2]*b[0]-a[0]*b[2],a[0]*b[1]-a[1]*b[0])

def tube(mesh,a,b,r0,r1,sides,material):
    axis=unit(tuple(b[i]-a[i] for i in range(3))); ref=(1,0,0) if abs(axis[0])<.9 else (0,1,0)
    u=unit(cross(axis,ref)); v=cross(axis,u); verts=[]; uv=[]
    for j,(p,r) in enumerate(((a,r0),(b,r1))):
        for i in range(sides+1):
            angle=2*pi*i/sides; verts.append(tuple(p[k]+r*(cos(angle)*u[k]+sin(angle)*v[k]) for k in range(3))); uv.append((i/sides,j))
    s=sides+1; faces=[]
    for i in range(sides): faces.extend(((i,i+1,s+i),(i+1,s+i+1,s+i)))
    mesh.add(verts,uv,faces,material)

def card(mesh,p,w,h,angle,material):
    x,y,z=p; dx,dy=cos(angle)*w/2,sin(angle)*w/2
    mesh.add([(x-dx,y-dy,z-h/2),(x+dx,y+dy,z-h/2),(x+dx,y+dy,z+h/2),(x-dx,y-dy,z+h/2)],[(0,0),(1,0),(1,1),(0,1)],[(0,1,2),(0,2,3)],material)

def generate(recipe,level=0):
    recipe.validate()
    if level not in range(4): raise ValueError('LOD must be 0..3')
    m=Mesh(); rng=Random(recipe.seed); h=recipe.height; r=recipe.radius
    bark=recipe.bark+'__opaque'; leaf=recipe.foliage+'__cutout'; sides=(10,6,4,3)[level]
    if level==3:
        for angle in (0,pi/2): card(m,(0,0,h/2),h*.75,h,angle,recipe.foliage+'__billboard_proxy')
        return m
    if recipe.species=='tree': tube(m,(0,0,0),(0,0,h),r,r*.08,sides,bark)
    tips=[]; stride=(1,2,4)[level]
    for i in range(recipe.branches):
        a=rng.uniform(0,2*pi); z=rng.uniform(.28,.85)*h if recipe.species=='tree' else 0
        spread=rng.uniform(.12,.35)*h; end=(cos(a)*spread,sin(a)*spread,min(h,z+rng.uniform(.08,.23)*h) if recipe.species=='tree' else rng.uniform(.45,.95)*h)
        tips.append(end)
        if i%stride==0 and recipe.species!='grass': tube(m,(0,0,z),end,r*.32,r*.035,sides,bark)
    for i in range(recipe.leaves):
        if tips:
            t=tips[i%len(tips)]; p=(t[0]+rng.uniform(-.1,.1)*h,t[1]+rng.uniform(-.1,.1)*h,max(.04*h,min(h,t[2]+rng.uniform(-.08,.08)*h)))
        else: p=(rng.uniform(-.25,.25)*h,rng.uniform(-.25,.25)*h,rng.uniform(.2,.8)*h)
        angle=rng.uniform(0,2*pi); w=rng.uniform(.035,.075)*h; height=w*1.3
        if i%stride==0: card(m,p,w*sqrt(stride),height*sqrt(stride),angle,leaf)
    return m

def write_obj(mesh,path):
    path=Path(path)
    with path.open('x',encoding='utf-8',newline='\n') as f:
        f.write('# Chimster Flora Forge; Z-up; material IDs only\n')
        for x,y,z in mesh.vertices: f.write(f'v {x:.7f} {y:.7f} {z:.7f}\n')
        for u,v in mesh.uv: f.write(f'vt {u:.7f} {v:.7f}\n')
        for material in sorted({m for _,m in mesh.faces}):
            f.write(f'g {material}\nusemtl {material}\n')
            for tri,mat in mesh.faces:
                if mat==material: f.write('f '+' '.join(f'{i+1}/{i+1}' for i in tri)+'\n')

def batch(recipes,output):
    output=Path(output); output.mkdir(parents=True,exist_ok=False); assets=[]; groups={}
    for i,recipe in enumerate(recipes):
        for level in range(4):
            mesh=generate(recipe,level); name=f'plant_{i:04d}_lod{level}.obj'; write_obj(mesh,output/name)
            assets.append({'file':name,'recipe':vars(recipe),'level':level,**mesh.stats()})
            for mat in sorted({m for _,m in mesh.faces}): groups.setdefault(f'lod{level}:{mat}',[]).append(name)
    report={'assets':assets,'groups':groups,'status':'intermediate OBJ only; no NIF, atlas, or baked billboard'}
    (output/'manifest.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8'); return report
