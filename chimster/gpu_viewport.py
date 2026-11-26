"""Optional OpenGL 3.3 preview using ModernGL. Original MIT code.
No engine assets, renderer or GL dependency required by the CPU fallback."""
from dataclasses import dataclass
from math import sin,cos,radians,sqrt,tan,isfinite
from array import array
from time import perf_counter
from .flora import cross
from .lod import validate_mesh

VERTEX="""#version 330
in vec3 pos; in vec3 norm; in vec2 uv;
uniform vec3 origin, eye, rightv, upv, backv;
uniform vec2 rotation, projection;
uniform float scale, nearp, farp;
out vec3 world, normal; out vec2 texcoord;
void main(){
 mat3 r=mat3(rotation.x,rotation.y,0,-rotation.y,rotation.x,0,0,0,1);
 world=origin+r*pos*scale; normal=r*norm; texcoord=uv;
 vec3 d=world-eye; float z=-dot(d,backv);
 gl_Position=vec4(dot(d,rightv)*projection.x,dot(d,upv)*projection.y,
 (farp+nearp)/(farp-nearp)*z-2.0*farp*nearp/(farp-nearp),z);
}"""
FRAGMENT="""#version 330
in vec3 world, normal; in vec2 texcoord;
uniform sampler2D albedo, normalmap, specmap;
uniform vec3 eye, tint, sun;
uniform float alpha_cut, normal_strength, normal_y, spec_strength, selected, gloss;
uniform vec3 object_id;
layout(location=0) out vec4 color;
layout(location=1) out vec4 picking;
void main(){
 vec4 a=texture(albedo,texcoord);
 if(a.a<alpha_cut) discard;
 vec3 n=normalize(normal)*(gl_FrontFacing?1.0:-1.0);
 // Cotangent frame from derivatives; skip degenerate UVs.
 vec3 dp1=dFdx(world),dp2=dFdy(world);
 vec2 du1=dFdx(texcoord),du2=dFdy(texcoord);
 float det=du1.x*du2.y-du1.y*du2.x;
 if(abs(det)>1e-9 && normal_strength>0.0){
   vec3 t=(dp1*du2.y-dp2*du1.y)/det;
   vec3 b=(-dp1*du2.x+dp2*du1.x)/det;
   t=t-n*dot(n,t);
   if(dot(t,t)>1e-10 && dot(b,b)>1e-10){
     t=normalize(t);
     vec3 bt=normalize(cross(n,t))*sign(dot(cross(n,t),b));
     vec3 map=texture(normalmap,texcoord).rgb*2.0-1.0;
     map.xy*=vec2(normal_strength,normal_strength*normal_y);
     n=normalize(mat3(t,bt,n)*map);
   }
 }
 vec3 l=normalize(sun), v=normalize(eye-world);
 float diffuse=max(0.0,dot(n,l));
 float spec=pow(max(0.0,dot(n,normalize(l+v))),gloss)*texture(specmap,texcoord).r*spec_strength;
 vec3 base=pow(max(a.rgb*tint,vec3(0)),vec3(2.2));
 vec3 lit=base*(0.28+0.72*diffuse)+vec3(spec*diffuse);
 color=vec4(mix(pow(clamp(lit,0.0,1.0),vec3(1.0/2.2)),vec3(1.0,0.72,0.22),selected*0.20),1);
 picking=vec4(object_id,1);
}"""

@dataclass(frozen=True)
class ImageMap:
    width:int
    height:int
    rgba:bytes
    def validate(self):
        if not 1<=self.width<=4096 or not 1<=self.height<=4096 or len(self.rgba)!=self.width*self.height*4:raise ValueError("invalid texture")
        return self

@dataclass(frozen=True)
class Material:
    diffuse:ImageMap=None
    normal:ImageMap=None
    specular:ImageMap=None
    tint:tuple=(1.,1.,1.)
    cutout:float=0.
    normal_strength:float=1.
    directx:bool=True
    spec_strength:float=.18
    gloss:float=24.
    def validate(self):
        for image in (self.diffuse,self.normal,self.specular):
            if image is not None:image.validate()
        if len(self.tint)!=3 or any(not isfinite(x) or not 0<=x<=1 for x in self.tint):raise ValueError("invalid tint")
        if not all(isfinite(v) for v in (self.cutout,self.normal_strength,self.spec_strength,self.gloss)) or not 0<=self.cutout<=1 or not 0<=self.normal_strength<=4 or not 0<=self.spec_strength<=1 or not 1<=self.gloss<=256:raise ValueError("invalid material")
        return self

def image_from_file(path):
    from PIL import Image
    with Image.open(path) as im:
        w,h=im.size
        if not 1<=w<=4096 or not 1<=h<=4096:raise ValueError("image exceeds viewport limit")
        return ImageMap(w,h,im.convert("RGBA").tobytes())

@dataclass(frozen=True)
class Settings:
    lod_distances:tuple=(22.,45.,90.)
    far:float=5000.
    near:float=.05
    fov:float=45.
    cull:bool=True
    light:tuple=(.3,.4,.866)
    def validate(self):
        if len(self.lod_distances)!=3 or not all(isfinite(x) and x>0 for x in self.lod_distances) or not self.lod_distances[0]<self.lod_distances[1]<self.lod_distances[2]:raise ValueError("LOD distances must increase")
        if not all(isfinite(x) for x in (self.far,self.near,self.fov)) or not 0<self.near<self.far<=1e7 or not 15<=self.fov<=100:raise ValueError("invalid camera settings")
        if len(self.light)!=3 or not all(isfinite(x) for x in self.light) or not any(self.light):raise ValueError("invalid sun direction")
        return self

def dot(a,b):return sum(x*y for x,y in zip(a,b))
def length(v):return sqrt(dot(v,v))
def basis(camera,w,h,settings):
    a,b=radians(camera.yaw),radians(camera.pitch)
    right=(cos(a),-sin(a),0);up=(-sin(a)*sin(b),-cos(a)*sin(b),cos(b))
    back=(sin(a)*cos(b),cos(a)*cos(b),sin(b))
    ty=tan(radians(settings.fov)/2);tx=ty*w/h
    distance=max(settings.near*2,h/(2*ty*max(.001,camera.zoom)))
    eye=tuple(camera.center[k]+back[k]*distance for k in range(3))
    return eye,right,up,back,tx,ty

def lod_index(distance,thresholds):
    return sum(distance>=t for t in thresholds)

def visible(center,radius,view,settings):
    eye,right,up,back,tx,ty=view
    d=tuple(center[k]-eye[k] for k in range(3));z=-dot(d,back)
    if z+radius<settings.near or z-radius>settings.far:return False
    return abs(dot(d,right))<=z*tx+radius*sqrt(1+tx*tx) and abs(dot(d,up))<=z*ty+radius*sqrt(1+ty*ty)

def variants(scene,asset):
    # Optional asset variants named base@lod1..3; base remains LOD 0.
    return [scene.assets.get(f"{asset}@lod{i}") for i in range(1,4)]

def default_material(name):
    if name=="bark__opaque":return Material(tint=(.57,.40,.24))
    if "leaf" in name or "terrain" in name or "billboard" in name:return Material(tint=(.42,.67,.36))
    return Material(tint=(.72,.74,.77))

def demo_materials(size=32):
    from .native_flora import material_images
    bark,normal,leaf=material_images(42,size)
    flat=ImageMap(1,1,bytes((128,128,255,255)))
    result={"bark__opaque":Material(ImageMap(size,size,bark),ImageMap(size,size,normal)),
            "leaves__cutout":Material(ImageMap(size,size,leaf),flat,cutout=.5,spec_strength=.06),
            "terrain__opaque":Material(tint=(.38,.48,.27),spec_strength=.02)}
    return result

def make_demo():
    from .scene import demo_scene
    from .flora import generate,Recipe
    from .lod import atlas_billboard
    s=demo_scene();r=Recipe();s.assets["tree"]=generate(r,0)
    s.assets["tree@lod1"]=generate(r,1);s.assets["tree@lod2"]=generate(r,2)
    mesh,rgba,side,_=atlas_billboard(s.assets["tree"],2,64)
    mesh.uv=[(u,1-v) for u,v in mesh.uv];s.assets["tree@lod3"]=mesh
    mats=demo_materials();mats["tree_atlas__cutout"]=Material(ImageMap(side,side,rgba),cutout=.5,spec_strength=0.)
    return s,mats

def vertex_data(mesh):
    validate_mesh(mesh);groups={};normals=[[0.,0.,0.] for _ in mesh.vertices]
    for tri,mat in mesh.faces:
        a,b,c=[mesh.vertices[i] for i in tri]
        n=cross(tuple(b[k]-a[k] for k in range(3)),tuple(c[k]-a[k] for k in range(3)))
        for i in tri:
            for k in range(3):normals[i][k]+=n[k]
        groups.setdefault(mat,[]).extend(tri)
    buf=array("f")
    for p,n,uv in zip(mesh.vertices,normals,mesh.uv):
        l=length(n);buf.extend((*p,*(tuple(x/l for x in n) if l>1e-12 else (0,0,1)),*uv))
    return buf,groups

class Renderer:
    def __init__(self,backend=None):
        import moderngl
        self.gl=moderngl
        if backend:self.ctx=moderngl.create_standalone_context(require=330,backend=backend)
        else:
            try:self.ctx=moderngl.create_standalone_context(require=330)
            except Exception:self.ctx=moderngl.create_standalone_context(require=330,backend="egl")
        self.program=self.ctx.program(vertex_shader=VERTEX,fragment_shader=FRAGMENT)
        self.program["albedo"].value=0;self.program["normalmap"].value=1;self.program["specmap"].value=2
        self.meshes={};self.textures={};self.targets=None;self.ids={};self.size=(0,0)
        self.white=ImageMap(1,1,b"\xff\xff\xff\xff");self.flat=ImageMap(1,1,bytes((128,128,255,255)))
    def mesh(self,m):
        key=id(m);entry=self.meshes.get(key)
        if entry is not None:return entry[1:]
        raw,groups=vertex_data(m);vbo=self.ctx.buffer(raw.tobytes());parts=[]
        for mat,indices in groups.items():
            ibo=self.ctx.buffer(array("I",indices).tobytes())
            vao=self.ctx.vertex_array(self.program,[(vbo,"3f 3f 2f","pos","norm","uv")],ibo,index_element_size=4)
            parts.append((mat,ibo,vao,len(indices)//3))
        radius=max(length(p) for p in m.vertices)
        self.meshes[key]=(m,vbo,parts,radius);return vbo,parts,radius
    def texture(self,img):
        key=id(img)
        if key in self.textures:return self.textures[key][1]
        img.validate();stride=img.width*4
        # Disk rows top-down; GL texture V=0 at bottom.
        data=b"".join(img.rgba[y:y+stride] for y in range((img.height-1)*stride,-1,-stride))
        t=self.ctx.texture((img.width,img.height),4,data,alignment=1)
        t.filter=(self.gl.LINEAR,self.gl.LINEAR)
        self.textures[key]=(img,t);return t
    def resize(self,w,h):
        if self.size==(w,h):return
        if self.targets:
            for obj in reversed(self.targets):obj.release()
        a=self.ctx.texture((w,h),4);b=self.ctx.texture((w,h),4)
        depth=self.ctx.depth_renderbuffer((w,h));fbo=self.ctx.framebuffer([a,b],depth)
        self.targets=(a,b,depth,fbo);self.size=(w,h)
    def prune(self,scene,materials):
        active={id(m) for m in scene.assets.values()}
        for key in list(self.meshes):
            if key not in active:
                _,vbo,parts,_=self.meshes.pop(key)
                for _,ibo,vao,_ in parts:vao.release();ibo.release()
                vbo.release()
        active_tex={id(self.white),id(self.flat)}
        for m in materials.values():
            active_tex.update(id(i) for i in (m.diffuse,m.normal,m.specular) if i is not None)
        for key in list(self.textures):
            if key not in active_tex:self.textures.pop(key)[1].release()
    def render(self,scene,camera,w,h,materials=None,settings=None,selected=None):
        start=perf_counter();settings=(settings or Settings()).validate();materials=materials or {}
        if not isinstance(w,int) or not isinstance(h,int) or not 1<=w<=1920 or not 1<=h<=1080:raise ValueError("viewport size out of range")
        self.prune(scene,materials);self.resize(w,h);a,b,depth,fbo=self.targets
        fbo.use();self.ctx.viewport=(0,0,w,h);self.ctx.enable_only(self.gl.DEPTH_TEST);self.ctx.depth_func="<"
        fbo.clear(0,0,0,0,depth=1.)
        view=basis(camera,w,h,settings);eye,right,up,back,tx,ty=view;p=self.program
        for key,value in {"eye":eye,"rightv":right,"upv":up,"backv":back,"projection":(1/tx,1/ty),"nearp":settings.near,"farp":settings.far,"sun":settings.light}.items():p[key].value=value
        self.ids={};stats={"objects":len(scene.instances),"visible":0,"culled":0,"triangles":0,"draw_calls":0,"lod_counts":[0]*4}
        for index,i in enumerate(scene.instances,1):
            base=scene.assets[i.asset];options=[base,*variants(scene,i.asset)]
            center=(i.x,i.y,i.z);distance=length(tuple(center[k]-eye[k] for k in range(3)))
            lod=lod_index(distance,settings.lod_distances)
            while options[lod] is None:lod-=1
            # Bound all variants, not only the selected geometry.
            radius=max(self.mesh(m)[2] for m in options if m is not None)*i.scale
            if settings.cull and not visible(center,radius,view,settings):
                stats["culled"]+=1;continue
            _,parts,_=self.mesh(options[lod]);stats["visible"]+=1;stats["lod_counts"][lod]+=1
            self.ids[index]=i.id;r=radians(i.yaw)
            p["origin"].value=center;p["rotation"].value=(cos(r),sin(r));p["scale"].value=i.scale
            p["object_id"].value=((index&255)/255,((index>>8)&255)/255,((index>>16)&255)/255)
            p["selected"].value=float(i.id==selected)
            for mat,_,vao,count in parts:
                m=materials.get(mat,default_material(mat)).validate()
                self.texture(m.diffuse or self.white).use(0);self.texture(m.normal or self.flat).use(1);self.texture(m.specular or self.white).use(2)
                for key,value in {"tint":m.tint,"alpha_cut":m.cutout,"normal_strength":m.normal_strength if m.normal else 0.,"normal_y":-1. if m.directx else 1.,"spec_strength":m.spec_strength,"gloss":m.gloss}.items():p[key].value=value
                vao.render(self.gl.TRIANGLES);stats["triangles"]+=count;stats["draw_calls"]+=1
        raw=a.read(alignment=1);stride=w*4
        raw=b"".join(raw[y:y+stride] for y in range((h-1)*stride,-1,-stride))
        stats["frame_ms"]=(perf_counter()-start)*1000;stats["renderer"]=self.ctx.info.get("GL_RENDERER","unknown")
        return raw,stats
    def pick(self,x,y):
        w,h=self.size
        if not self.targets or not 0<=x<w or not 0<=y<h:return None
        b=self.targets[-1].read(viewport=(int(x),h-1-int(y),1,1),attachment=1,components=4,alignment=1)
        return self.ids.get(b[0]|b[1]<<8|b[2]<<16)
    def close(self):
        for _,vbo,parts,_ in self.meshes.values():
            for _,ibo,vao,_ in parts:vao.release();ibo.release()
            vbo.release()
        for _,tex in self.textures.values():tex.release()
        if self.targets:
            for obj in reversed(self.targets):obj.release()
        self.meshes.clear();self.textures.clear();self.targets=None
        self.program.release();self.ctx.release()
