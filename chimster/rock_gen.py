"""Seeded, game-neutral rock meshes. Z-up; intermediate OBJ only."""
from dataclasses import dataclass
from math import sin, cos, pi, isfinite
from random import Random
from .flora import Mesh

@dataclass(frozen=True)
class RockRecipe:
    seed: int = 42
    width: float = 2.0
    depth: float = 1.5
    height: float = 1.0
    roughness: float = .25
    detail: int = 2

def generate(recipe):
    if not all(isfinite(v) and .001 <= v <= 10000 for v in (recipe.width,recipe.depth,recipe.height)):
        raise ValueError("dimensions must be finite and positive")
    if not 0 <= recipe.roughness <= .45 or type(recipe.detail) is not int or not 0 <= recipe.detail <= 4:
        raise ValueError("roughness 0..0.45; detail 0..4")
    rng=Random(recipe.seed)
    sides=8*2**recipe.detail
    rings=2+recipe.detail
    vertices=[(0,0,0)]
    uv=[(.5,0)]
    for j in range(1,rings+1):
        theta=pi*j/(rings+1)
        for i in range(sides):
            a=2*pi*i/sides
            scale=1+rng.uniform(-recipe.roughness,recipe.roughness)
            vertices.append((recipe.width/2*sin(theta)*cos(a)*scale,
                             recipe.depth/2*sin(theta)*sin(a)*scale,
                             recipe.height*(1-cos(theta))/2))
            uv.append((i/sides,j/(rings+1)))
    top=len(vertices)
    vertices.append((0,0,recipe.height));uv.append((.5,1))
    faces=[]
    for i in range(sides):
        n=(i+1)%sides
        faces.append((0,1+n,1+i))
        for j in range(rings-1):
            a=1+j*sides+i;b=1+j*sides+n
            faces.extend(((a,b,a+sides),(b,b+sides,a+sides)))
        a=1+(rings-1)*sides+i;b=1+(rings-1)*sides+n
        faces.append((a,b,top))
    mesh=Mesh();mesh.add(vertices,uv,faces,"rock__opaque")
    return mesh
