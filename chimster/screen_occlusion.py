"""Screen-space AO and bounded world-space volumetric integration."""
from . import gpu_lighting,gpu_shadows,gpu_volume
VERTEX="""#version 330
out vec2 uv;
void main(){
 vec2 p=vec2((gl_VertexID<<1)&2,gl_VertexID&2);
 uv=p; gl_Position=vec4(p*2.0-1.0,0,1);
}"""
FRAGMENT="""#version 330
in vec2 uv;
uniform sampler2D image, depthmap, surfacemap;
uniform float ssr_strength,ssr_distance;
uniform int ssr_steps;
uniform vec2 pixel;
uniform float nearp,farp, radius, strength, projection_y;
uniform float fog_density,scatter_strength,anisotropy;
uniform vec3 fog_color;
out vec4 color;
"""+gpu_lighting.GLSL+gpu_shadows.GLSL+gpu_volume.GLSL+"""
float linear_depth(float d){return nearp*farp/(farp-d*(farp-nearp));}
vec3 position_at(vec2 q,float d){
 float z=linear_depth(d);
 return vec3((q*2.0-1.0)*vec2(pixel.y/pixel.x,1.0)*z/projection_y,z);
}
vec3 position_safe(vec2 q){return position_at(clamp(q,0.0,1.0),texture(depthmap,clamp(q,0.0,1.0)).r);}
vec3 reflect_screen(vec3 src,vec3 p){
 vec4 material=texture(surfacemap,uv);
 float amount=material.a*ssr_strength;
 if(amount<=.001)return src;
 vec3 world_normal=material.rgb*2.0-1.0;
 vec3 n=normalize(vec3(dot(world_normal,camera_right),dot(world_normal,camera_up),dot(world_normal,camera_forward)));
 vec3 incident=normalize(p);
 if(dot(n,incident)>0.0)n=-n;
 vec3 ray=reflect(incident,n);
 float step_size=ssr_distance/float(ssr_steps);
 float previous=0.0;
 bool valid_previous=false;
 for(int i=0;i<32;i++){
   if(i>=ssr_steps)break;
   vec3 sample_pos=p+n*.06+ray*(float(i)+.5)*step_size;
   if(sample_pos.z<=nearp)break;
   vec2 q=sample_pos.xy/sample_pos.z*projection_y*vec2(pixel.x/pixel.y,1.0)*.5+.5;
   if(any(lessThan(q,vec2(.001)))||any(greaterThan(q,vec2(.999))))break;
   float d=texture(depthmap,q).r;
   if(d>=.999999){valid_previous=false;continue;}
   float gap=sample_pos.z-linear_depth(d);
   if(valid_previous&&previous<0.0&&gap>=0.0&&gap<max(.12,step_size*1.25)){
     float edge=min(min(q.x,1.0-q.x),min(q.y,1.0-q.y));
     float fade=smoothstep(0.0,.08,edge)*(1.0-float(i)/float(ssr_steps));
     float fresnel=.04+.96*pow(1.0-max(0.0,-dot(n,incident)),5.0);
     return mix(src,texture(image,q).rgb,amount*fade*(.35+.65*fresnel));
   }
   previous=gap;valid_previous=true;
 }
 return src;
}
void main(){
 vec4 src=texture(image,uv);
 float raw=texture(depthmap,uv).r;
 if(raw>=.999999){color=src;return;}
 float z=linear_depth(raw);
 float pixels=clamp(radius*projection_y/(z*pixel.y*2.0),2.0,32.0);
 vec3 pos=position_at(uv,raw);
 vec3 dx1=position_safe(uv+vec2(pixel.x,0))-pos,dx2=pos-position_safe(uv-vec2(pixel.x,0));
 vec3 dy1=position_safe(uv+vec2(0,pixel.y))-pos,dy2=pos-position_safe(uv-vec2(0,pixel.y));
 vec3 dx=abs(dx1.z)<abs(dx2.z)?dx1:dx2;
 vec3 dy=abs(dy1.z)<abs(dy2.z)?dy1:dy2;
 vec3 normal=cross(dy,dx);
 normal=length(normal)>1e-8?normalize(normal):vec3(0,0,-1);
 float occ=0.0, weight=0.0;
 if(strength>0.0){
 for(int i=0;i<8;i++){
   float a=float(i)*.785398163;
   vec2 dir=vec2(cos(a),sin(a));
   for(int j=1;j<=2;j++){
     vec2 q=uv+dir*pixel*pixels*float(j)*.5;
     if(any(lessThan(q,vec2(0)))||any(greaterThan(q,vec2(1))))continue;
     float d=texture(depthmap,q).r;
     if(d>=.999999)continue;
     vec3 delta=position_at(q,d)-pos;
     float dist=length(delta);
     float fall=1.0-smoothstep(radius*.4,radius,dist);
     occ+=max(0.0,dot(normal,delta/max(dist,1e-5))-.08)*fall;
     weight+=1.0;
   }
 }
 }
 vec3 rgb=reflect_screen(src.rgb,pos)*(1.0-strength*occ/max(weight,1.0));
 if(fog_density>0.0||volume_count>0)rgb=integrate_fog(rgb,pos);
 color=vec4(clamp(rgb,0.0,1.0),src.a);
}"""

class Occlusion:
    def __init__(self,ctx):
        self.ctx=ctx
        self.program=ctx.program(vertex_shader=VERTEX,fragment_shader=FRAGMENT)
        self.vao=ctx.vertex_array(self.program,[])
        self.target=None
        self.size=None
    def render(self,image,depth,surface,w,h,settings,effects,projection_y,view,shadows):
        if self.size!=(w,h):
            self.release_target()
            tex=self.ctx.texture((w,h),4)
            self.target=(tex,self.ctx.framebuffer([tex]))
            self.size=(w,h)
        tex,fbo=self.target
        fbo.use();self.ctx.viewport=(0,0,w,h);self.ctx.enable_only(0)
        image.use(0);depth.use(1);surface.use(2)
        for k,v in dict(image=0,depthmap=1,surfacemap=2,ssr_strength=effects.ssr_strength,ssr_steps=effects.ssr_steps,ssr_distance=effects.ssr_distance,pixel=(1/w,1/h),nearp=settings.near,farp=settings.far,radius=effects.ao_radius,strength=effects.ao_strength,projection_y=projection_y,fog_density=effects.fog_density,fog_color=effects.fog_color,scatter_strength=effects.scatter_strength,anisotropy=effects.scatter_anisotropy).items():
            self.program[k].value=v
        gpu_lighting.bind(self.program,effects)
        gpu_shadows.bind(self.program,shadows,bool(effects.shadow_size))
        gpu_volume.bind(self.program,effects,view,settings)
        self.vao.render(vertices=3)
        return tex
    def release_target(self):
        if self.target:
            for obj in reversed(self.target):obj.release()
            self.target=None
        self.size=None
    def close(self):
        self.release_target();self.vao.release();self.program.release()
