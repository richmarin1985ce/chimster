"""GLSL FilterManager with shared world-space volumetric lighting."""
from . import panda_volume
VERTEX="""#version 130
uniform mat4 p3d_ModelViewProjectionMatrix;
in vec4 p3d_Vertex;
in vec2 p3d_MultiTexCoord0;
out vec2 uv;
void main(){uv=p3d_MultiTexCoord0;gl_Position=p3d_ModelViewProjectionMatrix*p3d_Vertex;}"""
FRAGMENT="""#version 130
in vec2 uv;
uniform sampler2D color_tex,depth_tex;
uniform vec2 pixel,proj;
uniform float nearp,farp,ao_strength,ao_radius,fog_density,scatter_strength,anisotropy;
uniform vec3 fog_color;
uniform int use_volume,hdr_pass;
out vec4 frag;
"""+panda_volume.GLSL+"""
float depth(float d){return nearp*farp/(farp-d*(farp-nearp));}
vec3 pos(vec2 q){
 float z=depth(texture(depth_tex,clamp(q,0.0,1.0)).r);
 return vec3((q*2.0-1.0)*z/proj,z);
}
void main(){
 vec4 src=texture(color_tex,uv);
 float d=texture(depth_tex,uv).r;
 if(d>=.999999&&use_volume==0){frag=src;return;}
 vec3 p=pos(uv);
 if(d>=.999999)p=normalize(p)*volume_distance;
 vec3 dx1=pos(uv+vec2(pixel.x,0))-p,dx2=p-pos(uv-vec2(pixel.x,0));
 vec3 dy1=pos(uv+vec2(0,pixel.y))-p,dy2=p-pos(uv-vec2(0,pixel.y));
 vec3 n=cross(abs(dy1.z)<abs(dy2.z)?dy1:dy2,abs(dx1.z)<abs(dx2.z)?dx1:dx2);
 n=length(n)>1e-8?normalize(n):vec3(0,0,-1);
 float occ=0.0,weight=0.0;
 float px=clamp(ao_radius*proj.y/(p.z*pixel.y*2.0),2.0,24.0);
 if(ao_strength>0.0&&d<.999999){
 for(int i=0;i<8;i++){
   vec2 dir=vec2(cos(float(i)*.785398),sin(float(i)*.785398));
   for(int j=1;j<=2;j++){
     vec2 q=uv+dir*pixel*px*float(j)*.5;
     if(any(lessThan(q,vec2(0)))||any(greaterThan(q,vec2(1)))||texture(depth_tex,q).r>=.999999)continue;
     vec3 delta=pos(q)-p;
     float dist=length(delta);
     occ+=max(0.0,dot(n,delta/max(dist,1e-5))-.08)*(1.0-smoothstep(ao_radius*.4,ao_radius,dist));
     weight+=1.0;
   }
 }
 }
 vec3 rgb=src.rgb*(1.0-ao_strength*occ/max(1.0,weight));
 if(use_volume!=0)rgb=integrate_fog(rgb,p);
 frag=vec4(hdr_pass!=0?max(rgb,vec3(0.0)):clamp(rgb,0.0,1.0),src.a);
}"""

class GLSLFilters:
    def __init__(self,preview,effects,pipeline=None,cascades=None):
        from direct.filter.FilterManager import FilterManager
        from panda3d.core import Texture,Shader,FrameBufferProperties,GraphicsOutput
        self.preview=preview;self.effects=effects;self.cascades=cascades
        self.owns_manager=pipeline is None
        self.manager=FilterManager(preview.output,preview.camera) if self.owns_manager else pipeline._filtermgr
        self.quad=None;self.sun_depth=None;self.spot_depth=None;self.state=preview.root.get_state()
        self.volume=panda_volume.needs_volume(effects);self.shadow_error=None
        try:
            if self.volume:preview.root.clear_fog()
            color=Texture("chimster-post-color") if self.owns_manager else self.manager.buffers[0].get_texture()
            depth=Texture("chimster-post-depth")
            depth.set_format(Texture.F_depth_component)
            for tex in (color,depth):
                tex.set_wrap_u(Texture.WM_clamp);tex.set_wrap_v(Texture.WM_clamp)
                tex.set_minfilter(Texture.FT_nearest);tex.set_magfilter(Texture.FT_nearest)
            if self.owns_manager:
                quad=self.manager.render_scene_into(colortex=color,depthtex=depth)
            else:
                # Insert before SimplePBR tone mapping, inside its existing filter
                # graph, retaining the HDR scene and its original camera.
                self.manager.buffers[0].add_render_texture(depth,GraphicsOutput.RTM_bind_or_copy,GraphicsOutput.RTP_depth)
                hdr=Texture("chimster-volume-hdr")
                hdr.set_format(Texture.F_rgba16);hdr.set_component_type(Texture.T_float)
                props=FrameBufferProperties();props.set_float_color(True);props.set_rgba_bits(16,16,16,16)
                quad=self.manager.render_quad_into("chimster-volume-hdr",colortex=hdr,fbprops=props)
                if quad is not None:pipeline._post_process_quad.set_shader_input("tex",hdr)
            if quad is None:raise RuntimeError("GLSL filter buffer unavailable")
            self.quad=quad
            shader=Shader.make(Shader.SL_GLSL,VERTEX,FRAGMENT)
            quad.set_shader(shader)
            quad.set_shader_input("color_tex",color);quad.set_shader_input("depth_tex",depth)
            gsg=preview.output.get_gsg()
            shader.prepare_now(gsg.get_prepared_objects(),gsg)
            if shader.get_error_flag():raise RuntimeError("GLSL post shader failed")
            quad.set_shader_input("pixel",(1/preview.output.get_x_size(),1/preview.output.get_y_size()))
            for key in ("ao_strength","ao_radius","fog_density","scatter_strength","fog_color"):
                quad.set_shader_input(key,getattr(effects,key))
            quad.set_shader_input("anisotropy",effects.scatter_anisotropy)
            quad.set_shader_input("use_volume",int(self.volume));quad.set_shader_input("hdr_pass",int(not self.owns_manager))
            # Valid sampler and uniforms even when the shadow pass is disabled.
            from panda3d.core import Mat4
            quad.set_shader_input("chimster_csm_enabled",0)
            quad.set_shader_input("chimster_csm_bias",effects.shadow_bias);quad.set_shader_input("chimster_csm_texel",1.)
            for i in range(2):
                quad.set_shader_input("chimster_csm"+str(i),depth);quad.set_shader_input("chimster_mvp"+str(i),Mat4.ident_mat())
            quad.set_shader_input("volume_shadow",depth)
            quad.set_shader_input("volume_spot_depth",depth)
            quad.set_shader_input("volume_spot_index",-1)
            for key,val in dict(volume_spot_origin=(0,0,0),volume_spot_right=(1,0,0),volume_spot_up=(0,0,1),volume_spot_forward=(0,1,0),volume_spot_proj=(1,1),volume_spot_near=.05,volume_spot_far=1.).items():quad.set_shader_input(key,val)
            quad.set_shader_input("volume_shadow_enabled",0)
            for key,val in dict(volume_shadow_origin=(0,0,0),volume_shadow_right=(1,0,0),volume_shadow_up=(0,0,1),volume_shadow_forward=(0,1,0),volume_shadow_extent=1.,volume_shadow_near=.1,volume_shadow_far=1.,volume_shadow_bias=effects.shadow_bias).items():quad.set_shader_input(key,val)
            if self.volume and effects.shadow_size and effects.scatter_strength:
                if cascades is None:
                    try:self.sun_depth=panda_volume.SunDepth(preview,effects)
                    except Exception as exc:self.shadow_error=str(exc)[:160]
                index=next((i for i,light in enumerate(effects.lights) if light.shadows and light.direction is not None),None)
                if index is not None:
                    try:self.spot_depth=panda_volume.SpotDepth(preview,effects,index)
                    except Exception as exc:self.shadow_error=str(exc)[:160]
        except Exception:
            self.close()
            raise
    def update(self):
        from math import tan,radians
        from panda3d.core import Vec3
        lens=self.preview.lens
        h,v=lens.get_fov()
        self.quad.set_shader_input("proj",(1/tan(radians(h)/2),1/tan(radians(v)/2)))
        self.quad.set_shader_input("nearp",lens.get_near());self.quad.set_shader_input("farp",lens.get_far())
        panda_volume.bind(self.quad,self.preview,self.effects)
        if self.cascades is not None:self.cascades.bind(self.quad)
        if self.sun_depth is not None:self.sun_depth.bind(self.quad)
        if self.spot_depth is not None:self.spot_depth.bind(self.quad)
    def close(self):
        if self.spot_depth is not None:self.spot_depth.close();self.spot_depth=None
        if self.sun_depth is not None:self.sun_depth.close();self.sun_depth=None
        if self.owns_manager:self.manager.cleanup();self.manager.ignore_all()
        self.quad=None
        self.preview.root.set_state(self.state)
