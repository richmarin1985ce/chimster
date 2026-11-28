"""Dependency-free synthetic LOD macro geometry benchmark (not game FPS)."""
import time,tracemalloc
from .world_lod_builtin import macro_mesh
from .world_lod_metadata import dirty_tiles
from .fnv_lod_nif import encode,check

def run(side=16):
    if type(side)!=int or not 1<=side<=32:raise ValueError("Benchmark side must be 1–32 cells")
    # Adjacent cell boundaries are continuous by construction.
    tracemalloc.start()
    start=time.perf_counter()
    try:
        grids={(x,y):[[float((x*32+i)+(y*32+j)*2) for i in range(33)] for j in range(33)] for y in range(side) for x in range(side)}
        plan=dirty_tiles(grids)
        setup=time.perf_counter()-start
        rows=[]
        for level,tiles in plan.items():
            before=time.perf_counter();triangles=vertices=bytes_written=0
            for x,y in tiles:
                local={(cx,cy):grids[cx,cy] for cx in range(x,x+level) for cy in range(y,y+level) if (cx,cy) in grids}
                mesh=macro_mesh(local,x,y,level,skirts=256,stitch=True)
                raw=encode(mesh,"textures/chimster/benchmark.dds","textures/chimster/benchmark_n.dds")
                info=check(raw,len(mesh.faces))
                triangles+=info["triangles"];vertices+=info["vertices"];bytes_written+=len(raw)
            rows.append({"level":level,"tiles":len(tiles),"triangles":triangles,"vertices":vertices,"bytes":bytes_written,"seconds":time.perf_counter()-before})
        _,peak=tracemalloc.get_traced_memory()
        return {"cells":side*side,"setup_seconds":setup,"elapsed_seconds":time.perf_counter()-start,"peak_python_bytes":peak,"tiers":rows,"external_tools":False,"scope":"Synthetic geometry and serialization only; no textures, game runtime or GPU performance"}
    finally:tracemalloc.stop()
