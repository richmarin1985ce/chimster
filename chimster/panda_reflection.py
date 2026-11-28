"""Optional planar water reflection and refraction render targets."""
def mirror_point(p,z):
    return (p[0],p[1],2*z-p[2])

def mirror_vector(v):
    return (v[0],v[1],-v[2])

class WaterTargets:
    def __init__(self,preview,effects,w,h):
        from panda3d.core import Camera,BitMask32,NodePath,Plane,PlaneNode,Vec3,Point3
        self.preview=preview
        self.buffers=[];self.nodes=[];self.cameras={}
        self.level=effects.water_level
        width=min(w,effects.reflection_size)
        height=max(1,round(width*h/w))
        try:
            for name in ("reflection","refraction") if effects.refraction else ("reflection",):
                buf=preview.output.make_texture_buffer(name,width,height)
                if buf is None:raise RuntimeError("Water target unavailable")
                self.buffers.append(buf);buf.set_sort(-100+len(self.buffers))
                buf.set_clear_color((*effects.fog_color,1));buf.set_clear_color_active(True)
                camera=preview.root.attach_new_node(Camera(name,preview.lens))
                self.nodes.append(camera);self.cameras[name]=camera
                camera.node().set_scene(preview.root)
                camera.node().set_camera_mask(BitMask32.bit(2))
                side=1 if name=="reflection" else -1
                pn=PlaneNode(name+"-clip")
                pn.set_plane(Plane(Vec3(0,0,side),Point3(0,0,self.level)))
                plane=preview.root.attach_new_node(pn);self.nodes.append(plane)
                tmp=NodePath("clip-state");tmp.set_clip_plane(plane)
                camera.node().set_initial_state(tmp.get_state())
                region=buf.make_display_region();region.set_camera(camera)
                preview.water.set_shader_input(name+"_tex",buf.get_texture())
            preview.water.hide(BitMask32.bit(2))
            preview.water.set_shader_input("use_reflection",1.)
            preview.water.set_shader_input("use_refraction",float(effects.refraction))
        except Exception:
            self.close()
            raise
    def update(self,eye,center,up):
        from panda3d.core import Point3,Vec3
        cam=self.cameras["reflection"]
        cam.set_pos(*mirror_point(eye,self.level))
        cam.look_at(Point3(*mirror_point(center,self.level)),Vec3(*mirror_vector(up)))
        if "refraction" in self.cameras:
            cam=self.cameras["refraction"];cam.set_pos(*eye)
            cam.look_at(Point3(*center),Vec3(*up))
    def close(self):
        for b in self.buffers:self.preview.engine.remove_window(b)
        for n in self.nodes:n.remove_node()
        self.buffers.clear();self.nodes.clear();self.cameras.clear()
        if self.preview.water is not None:
            self.preview.water.set_shader_input("use_reflection",0.)
            self.preview.water.set_shader_input("use_refraction",0.)
