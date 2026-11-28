"""Explicit opt-in visibility preview; portable layouts, not native geometry."""
from .interior_layout import validate,bounds,contains
from .portal_clip import visible,ordered

class Visibility:
    def __init__(self,root,layout,membership):
        if not validate(layout)["valid"]:raise ValueError("Invalid layout")
        self.root=root;self.layout=layout
        self.rooms={r["id"]:bounds(r) for r in layout["rooms"]}
        self.nodes={k:root.attach_new_node("room:"+k) for k in self.rooms}
        self.occluders=[]
        for child in list(root.get_children()):
            if not child.has_tag("chimster_id"):continue
            room=membership.get(child.get_tag("chimster_id"))
            if room in self.nodes:child.wrt_reparent_to(self.nodes[room])
    def update(self,eye,enabled=True,closed=()):
        matches=[k for k,b in self.rooms.items() if contains(b,eye)]
        allowed=set(self.rooms)
        if enabled and len(matches)==1:
            allowed=set(visible(self.layout,matches[0],eye,closed=closed)["visible_candidates"])
        for k,node in self.nodes.items():
            if k in allowed:node.show()
            else:node.hide()
        return sorted(allowed)
    def add_occluder(self,corners):
        from panda3d.core import OccluderNode,Point3
        from .interior_layout import point
        from .portal_clip import cross,sub,dot
        from math import sqrt
        p=[point(v) for v in corners]
        if len(p)!=4 or len(set(p))!=4:raise ValueError("Expected rectangle")
        a,b,c,d=p
        u,v=sub(b,a),sub(d,a)
        if abs(dot(u,v))>1e-6*sqrt(dot(u,u)*dot(v,v)) or any(abs(c[i]-b[i]-d[i]+a[i])>1e-6 for i in range(3)):raise ValueError("Expected ordered rectangle")
        n=OccluderNode("chimster-occluder");n.set_vertices(*(Point3(*v) for v in p));n.set_double_sided(True)
        node=self.root.attach_new_node(n);self.occluders.append(node)
        return node
    def enable_occlusion(self,enabled):
        for node in self.occluders:
            if enabled:self.root.set_occluder(node)
            else:self.root.clear_occluder(node)
