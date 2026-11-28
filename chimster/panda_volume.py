"""Panda bindings for the shared volumetric scattering shader and sun depth pass."""
from . import gpu_lighting,gpu_volume

# Explicit named uniforms avoid driver differences in Panda array input handling.
def expand_arrays(source):
    for name in ("light_position","light_color","light_cone","volume_sphere"):
        source=source.replace(name+"[4]",name+"0,"+name+"1,"+name+"2,"+name+"3")
        source=source.replace(name+"[i]",name+"_at(i)")
    source=source.replace("uniform float volume_density[4];","uniform vec4 volume_density;")
    marker="vec3 local_light" if "vec3 local_light" in source else "float density_at"
    names=("light_position","light_color","light_cone") if marker=="vec3 local_light" else ("volume_sphere",)
    funcs="".join("vec4 "+n+"_at(int i){return i==0?"+n+"0:i==1?"+n+"1:i==2?"+n+"2:"+n+"3;}\n" for n in names)
    return source.replace(marker,funcs+marker,1)

SHADOW_GLSL="""
uniform sampler2D volume_shadow;
uniform int volume_shadow_enabled;
uniform vec3 volume_shadow_origin,volume_shadow_right,volume_shadow_up,volume_shadow_forward;
uniform float volume_shadow_extent,volume_shadow_near,volume_shadow_far,volume_shadow_bias;
float sun_visibility(vec3 p,float slope,bool soft){
 if(volume_shadow_enabled==0)return 1.0;
 vec3 d=p-volume_shadow_origin;
 vec2 q=vec2(dot(d,volume_shadow_right),dot(d,volume_shadow_up))/(2.0*volume_shadow_extent)+.5;
 float z=(dot(d,volume_shadow_forward)-volume_shadow_near)/(volume_shadow_far-volume_shadow_near);
 if(any(lessThan(q,vec2(0)))||any(greaterThan(q,vec2(1)))||z<0.0||z>1.0)return 1.0;
 return step(z-volume_shadow_bias,texture(volume_shadow,q).r);
}
uniform sampler2D volume_spot_depth;
uniform int volume_spot_index;
uniform vec3 volume_spot_origin,volume_spot_right,volume_spot_up,volume_spot_forward;
uniform vec2 volume_spot_proj;
uniform float volume_spot_near,volume_spot_far;
float local_visibility(int i,vec3 p){
 if(i!=volume_spot_index)return 1.0;
 vec3 d=p-volume_spot_origin;
 float z=dot(d,volume_spot_forward);
 if(z<=volume_spot_near||z>=volume_spot_far)return 1.0;
 vec2 q=vec2(dot(d,volume_spot_right),dot(d,volume_spot_up))*volume_spot_proj/z*.5+.5;
 if(any(lessThan(q,vec2(0)))||any(greaterThan(q,vec2(1))))return 1.0;
 float depth=volume_spot_far/(volume_spot_far-volume_spot_near)*(1.0-volume_spot_near/z);
 return step(depth-volume_shadow_bias,texture(volume_spot_depth,q).r);
}
"""
GLSL=expand_arrays(gpu_lighting.GLSL)+SHADOW_GLSL+expand_arrays(gpu_volume.GLSL)

def needs_volume(effects):
    return bool(effects.fog_volumes or effects.fog_density and (effects.scatter_strength or effects.fog_falloff))

def bind(quad,preview,effects):
    from math import cos,radians
    from panda3d.core import Vec3,Vec4
    from .shadow_math import unit
    cam=preview.camera;root=preview.root;q=cam.get_quat(root)
    sun=preview.sun.get_quat(root).xform(Vec3(0,-1,0))
    inputs=dict(camera_eye=cam.get_pos(root),camera_right=q.xform(Vec3(1,0,0)),camera_up=q.xform(Vec3(0,0,1)),camera_forward=q.xform(Vec3(0,1,0)),world_sun=sun,ambient_level=effects.ambient,sun_color=effects.sun_color,sun_intensity=effects.sun_intensity,light_count=len(effects.lights),volume_steps=effects.volume_steps,volume_count=len(effects.fog_volumes),volume_distance=effects.volume_distance,fog_height=effects.fog_height,fog_falloff=effects.fog_falloff)
    for i in range(4):
        light=effects.lights[i] if i<len(effects.lights) else None
        volume=effects.fog_volumes[i] if i<len(effects.fog_volumes) else None
        inputs["light_position"+str(i)]=Vec4(*light.position,light.radius) if light else Vec4(0,0,0,1)
        inputs["light_color"+str(i)]=Vec4(*light.color,light.intensity) if light else Vec4(0)
        inputs["light_cone"+str(i)]=Vec4(*unit(light.direction),cos(radians(light.cone/2))) if light and light.direction else Vec4(0,0,1,-1)
        inputs["volume_sphere"+str(i)]=Vec4(*volume.center,volume.radius) if volume else Vec4(0,0,0,1)
    inputs["volume_density"]=Vec4(*(effects.fog_volumes[i].density if i<len(effects.fog_volumes) else 0. for i in range(4)))
    for name,value in inputs.items():quad.set_shader_input(name,value)

class SunDepth:
    """Bounded auxiliary sun map, only allocated for shadowed volume mode."""
    def __init__(self,preview,effects):
        from panda3d.core import Texture,GraphicsOutput,Camera,OrthographicLens,NodePath,BitMask32
        self.preview=preview;self.buffer=None;self.camera=None;self.effects=effects
        self.depth=Texture("volume-sun-depth")
        self.depth.set_format(Texture.F_depth_component)
        self.depth.set_minfilter(Texture.FT_nearest);self.depth.set_magfilter(Texture.FT_nearest)
        self.depth.set_wrap_u(Texture.WM_clamp);self.depth.set_wrap_v(Texture.WM_clamp)
        try:
            size=min(512,effects.shadow_size)
            self.buffer=preview.output.make_texture_buffer("volume-sun",size,size)
            if self.buffer is None:raise RuntimeError("Volume shadow buffer unavailable")
            self.buffer.set_sort(-2000)
            self.buffer.add_render_texture(self.depth,GraphicsOutput.RTM_bind_or_copy,GraphicsOutput.RTP_depth)
            self.buffer.set_clear_depth_active(True);self.buffer.set_clear_depth(1.)
            self.lens=OrthographicLens();self.lens.set_film_size(effects.shadow_extent*2,effects.shadow_extent*2)
            self.lens.set_near_far(.1,effects.shadow_extent*4)
            self.camera=preview.root.attach_new_node(Camera("volume-sun-camera",self.lens))
            self.camera.node().set_scene(preview.root)
            self.camera.node().set_camera_mask(BitMask32.bit(2))
            # Depth-only geometry path: preserve per-material alpha testing, avoid
            # recursively sampling the scene's lighting/shadow shader.
            state=NodePath("volume-depth-state");state.set_shader_off(100);state.set_light_off(100);state.set_fog_off(100)
            self.camera.node().set_initial_state(state.get_state())
            self.buffer.make_display_region().set_camera(self.camera)
        except Exception:
            self.close();raise
    def bind(self,quad):
        from panda3d.core import Vec3
        root=self.preview.root;sun=self.preview.sun
        self.camera.set_mat(root,sun.get_mat(root));q=self.camera.get_quat(root)
        for key,value in dict(volume_shadow=self.depth,volume_shadow_enabled=1,volume_shadow_origin=self.camera.get_pos(root),volume_shadow_right=q.xform(Vec3(1,0,0)),volume_shadow_up=q.xform(Vec3(0,0,1)),volume_shadow_forward=q.xform(Vec3(0,1,0)),volume_shadow_extent=self.effects.shadow_extent,volume_shadow_near=self.lens.get_near(),volume_shadow_far=self.lens.get_far(),volume_shadow_bias=self.effects.shadow_bias).items():quad.set_shader_input(key,value)
    def close(self):
        if self.buffer is not None:self.preview.engine.remove_window(self.buffer);self.buffer=None
        if self.camera is not None:self.camera.remove_node();self.camera=None

class SpotDepth(SunDepth):
    """One local spotlight visibility pass, bounded to 256 depth pixels."""
    def __init__(self,preview,effects,index):
        from panda3d.core import Texture,GraphicsOutput,Camera,PerspectiveLens,NodePath,BitMask32
        self.preview=preview;self.effects=effects;self.index=index
        self.buffer=None;self.camera=None
        self.depth=Texture("volume-spot-depth")
        self.depth.set_format(Texture.F_depth_component)
        self.depth.set_minfilter(Texture.FT_nearest);self.depth.set_magfilter(Texture.FT_nearest)
        self.depth.set_wrap_u(Texture.WM_clamp);self.depth.set_wrap_v(Texture.WM_clamp)
        try:
            self.buffer=preview.output.make_texture_buffer("volume-spot",256,256)
            if self.buffer is None:raise RuntimeError("Spot volume shadow buffer unavailable")
            self.buffer.set_sort(-1999)
            self.buffer.add_render_texture(self.depth,GraphicsOutput.RTM_bind_or_copy,GraphicsOutput.RTP_depth)
            self.buffer.set_clear_depth_active(True);self.buffer.set_clear_depth(1.)
            light=effects.lights[index]
            self.lens=PerspectiveLens();self.lens.set_fov(light.cone);self.lens.set_near_far(.05,max(.1,light.radius))
            self.camera=preview.root.attach_new_node(Camera("volume-spot-camera",self.lens))
            self.camera.node().set_scene(preview.root);self.camera.node().set_camera_mask(BitMask32.bit(2))
            state=NodePath("volume-spot-state");state.set_shader_off(100);state.set_light_off(100);state.set_fog_off(100)
            self.camera.node().set_initial_state(state.get_state())
            self.buffer.make_display_region().set_camera(self.camera)
        except Exception:
            self.close();raise
    def bind(self,quad):
        from math import tan,radians
        from panda3d.core import Vec3
        root=self.preview.root;light=self.preview.effect_nodes[self.index]
        self.camera.set_mat(root,light.get_mat(root));q=self.camera.get_quat(root)
        h,v=self.lens.get_fov()
        for key,value in dict(volume_spot_depth=self.depth,volume_spot_index=self.index,volume_spot_origin=self.camera.get_pos(root),volume_spot_right=q.xform(Vec3(1,0,0)),volume_spot_up=q.xform(Vec3(0,0,1)),volume_spot_forward=q.xform(Vec3(0,1,0)),volume_spot_proj=(1/tan(radians(h)/2),1/tan(radians(v)/2)),volume_spot_near=self.lens.get_near(),volume_spot_far=self.lens.get_far()).items():quad.set_shader_input(key,value)
