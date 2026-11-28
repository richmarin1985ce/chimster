"""Two nested, texel-stabilized orthographic sun shadow maps."""
from .shadow_math import unit,cross,snap_center,dot

GLSL="""
uniform sampler2D shadow_near,shadow_far;
uniform int shadow_count;
uniform vec3 shadow_right,shadow_up,shadow_axis,shadow_center0,shadow_center1;
uniform vec2 shadow_extent;
uniform float shadow_depth,shadow_bias,shadow_texel;
vec3 shadow_coord(vec3 p,vec3 center,float extent){
 vec3 d=p-center;
 return vec3(dot(d,shadow_right)/extent,dot(d,shadow_up)/extent,-dot(d,shadow_axis)/shadow_depth)*.5+.5;
}
bool shadow_inside(vec3 q){return all(greaterThan(q,vec3(0.0)))&&all(lessThan(q,vec3(1.0)));}
float shadow_tap(sampler2D map,vec3 q,float bias,bool soft){
 if(!shadow_inside(q))return 1.0;
 if(!soft)return step(q.z-bias,texture(map,q.xy).r);
 float sum=0.0;
 for(int y=-1;y<=1;y++)for(int x=-1;x<=1;x++){
   vec2 uv=q.xy+vec2(x,y)*shadow_texel;
   sum+=any(lessThan(uv,vec2(0)))||any(greaterThan(uv,vec2(1)))?1.0:step(q.z-bias,texture(map,uv).r);
 }
 return sum/9.0;
}
float sun_visibility(vec3 p,float slope,bool soft){
 if(shadow_count==0)return 1.0;
 float bias=shadow_bias*(1.0+2.0*slope);
 vec3 a=shadow_coord(p,shadow_center0,shadow_extent.x);
 if(shadow_count==1)return shadow_tap(shadow_near,a,bias,soft);
 vec3 b=shadow_coord(p,shadow_center1,shadow_extent.y);
 float farv=shadow_tap(shadow_far,b,bias,soft);
 if(!shadow_inside(a))return farv;
 float edge=max(abs(a.x-.5),abs(a.y-.5))*2.0;
 return mix(shadow_tap(shadow_near,a,bias,soft),farv,smoothstep(.8,.98,edge));
}
"""
VERTEX="""#version 330
in vec3 pos;in vec2 uv;in vec3 origin;in vec2 rotation;in float scale;
uniform vec3 center,rightv,upv,axis;
uniform float extent,depth_range;
out vec2 texcoord;
void main(){
 mat3 r=mat3(rotation.x,rotation.y,0,-rotation.y,rotation.x,0,0,0,1);
 vec3 d=origin+r*pos*scale-center;
 gl_Position=vec4(dot(d,rightv)/extent,dot(d,upv)/extent,-dot(d,axis)/depth_range,1);
 texcoord=uv;
}"""
FRAGMENT="""#version 330
in vec2 texcoord;
uniform sampler2D albedo;
uniform float alpha_cut;
void main(){if(texture(albedo,texcoord).a<alpha_cut)discard;}"""

def frames(center,direction,extent,resolution,count):
    n=unit(direction);ref=(0,0,1) if abs(n[2])<.99 else (0,1,0)
    r=unit(cross(n,ref));u=cross(r,n)
    sizes=(extent,) if count==1 else (extent*.35,extent)
    return r,u,n,[(snap_center(center,n,e,resolution),e) for e in sizes]

class ShadowMaps:
    def __init__(self,renderer):
        self.renderer=renderer;self.ctx=renderer.ctx
        self.program=self.ctx.program(vertex_shader=VERTEX,fragment_shader=FRAGMENT)
        self.program["albedo"].value=0
        self.targets=[];self.key=None;self.state=None
    def resize(self,size,count):
        if self.key==(size,count):return
        self.release_targets()
        for _ in range(count):
            tex=self.ctx.depth_texture((size,size))
            tex.compare_func="";tex.filter=(self.renderer.gl.NEAREST,)*2;tex.repeat_x=False;tex.repeat_y=False
            self.targets.append((tex,self.ctx.framebuffer(depth_attachment=tex)))
        self.key=(size,count)
    def render(self,scene,center,settings,effects,materials):
        from .gpu_viewport import default_material,variants,lod_index,length
        from math import radians,cos,sin
        from array import array
        r,u,n,views=frames(center,settings.light,effects.shadow_extent,effects.shadow_size,effects.shadow_cascades)
        self.resize(effects.shadow_size,len(views));depth_range=effects.shadow_extent*2
        p=self.program
        for i,(anchor,extent) in enumerate(views):
            tex,fbo=self.targets[i];fbo.use();fbo.clear(depth=1.)
            self.ctx.viewport=(0,0,effects.shadow_size,effects.shadow_size)
            self.ctx.enable_only(self.renderer.gl.DEPTH_TEST);self.ctx.depth_func="<"
            for key,value in dict(center=anchor,rightv=r,upv=u,axis=n,extent=extent,depth_range=depth_range).items():p[key].value=value
            batches={}
            for item in scene.instances:
                meshes=[scene.assets[item.asset],*variants(scene,item.asset)]
                delta=tuple(v-a for v,a in zip((item.x,item.y,item.z),anchor))
                rad=max(self.renderer.radius(m) for m in meshes if m is not None)*item.scale
                if abs(dot(delta,r))>extent+rad or abs(dot(delta,u))>extent+rad or abs(dot(delta,n))>depth_range+rad:continue
                lod=lod_index(length(delta),settings.lod_distances)
                while meshes[lod] is None:lod-=1
                m=meshes[lod];a=radians(item.yaw)
                batches.setdefault(id(m),(m,[]))[1].extend((item.x,item.y,item.z,cos(a),sin(a),item.scale,0,0,0,0))
            for mesh,rows in batches.values():
                vbo,parts,_=self.renderer.mesh(mesh)
                self.renderer.instance_buffer.write(array("f",rows).tobytes())
                for name,ibo,_,count in parts:
                    mat=materials.get(name,default_material(name)).validate()
                    self.renderer.texture(mat.diffuse or self.renderer.white).use(0);p["alpha_cut"].value=mat.cutout
                    vao=self.ctx.vertex_array(p,[(vbo,"3f 12x 2f","pos","uv"),(self.renderer.instance_buffer,"3f 2f 1f 16x /i","origin","rotation","scale")],ibo,index_element_size=4)
                    try:vao.render(self.renderer.gl.TRIANGLES,instances=len(rows)//10)
                    finally:vao.release()
        a,e=views[0];b,f=views[-1]
        self.state=dict(shadow_count=len(views),shadow_right=r,shadow_up=u,shadow_axis=n,shadow_center0=a,shadow_center1=b,shadow_extent=(e,f),shadow_depth=depth_range,shadow_bias=effects.shadow_bias,shadow_texel=1/effects.shadow_size)
    def bind(self,program,enabled):
        program["shadow_count"].value=len(self.targets) if enabled and self.state else 0
        program["shadow_near"].value=3;program["shadow_far"].value=4
        if not enabled or not self.state:return
        for key,value in self.state.items():
            if key in program:program[key].value=value
        self.targets[0][0].use(3);self.targets[-1][0].use(4)
    def release_targets(self):
        for tex,fbo in self.targets:fbo.release();tex.release()
        self.targets=[];self.key=None;self.state=None
    def close(self):
        self.release_targets();self.program.release()

def bind(program,maps,enabled):
    if maps is not None:maps.bind(program,enabled)
    else:
        program["shadow_count"].value=0
        program["shadow_near"].value=3;program["shadow_far"].value=4
