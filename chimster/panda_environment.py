"""Asset-free sky cubemap for SimplePBR's upstream image-based lighting."""
from functools import lru_cache
from math import sqrt

def sky_bytes(size,color,strength):
    out=bytearray()
    for face in range(6):
        for y in range(size):
            v=2*(y+.5)/size-1
            for x in range(size):
                u=2*(x+.5)/size-1
                # Panda cubemap face sequence: +X,-X,+Y,-Y,+Z,-Z.
                d=((1,-v,-u),(-1,-v,u),(u,1,v),(u,-1,-v),(u,-v,1),(-u,-v,-1))[face]
                z=d[2]/sqrt(sum(q*q for q in d))
                t=max(0.,z)
                for c,top in zip(color,(.40,.57,.8)):
                    value=(c*(1-t)+top*t) if z>=0 else c*(1+.65*z)
                    out.append(round(max(0.,min(1.,value*strength))*255))
                out.append(255)
    return bytes(out)

@lru_cache(maxsize=4)
def environment(color,strength):
    from panda3d.core import Texture
    from simplepbr import EnvMap
    tex=Texture("chimster-procedural-sky")
    tex.setup_cube_map(16,Texture.T_unsigned_byte,Texture.F_rgba8)
    tex.set_ram_image_as(sky_bytes(16,color,strength),"RGBA")
    return EnvMap(tex,prefiltered_size=16,prefiltered_samples=8,blocking_prepare=True)
