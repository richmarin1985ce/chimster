"""Depth and normal aware AO mask plus bilateral smoothing."""
from .screen_occlusion import VERTEX
FRAGMENT="""#version 330
in vec2 uv;
uniform sampler2D depthmap,surfacemap;
uniform vec2 pixel;
uniform float nearp,farp,radius,projection_y;
out float mask;
float depth(float d){return nearp*farp/(farp-d*(farp-nearp));}
vec3 pos(vec2 q,float d){
 float z=depth(d);
 return vec3((q*2.0-1.0)*vec2(pixel.y/pixel.x,1.0)*z/projection_y,z);
}
void main(){
 float raw=texture(depthmap,uv).r;
 if(raw>=.999999){mask=0.0;return;}
 vec3 p=pos(uv,raw);
 vec3 dx1=pos(uv+vec2(pixel.x,0),texture(depthmap,uv+vec2(pixel.x,0)).r)-p;
 vec3 dx2=p-pos(uv-vec2(pixel.x,0),texture(depthmap,uv-vec2(pixel.x,0)).r);
 vec3 dy1=pos(uv+vec2(0,pixel.y),texture(depthmap,uv+vec2(0,pixel.y)).r)-p;
 vec3 dy2=p-pos(uv-vec2(0,pixel.y),texture(depthmap,uv-vec2(0,pixel.y)).r);
 vec3 n=cross(abs(dy1.z)<abs(dy2.z)?dy1:dy2,abs(dx1.z)<abs(dx2.z)?dx1:dx2);
 n=length(n)>1e-8?normalize(n):vec3(0,0,-1);
 float pixels=clamp(radius*projection_y/(p.z*pixel.y*2.0),2.0,32.0);
 float occ=0.0,weight=0.0;
 for(int i=0;i<8;i++){
   vec2 dir=vec2(cos(float(i)*.785398),sin(float(i)*.785398));
   for(int j=1;j<=2;j++){
     vec2 q=uv+dir*pixel*pixels*float(j)*.5;
     if(any(lessThan(q,vec2(0)))||any(greaterThan(q,vec2(1))))continue;
     float d=texture(depthmap,q).r;
     if(d>=.999999)continue;
     vec3 delta=pos(q,d)-p;
     float dist=length(delta);
     occ+=max(0.0,dot(n,delta/max(dist,1e-5))-.08)*(1.0-smoothstep(radius*.4,radius,dist));
     weight+=1.0;
   }
 }
 mask=occ/max(1.0,weight);
}"""
class Mask:
    def __init__(self,ctx):
        self.ctx=ctx;self.program=ctx.program(vertex_shader=VERTEX,fragment_shader=FRAGMENT)
        self.vao=ctx.vertex_array(self.program,[]);self.targets=None;self.size=None
    def render(self,depth,w,h,settings,effects,projection_y):
        if self.size!=(w,h):
            self.release_targets()
            tex=self.ctx.texture((w,h),1,dtype="f2")
            tex.repeat_x=False;tex.repeat_y=False
            self.targets=(tex,self.ctx.framebuffer([tex]));self.size=(w,h)
        tex,fbo=self.targets
        fbo.use();self.ctx.viewport=(0,0,w,h);self.ctx.enable_only(0)
        depth.use(1)
        for k,v in dict(depthmap=1,pixel=(1/w,1/h),nearp=settings.near,farp=settings.far,radius=effects.ao_radius,projection_y=projection_y).items():self.program[k].value=v
        self.vao.render(vertices=3)
        return tex
    def release_targets(self):
        if self.targets:
            for obj in reversed(self.targets):obj.release()
        self.targets=None;self.size=None
    def close(self):
        self.release_targets();self.vao.release();self.program.release()
