"""Bounded depth-neighborhood screen-space occlusion, no world geometry pass."""
VERTEX="""#version 330
out vec2 uv;
void main(){
 vec2 p=vec2((gl_VertexID<<1)&2,gl_VertexID&2);
 uv=p; gl_Position=vec4(p*2.0-1.0,0,1);
}"""
FRAGMENT="""#version 330
in vec2 uv;
uniform sampler2D image, depthmap;
uniform vec2 pixel;
uniform float nearp,farp, radius, strength, projection_y;
out vec4 color;
float linear_depth(float d){return nearp*farp/(farp-d*(farp-nearp));}
void main(){
 vec4 src=texture(image,uv);
 float raw=texture(depthmap,uv).r;
 if(raw>=.999999){color=src;return;}
 float z=linear_depth(raw);
 float pixels=clamp(radius*projection_y/(z*pixel.y*2.0),2.0,32.0);
 float occ=0.0, weight=0.0;
 for(int i=0;i<8;i++){
   float a=float(i)*.785398163;
   vec2 dir=vec2(cos(a),sin(a));
   for(int j=1;j<=2;j++){
     vec2 q=uv+dir*pixel*pixels*float(j)*.5;
     if(any(lessThan(q,vec2(0)))||any(greaterThan(q,vec2(1))))continue;
     float d=texture(depthmap,q).r;
     if(d>=.999999)continue;
     float dz=z-linear_depth(d);
     float fall=1.0-smoothstep(radius*.5,radius,abs(dz));
     occ+=smoothstep(radius*.025,radius*.25,dz)*fall;
     weight+=1.0;
   }
 }
 color=vec4(src.rgb*(1.0-strength*occ/max(weight,1.0)),src.a);
}"""

class Occlusion:
    def __init__(self,ctx):
        self.ctx=ctx
        self.program=ctx.program(vertex_shader=VERTEX,fragment_shader=FRAGMENT)
        self.vao=ctx.vertex_array(self.program,[])
        self.target=None
        self.size=None
    def render(self,image,depth,w,h,settings,effects,projection_y):
        if self.size!=(w,h):
            self.release_target()
            tex=self.ctx.texture((w,h),4)
            self.target=(tex,self.ctx.framebuffer([tex]))
            self.size=(w,h)
        tex,fbo=self.target
        fbo.use();self.ctx.viewport=(0,0,w,h);self.ctx.enable_only(0)
        image.use(0);depth.use(1)
        for k,v in dict(image=0,depthmap=1,pixel=(1/w,1/h),nearp=settings.near,farp=settings.far,radius=effects.ao_radius,strength=effects.ao_strength,projection_y=projection_y).items():
            self.program[k].value=v
        self.vao.render(vertices=3)
        return tex
    def release_target(self):
        if self.target:
            for obj in reversed(self.target):obj.release()
            self.target=None
        self.size=None
    def close(self):
        self.release_target();self.vao.release();self.program.release()
