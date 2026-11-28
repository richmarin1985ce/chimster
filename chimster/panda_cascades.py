"""Panda-native PSSM cameras and two-depth-map SimplePBR adapter."""
GLSL="""
uniform int chimster_csm_enabled;
uniform sampler2D chimster_csm0,chimster_csm1;
uniform mat4 chimster_mvp0,chimster_mvp1;
uniform float chimster_csm_bias,chimster_csm_texel;
vec3 chimster_coord(mat4 m,vec3 p){
 vec4 q=m*vec4(p,1.0);
 return q.xyz/q.w*.5+.5;
}
bool chimster_inside(vec3 q){return all(greaterThan(q,vec3(0)))&&all(lessThan(q,vec3(1)));}
float chimster_sample(sampler2D map,vec3 q,bool soft){
 if(!chimster_inside(q))return 1.0;
 if(!soft)return step(q.z-chimster_csm_bias,texture(map,q.xy).r);
 float sum=0.0;
 for(int y=-1;y<=1;y++)for(int x=-1;x<=1;x++){
   vec2 uv=q.xy+vec2(x,y)*chimster_csm_texel;
   sum+=any(lessThan(uv,vec2(0)))||any(greaterThan(uv,vec2(1)))?1.0:step(q.z-chimster_csm_bias,texture(map,uv).r);
 }
 return sum/9.0;
}
float chimster_csm(vec3 p,bool soft){
 vec3 a=chimster_coord(chimster_mvp0,p),b=chimster_coord(chimster_mvp1,p);
 if(!chimster_inside(a))return chimster_sample(chimster_csm1,b,soft);
 float v=chimster_sample(chimster_csm0,a,soft);
 if(!chimster_inside(b))return v;
 float edge=max(max(abs(a.x-.5),abs(a.y-.5)),abs(a.z-.5))*2.0;
 return mix(v,chimster_sample(chimster_csm1,b,soft),smoothstep(.8,.98,edge));
}
"""

def shader(pipeline):
    from simplepbr import _shaderutils
    from panda3d.core import Shader
    defines=dict(MAX_LIGHTS=pipeline.max_lights,USE_NORMAL_MAP=pipeline.use_normal_maps,USE_EMISSION_MAP=pipeline.use_emission_maps,ENABLE_SHADOWS=pipeline.enable_shadows,ENABLE_FOG=pipeline.enable_fog,USE_OCCLUSION_MAP=pipeline.use_occlusion_maps,USE_330=True,IS_WEBGL=False,ENABLE_SKINNING=False,CALC_NORMAL_Z=pipeline.calculate_normalmap_blue)
    vert=_shaderutils._load_shader_str("simplepbr.vert",defines)
    frag=_shaderutils._load_shader_str("simplepbr.frag",defines)
    marker="        float shadow = shadowSpot * shadow_caster * attenuation_factor;"
    if marker not in frag:raise RuntimeError("Unsupported upstream PBR shader")
    frag=frag.replace(marker,"        if(chimster_csm_enabled!=0 && p3d_LightSource[i].position.w==0.0)shadow_caster=chimster_csm(v_world_position,true);\n"+marker)
    pos=frag.index("void main(")
    frag=frag[:pos]+GLSL+frag[pos:]
    return Shader.make(Shader.SL_GLSL,vert,frag)

class Cascades:
    def __init__(self,preview,effects):
        from panda3d.core import Texture,GraphicsOutput,Camera,OrthographicLens,NodePath,BitMask32
        self.preview=preview;self.effects=effects;self.buffers=[];self.cameras=[];self.textures=[];self.rig=None
        self.size=min(1024,effects.shadow_size)
        self.distance=min(preview.lens.get_far(),effects.shadow_extent*2,800.)
        try:
            try:
                from panda3d._rplight import PSSMCameraRig
                self.rig=PSSMCameraRig(2)
                self.rig.reparent_to(preview.root);self.rig.set_resolution(self.size)
                self.rig.set_pssm_distance(self.distance);self.rig.set_sun_distance(max(40.,self.distance*2))
                self.rig.set_use_fixed_film_size(True);self.rig.set_use_stable_csm(True)
                self.rig.set_logarithmic_factor(.5);self.rig.set_border_bias(.15)
            except ImportError:self.rig=None
            state=NodePath("cascade-depth-state")
            state.set_shader_off(100);state.set_light_off(100);state.set_fog_off(100)
            for i in range(2):
                camera=self.rig.get_camera(i) if self.rig else preview.root.attach_new_node(Camera("cascade-"+str(i),OrthographicLens()))
                self.cameras.append(camera)
                camera.node().set_scene(preview.root);camera.node().set_camera_mask(BitMask32.bit(2))
                camera.node().set_initial_state(state.get_state())
                tex=Texture("cascade-depth-"+str(i));tex.set_format(Texture.F_depth_component)
                tex.set_minfilter(Texture.FT_nearest);tex.set_magfilter(Texture.FT_nearest)
                tex.set_wrap_u(Texture.WM_clamp);tex.set_wrap_v(Texture.WM_clamp)
                buf=preview.output.make_texture_buffer("cascade-"+str(i),self.size,self.size)
                if buf is None:raise RuntimeError("Cascade depth buffer unavailable")
                self.buffers.append(buf);self.textures.append(tex);buf.set_sort(-2100+i)
                buf.add_render_texture(tex,GraphicsOutput.RTM_bind_or_copy,GraphicsOutput.RTP_depth)
                buf.set_clear_depth_active(True);buf.set_clear_depth(1.)
                buf.make_display_region().set_camera(camera)
        except Exception:
            self.close();raise
    def update(self):
        from panda3d.core import Vec3,Point3
        from math import radians,tan
        p=self.preview;root=p.root;sun=p.sun.get_quat(root).xform(Vec3(0,-1,0))
        if self.rig:
            self.rig.update(p.camera,sun)
        else:
            from .gpu_shadows import frustum_frames
            q=p.camera.get_quat(root);h,v=p.lens.get_fov()
            view=(tuple(p.camera.get_pos(root)),tuple(q.xform(Vec3(1,0,0))),tuple(q.xform(Vec3(0,0,1))),tuple(q.xform(Vec3(0,-1,0))),tan(radians(h)/2),tan(radians(v)/2))
            _,_,axis,views,_,_=frustum_frames(view,p.lens.get_near(),p.lens.get_far(),tuple(sun),self.effects.shadow_extent,self.size,2)
            for camera,(center,size) in zip(self.cameras,views):
                lens=camera.node().get_lens();lens.set_film_size(size*2,size*2);lens.set_near_far(.1,size*8)
                camera.set_pos(*(center[i]+axis[i]*size*4 for i in range(3)))
                camera.look_at(Point3(*center),Vec3(0,0,1) if abs(axis[2])<.99 else Vec3(0,1,0))
    def bind(self,node):
        node.set_shader_input("chimster_csm_enabled",1)
        node.set_shader_input("chimster_csm_bias",self.effects.shadow_bias)
        node.set_shader_input("chimster_csm_texel",1/self.size)
        for i,(camera,tex) in enumerate(zip(self.cameras,self.textures)):
            m=self.preview.root.get_transform(camera).get_mat()*camera.node().get_lens().get_projection_mat()
            node.set_shader_input("chimster_mvp"+str(i),m)
            node.set_shader_input("chimster_csm"+str(i),tex)
    def close(self):
        for b in self.buffers:self.preview.engine.remove_window(b)
        for c in self.cameras:c.remove_node()
        self.buffers.clear();self.cameras.clear();self.textures.clear();self.rig=None
