"""Manually baked, bounded local reflection/irradiance probes for SimplePBR."""
from dataclasses import dataclass
from math import isfinite,dist
from functools import lru_cache
import base64,json
from pathlib import Path

@dataclass(frozen=True)
class Probe:
    center:tuple
    radius:float
    environment:object

def nearest(probes,position):
    inside=[(dist(p.center,position)/p.radius,i,p) for i,p in enumerate(probes) if dist(p.center,position)<=p.radius]
    return min(inside,key=lambda item:(item[0],item[1]))[2] if inside else None

INPUTS=("sh_coeffs","filtered_env_map","max_reflection_lod")

def apply(model,probes):
    if model is None:return 0
    count=0
    for node in model.get_children():
        if not node.has_tag("chimster_id"):continue
        env=blended(probes,tuple(node.get_pos()))
        if env is None:
            for key in INPUTS:node.clear_shader_input(key)
        else:
            node.set_shader_input("sh_coeffs",env.sh_coefficients)
            node.set_shader_input("filtered_env_map",env.filtered_env_map)
            node.set_shader_input("max_reflection_lod",env.filtered_env_map.num_loadable_ram_mipmap_images)
            count+=1
    return count

def capture(preview,center,radius,size=32):
    from panda3d.core import BitMask32,NodePath,Texture
    from simplepbr import EnvMap
    if preview.output is None:raise ValueError("Render a scene before baking a probe")
    if len(center)!=3 or any(not isfinite(x) or abs(x)>1e7 for x in center) or not isfinite(radius) or not .1<=radius<=10000 or size not in (16,32,64):
        raise ValueError("Invalid probe bounds or resolution")
    if preview.visibility is not None:raise ValueError("Disable camera-specific room visibility before baking a probe")
    rig=preview.root.attach_new_node("probe-capture")
    rig.set_pos(*center);buf=None
    try:
        buf=preview.output.make_cube_map("local-probe",size,rig,BitMask32.bit(2),True)
        if buf is None:raise RuntimeError("Cubemap capture unavailable")
        buf.set_sort(-1600)
        state=NodePath("probe-native-state");state.set_shader_off(100);state.set_fog_off(100)
        for region in buf.get_display_regions():
            cam=region.get_camera()
            if cam.is_empty():continue
            cam.node().set_scene(preview.root)
            cam.node().set_initial_state(state.get_state())
            cam.node().get_lens().set_near_far(.05,max(1.,radius*2))
            region.set_clear_color((.12,.18,.25,1));region.set_clear_color_active(True)
            region.set_clear_depth(1.);region.set_clear_depth_active(True)
        preview.engine.render_frame();preview.engine.sync_frame()
        tex=buf.get_texture()
        if not tex.has_ram_image():raise RuntimeError("Incomplete cubemap capture")
        raw=bytes(tex.get_ram_image_as("RGBA"))
        if len(raw)!=6*size*size*4:raise RuntimeError("Incomplete six-face cubemap")
        cube=Texture("local-probe-baked")
        cube.setup_cube_map(size,Texture.T_unsigned_byte,Texture.F_rgba8)
        cube.set_ram_image_as(raw,"RGBA")
        env=EnvMap(cube,prefiltered_size=size,prefiltered_samples=8,blocking_prepare=True)
        if not env.filtered_env_map.has_ram_image():raise RuntimeError("Probe filtering incomplete")
        return Probe(tuple(center),radius,env)
    finally:
        if buf is not None:preview.engine.remove_window(buf)
        rig.remove_node()

def influence(probes,position):
    """Two strongest smooth radial weights; quantize blend to bound work."""
    candidates=[]
    for i,p in enumerate(probes):
        x=max(0.,1.-dist(p.center,position)/p.radius)
        w=x*x*(3.-2.*x)
        if w>0:candidates.append((w,i))
    candidates.sort(key=lambda x:(-x[0],x[1]))
    if not candidates:return ()
    if len(candidates)==1:return ((candidates[0][1],8),)
    a,b=candidates[:2]
    k=max(0,min(8,round(8*b[0]/(a[0]+b[0]))))
    return ((a[1],8-k),(b[1],k)) if k else ((a[1],8),)

def cubemap_data(env):
    tex=env.cubemap
    size=tex.get_x_size()
    raw=bytes(tex.get_ram_image_as("RGBA"))
    if size not in (16,32,64) or len(raw)!=6*size*size*4:raise ValueError("Invalid probe image")
    return size,raw

def environment_from_data(size,raw):
    from panda3d.core import Texture
    from simplepbr import EnvMap
    if size not in (16,32,64) or len(raw)!=6*size*size*4:raise ValueError("Invalid probe image")
    cube=Texture("local-probe")
    cube.setup_cube_map(size,Texture.T_unsigned_byte,Texture.F_rgba8)
    cube.set_ram_image_as(raw,"RGBA")
    env=EnvMap(cube,prefiltered_size=size,prefiltered_samples=8,blocking_prepare=True)
    if not env.filtered_env_map.has_ram_image():raise RuntimeError("Probe filtering incomplete")
    return env

def resample(size,raw,target):
    if size==target:return raw
    out=bytearray()
    for face in range(6):
        for y in range(target):
            for x in range(target):
                pos=4*(face*size*size+(y*size//target)*size+x*size//target)
                out.extend(raw[pos:pos+4])
    return bytes(out)

@lru_cache(maxsize=12)
def blend_pair(a,b,k):
    sa,ra=cubemap_data(a);sb,rb=cubemap_data(b);size=min(sa,sb)
    ra=resample(sa,ra,size);rb=resample(sb,rb,size)
    raw=bytes((x*(8-k)+y*k+4)//8 for x,y in zip(ra,rb))
    return environment_from_data(size,raw)

def blended(probes,position):
    weights=influence(probes,position)
    if not weights:return None
    a,wa=weights[0]
    if len(weights)==1:return probes[a].environment
    b,k=weights[1]
    return blend_pair(probes[a].environment,probes[b].environment,k)

def save(path,probes):
    if len(probes)>4:raise ValueError("Too many probes")
    rows=[]
    for probe in probes:
        size,raw=cubemap_data(probe.environment)
        rows.append(dict(center=probe.center,radius=probe.radius,size=size,rgba=base64.b64encode(raw).decode("ascii")))
    with Path(path).open("x",encoding="utf-8") as f:
        json.dump(dict(version=1,probes=rows),f,allow_nan=False,separators=(",",":"))

def load(path):
    p=Path(path)
    if p.stat().st_size>1024*1024:raise ValueError("Probe file too large")
    data=json.loads(p.read_text(encoding="utf-8"))
    if data.get("version")!=1 or not isinstance(data.get("probes"),list) or len(data["probes"])>4:raise ValueError("Invalid probe file")
    decoded=[]
    for row in data["probes"]:
        center=tuple(row["center"]);radius=row["radius"];size=row["size"]
        if len(center)!=3 or any(not isfinite(x) or abs(x)>1e7 for x in center) or not isfinite(radius) or not .1<=radius<=10000 or type(size) is not int or size not in (16,32,64):raise ValueError("Invalid probe metadata")
        raw=base64.b64decode(row["rgba"],validate=True)
        if len(raw)!=6*size*size*4:raise ValueError("Invalid probe image")
        decoded.append((center,radius,size,raw))
    return [Probe(center,radius,environment_from_data(size,raw)) for center,radius,size,raw in decoded]
