"""Manually baked, bounded local reflection/irradiance probes for SimplePBR."""
from dataclasses import dataclass
from math import isfinite,dist

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
        p=nearest(probes,tuple(node.get_pos()))
        if p is None:
            for key in INPUTS:node.clear_shader_input(key)
        else:
            env=p.environment
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
