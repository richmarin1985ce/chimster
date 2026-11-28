"""GLSL FilterManager fallback for systems without legacy Cg filters."""
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
uniform vec3 fog_color,sun_view;
out vec4 frag;
float depth(float d){return nearp*farp/(farp-d*(farp-nearp));}
vec3 pos(vec2 q){
 float z=depth(texture(depth_tex,clamp(q,0.0,1.0)).r);
 return vec3((q*2.0-1.0)*z/proj,z);
}
void main(){
 vec4 src=texture(color_tex,uv);
 float d=texture(depth_tex,uv).r;
 if(d>=.999999){frag=src;return;}
 vec3 p=pos(uv);
 vec3 dx1=pos(uv+vec2(pixel.x,0))-p,dx2=p-pos(uv-vec2(pixel.x,0));
 vec3 dy1=pos(uv+vec2(0,pixel.y))-p,dy2=p-pos(uv-vec2(0,pixel.y));
 vec3 n=cross(abs(dy1.z)<abs(dy2.z)?dy1:dy2,abs(dx1.z)<abs(dx2.z)?dx1:dx2);
 n=length(n)>1e-8?normalize(n):vec3(0,0,-1);
 float occ=0.0,weight=0.0;
 float px=clamp(ao_radius*proj.y/(p.z*pixel.y*2.0),2.0,24.0);
 if(ao_strength>0.0){
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
 // Native scene already applies distance fog. Add only forward scattering.
 float mu=dot(normalize(p),normalize(sun_view)),g2=anisotropy*anisotropy;
 float phase=(1.0-g2)/pow(max(.01,1.0+g2-2.0*anisotropy*mu),1.5);
 rgb+=fog_color*(1.0-exp(-fog_density*length(p)))*scatter_strength*phase*.12;
 frag=vec4(clamp(rgb,0.0,1.0),src.a);
}"""

class GLSLFilters:
    def __init__(self,preview,effects):
        from direct.filter.FilterManager import FilterManager
        from panda3d.core import Texture,Shader
        self.preview=preview;self.effects=effects
        self.manager=FilterManager(preview.output,preview.camera)
        self.quad=None
        try:
            color=Texture("chimster-post-color");depth=Texture("chimster-post-depth")
            depth.set_format(Texture.F_depth_component)
            for tex in (color,depth):
                tex.set_wrap_u(Texture.WM_clamp);tex.set_wrap_v(Texture.WM_clamp)
                tex.set_minfilter(Texture.FT_nearest);tex.set_magfilter(Texture.FT_nearest)
            quad=self.manager.render_scene_into(colortex=color,depthtex=depth)
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
        # Use light orientation, not the camera-relative sun anchor.
        direction=self.preview.camera.get_relative_vector(self.preview.root,self.preview.sun.get_quat().xform(Vec3(0,-1,0)))
        self.quad.set_shader_input("sun_view",(direction.x,direction.z,direction.y))
    def close(self):
        self.manager.cleanup();self.manager.ignore_all();self.quad=None
