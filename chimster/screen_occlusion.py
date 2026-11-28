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
uniform sampler2D image, depthmap, surfacemap,aomap;
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
 vec3 pos=position_at(uv,raw);
 float occ=0.0;
 if(strength>0.0){
   vec3 n=texture(surfacemap,uv).rgb*2.0-1.0;
   float total=0.0;
   for(int y=-1;y<=1;y++)for(int x=-1;x<=1;x++){
     vec2 q=clamp(uv+vec2(x,y)*pixel,vec2(0.0),vec2(1.0));
     float d=texture(depthmap,q).r;
     if(d>=.999999)continue;
     vec3 other=texture(surfacemap,q).rgb*2.0-1.0;
     float w=exp(-abs(linear_depth(d)-pos.z)/max(.02,radius*.15))*pow(max(0.0,dot(normalize(n),normalize(other))),8.0);
     w*=1.0/(1.0+float(x*x+y*y));
     occ+=texture(aomap,q).r*w;total+=w;
   }
   occ/=max(total,1e-5);
 }
 vec3 rgb=reflect_screen(src.rgb,pos)*(1.0-strength*occ);
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
        self.mask=None
    def render(self,image,depth,surface,w,h,settings,effects,projection_y,view,shadows):
        if self.size!=(w,h):
            self.release_target()
            tex=self.ctx.texture((w,h),4)
            self.target=(tex,self.ctx.framebuffer([tex]))
            self.size=(w,h)
        if effects.ao_strength:
            from .gpu_ao_mask import Mask
            if self.mask is None:self.mask=Mask(self.ctx)
            mask=self.mask.render(depth,w,h,settings,effects,projection_y)
        else:mask=surface
        tex,fbo=self.target
        fbo.use();self.ctx.viewport=(0,0,w,h);self.ctx.enable_only(0)
        image.use(0);depth.use(1);surface.use(2);mask.use(5)
        for k,v in dict(image=0,depthmap=1,surfacemap=2,aomap=5,ssr_strength=effects.ssr_strength,ssr_steps=effects.ssr_steps,ssr_distance=effects.ssr_distance,pixel=(1/w,1/h),nearp=settings.near,farp=settings.far,radius=effects.ao_radius,strength=effects.ao_strength,projection_y=projection_y,fog_density=effects.fog_density,fog_color=effects.fog_color,scatter_strength=effects.scatter_strength,anisotropy=effects.scatter_anisotropy).items():
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
        if self.mask is not None:self.mask.close();self.mask=None
        self.release_target();self.vao.release();self.program.release()
