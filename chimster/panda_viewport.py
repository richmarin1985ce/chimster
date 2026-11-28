"""Optional Panda3D scene adapter; no Panda dependency at import time."""
def build_scene(scene):
    from panda3d.core import (NodePath, GeomNode, Geom, GeomTriangles,
        GeomVertexData, GeomVertexFormat, GeomVertexWriter)
    from .gpu_viewport import vertex_data, default_material
    root=NodePath("chimster")
    assets={}
    for key in {i.asset for i in scene.instances}:
        raw,groups=vertex_data(scene.assets[key])
        data=GeomVertexData(key,GeomVertexFormat.get_v3n3t2(),Geom.UH_static)
        data.set_num_rows(len(raw)//8)
        pos=GeomVertexWriter(data,"vertex")
        norm=GeomVertexWriter(data,"normal")
        uv=GeomVertexWriter(data,"texcoord")
        for j in range(0,len(raw),8):
            pos.add_data3f(*raw[j:j+3]);norm.add_data3f(*raw[j+3:j+6]);uv.add_data2f(*raw[j+6:j+8])
        template=NodePath(key)
        for material,indices in groups.items():
            triangles=GeomTriangles(Geom.UH_static)
            for j in range(0,len(indices),3):
                triangles.add_vertices(*indices[j:j+3])
            geom=Geom(data);geom.add_primitive(triangles)
            node=GeomNode(material);node.add_geom(geom)
            part=template.attach_new_node(node)
            part.set_color(*default_material(material).tint,1)
            part.set_two_sided(True)
        assets[key]=template
    for i in scene.instances:
        node=root.attach_new_node(i.id)
        assets[i.asset].instance_to(node)
        node.set_pos(i.x,i.y,i.z);node.set_h(i.yaw);node.set_scale(i.scale)
        node.set_tag("chimster_id",i.id)
    return root
