"""Bounded globally aligned AutoNav refinement; never mix incompatible grids."""
import math
from .navmesh import num,quality
from .navmesh_tiles import build
from .navmesh_areas import classify
from .navmesh_simplify import simplify

def refine(spec,*,levels=3,tile_cells=32,triangle_budget=250000,policy=None,previous=None):
    if type(levels) is not int or not 1<=levels<=5:raise ValueError("refinement levels must be 1–5")
    if type(triangle_budget) is not int or not 1<=triangle_budget<=1000000:raise ValueError("invalid triangle budget")
    base=num(spec["spacing"],.01,1e5)
    attempts=[];chosen=None
    for level in range(levels):
        spacing=base/(2**level)
        if spacing<.01:break
        candidate={**spec,"spacing":spacing}
        # Keep one grid per output; any finer trial replaces the entire candidate.
        try:
            prior=previous if previous and previous.get("settings",{}).get("spacing")==spacing else None
            bundle=build(candidate,prior,tile_cells)
        except ValueError as exc:
            if "limit" not in str(exc) and "budget" not in str(exc) and "halo too large" not in str(exc):raise
            attempts.append({"spacing":spacing,"status":"resource-limit","reason":str(exc)})
            break
        mesh=bundle["mesh"];raw=len(mesh["triangles"])
        if raw>triangle_budget:
            attempts.append({"spacing":spacing,"status":"triangle-budget","triangles":raw});break
        mesh=simplify(classify(mesh,policy))
        q=quality(mesh)
        attempts.append({"spacing":spacing,"status":"candidate","triangles":raw,"simplified":len(mesh["triangles"]),
                         "surface_area":q["surface_area"],"regions":len(mesh["regions"]),"seam_edges":mesh["seam_edges"]})
        if mesh["triangles"]:
            chosen={**bundle,"mesh":mesh,"spacing":spacing}
    if chosen is None:raise ValueError("no nonempty mesh within refinement budget")
    chosen["refinement"]={"attempts":attempts,"chosen_spacing":chosen["spacing"],
                          "scope":"global resolution trials with simplified planar interiors; not mixed-resolution tiling"}
    return chosen
