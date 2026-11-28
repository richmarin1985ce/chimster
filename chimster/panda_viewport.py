"""Optional Panda3D scene adapter; no Panda dependency at import time."""
from math import inf

def lod_ranges(available, distances):
    """Coalesce missing tiers using the closest available finer mesh."""
    if len(available)!=4 or not available[0]:
        raise ValueError("Base LOD is required")
    if len(distances)!=3 or not 0<distances[0]<distances[1]<distances[2]<inf:
        raise ValueError("Invalid LOD distances")
    edges=(0,*distances,inf)
    active=0
    near=0
    result=[]
    for tier in range(1,4):
        if available[tier]:
            result.append((active,near,edges[tier]))
            active=tier
            near=edges[tier]
    result.append((active,near,inf))
    return result


def texture_bytes(image):
    """Panda RAM texture rows start at the bottom, like the ModernGL path."""
    image.validate()
    stride=image.width*4
    return b"".join(image.rgba[y:y+stride] for y in range((image.height-1)*stride,-1,-stride))


def build_scene(scene, materials=None, settings=None):
    from panda3d.core import (NodePath, GeomNode, Geom, GeomTriangles,
        GeomVertexData, GeomVertexFormat, GeomVertexWriter, Texture,
        SamplerState, AlphaTestAttrib, LODNode)
    from .gpu_viewport import vertex_data, default_material, variants, Settings
    settings=(settings or Settings()).validate()
    materials=dict(materials or {})
    root=NodePath("chimster")
    assets={}
    textures={}
    def texture(image):
        key=id(image)
        if key not in textures:
            tex=Texture("chimster-diffuse")
            tex.setup_2d_texture(image.width,image.height,Texture.T_unsigned_byte,Texture.F_rgba8)
            tex.set_ram_image_as(texture_bytes(image),"RGBA")
            tex.set_minfilter(SamplerState.FT_linear)
            tex.set_magfilter(SamplerState.FT_linear)
            textures[key]=tex
        return textures[key]
    def template(key,mesh):
        raw,groups=vertex_data(mesh)
        data=GeomVertexData(key,GeomVertexFormat.get_v3n3t2(),Geom.UH_static)
        data.set_num_rows(len(raw)//8)
        pos=GeomVertexWriter(data,"vertex")
        norm=GeomVertexWriter(data,"normal")
        uv=GeomVertexWriter(data,"texcoord")
        for j in range(0,len(raw),8):
            pos.add_data3f(*raw[j:j+3]);norm.add_data3f(*raw[j+3:j+6]);uv.add_data2f(*raw[j+6:j+8])
        model=NodePath(key)
        for material,indices in groups.items():
            triangles=GeomTriangles(Geom.UH_static)
            for j in range(0,len(indices),3):
                triangles.add_vertices(*indices[j:j+3])
            geom=Geom(data);geom.add_primitive(triangles)
            node=GeomNode(material);node.add_geom(geom)
            part=model.attach_new_node(node)
            mat=materials.get(material,default_material(material)).validate()
            part.set_color_scale(*mat.tint,1)
            if mat.diffuse is not None:
                part.set_texture(texture(mat.diffuse),1)
            if mat.cutout>0:
                part.set_attrib(AlphaTestAttrib.make(AlphaTestAttrib.M_greater_equal,mat.cutout))
            part.set_two_sided(True)
        return model
    for key in sorted({i.asset for i in scene.instances}):
        options=[scene.assets[key],*variants(scene,key)]
        models={tier:template(f"{key}:{tier}",mesh) for tier,mesh in enumerate(options) if mesh is not None}
        assets[key]=(models,lod_ranges([m is not None for m in options],settings.lod_distances))
    for i in scene.instances:
        node=root.attach_new_node(i.id)
        node.set_pos(i.x,i.y,i.z);node.set_h(i.yaw)
        node.set_tag("chimster_id",i.id)
        models,ranges=assets[i.asset]
        if len(ranges)==1:
            target=node.attach_new_node("mesh")
            target.set_scale(i.scale)
            models[0].instance_to(target)
        else:
            lod=LODNode("distance-lod")
            lodpath=node.attach_new_node(lod)
            for tier,near,far in ranges:
                # Keep distance switches in world units by scaling the mesh child,
                # not the LOD node. A finite far limit exceeds valid scene bounds.
                target=lodpath.attach_new_node(f"tier:{tier}")
                target.set_scale(i.scale)
                models[tier].instance_to(target)
                lod.add_switch(1e9 if far==inf else far,near)
    return root


class Preview:
    """Offscreen engine preview; owns its buffer, no separate application."""
    def __init__(self):
        from panda3d.core import GraphicsEngine, GraphicsPipeSelection, NodePath
        self.engine=GraphicsEngine()
        self.pipe=GraphicsPipeSelection.get_global_ptr().make_default_pipe()
        if self.pipe is None: raise RuntimeError("No Panda3D graphics pipe")
        self.root=NodePath("preview")
        self.model=None; self.key=None; self.output=None
        self.visibility=None;self.visibility_spec=None;self.visibility_report=None
        from panda3d.core import Camera, PerspectiveLens, AmbientLight, DirectionalLight
        self.lens=PerspectiveLens()
        self.camera=self.root.attach_new_node(Camera("camera",self.lens))
        ambient=AmbientLight("ambient");ambient.set_color((.35,.35,.35,1))
        sun=DirectionalLight("sun");sun.set_color((.8,.8,.8,1))
        a=self.root.attach_new_node(ambient);s=self.root.attach_new_node(sun)
        s.set_hpr(-35,-50,0);self.root.set_light(a);self.root.set_light(s)
    def configure_visibility(self,layout=None,membership=None,occluders=()):
        from copy import deepcopy
        self.visibility_spec=deepcopy((layout,membership or {},tuple(occluders))) if layout is not None else None
        self.key=None
    def render(self,scene,camera,w,h,materials=None,settings=None):
        from panda3d.core import FrameBufferProperties,WindowProperties,GraphicsPipe,Texture,GraphicsOutput
        from .gpu_viewport import basis,Settings
        settings=(settings or Settings()).validate()
        materials=dict(materials or {})
        if not 1<=w<=1280 or not 1<=h<=720:raise ValueError("preview size exceeds limit")
        if self.output is None or (self.output.get_x_size(),self.output.get_y_size())!=(w,h):
            self.close_buffer()
            fb=FrameBufferProperties();fb.set_rgb_color(True);fb.set_depth_bits(24)
            self.output=self.engine.make_output(self.pipe,"chimster",0,fb,WindowProperties.size(w,h),GraphicsPipe.BF_refuse_window)
            if self.output is None:raise RuntimeError("Offscreen graphics unavailable")
            self.texture=Texture()
            self.output.add_render_texture(self.texture,GraphicsOutput.RTM_copy_ram,GraphicsOutput.RTP_color)
            region=self.output.make_display_region();region.set_camera(self.camera)
            self.output.set_clear_color((.09,.12,.16,1));self.output.set_clear_color_active(True)
        key=(scene.instances,tuple(sorted((k,id(m)) for k,m in scene.assets.items())),tuple(sorted(materials.items())),settings)
        if key!=self.key:
            candidate=build_scene(scene,materials,settings)
            visibility=None
            if self.visibility_spec is not None:
                from .panda_visibility import Visibility
                layout,membership,occluders=self.visibility_spec
                visibility=Visibility(candidate,layout,membership)
                for corners in occluders:visibility.add_occluder(corners)
                visibility.enable_occlusion(True)
            self.visibility=visibility
            if self.model is not None:self.model.remove_node()
            self.model=candidate;self.model.reparent_to(self.root);self.key=key
        eye,_,_,_,_,_=basis(camera,w,h,settings)
        self.lens.set_aspect_ratio(w/h);self.lens.set_fov(settings.fov);self.lens.set_near_far(settings.near,settings.far)
        self.visibility_report=self.visibility.update(eye) if self.visibility is not None else None
        self.camera.set_pos(*eye);self.camera.look_at(*camera.center)
        self.engine.render_frame();self.engine.sync_frame()
        raw=bytes(self.texture.get_ram_image_as("RGBA"))
        if len(raw)!=w*h*4:raise RuntimeError("Incomplete framebuffer")
        stride=w*4
        return b"".join(raw[y:y+stride] for y in range((h-1)*stride,-1,-stride))
    def close_buffer(self):
        if self.output is not None:
            self.engine.remove_window(self.output);self.output=None
    def close(self):
        self.close_buffer();self.root.remove_node()
