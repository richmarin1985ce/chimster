"""Matched software/hardware GL runs, separating instancing and hierarchical culling."""
from dataclasses import replace
from statistics import median
from math import ceil,sqrt
from .gpu_viewport import Renderer,Settings,make_demo
from .scene import Scene,Instance,Camera

def forest(count):
    if not isinstance(count,int) or not 1<=count<=5000:raise ValueError("count must be 1..5000")
    s,materials=make_demo()
    side=ceil(sqrt(count))
    instances=[Instance(f"tree-{i}","tree",(i%side-side/2)*5,(i//side-side/2)*5,0,(i*37)%360,.8+(i%5)*.08) for i in range(count)]
    return Scene(s.assets,instances),materials

def benchmark(count=2500,frames=5,backend="egl"):
    if not isinstance(frames,int) or not 1<=frames<=50:raise ValueError("frames must be 1..50")
    scene,materials=forest(count);r=Renderer(backend)
    cam=Camera(yaw=35,pitch=32,zoom=4)
    settings=Settings(lod_distances=(25,50,100))
    result={}
    try:
        for label,opt in [("baseline",replace(settings,instancing=False,hierarchy=False)),("instanced",replace(settings,hierarchy=False)),("instanced_hierarchy",settings)]:
            # Same context, scene, camera, material and resolution; one warmup per mode.
            r.render(scene,cam,640,480,materials,opt)
            times=[]
            for _ in range(frames):
                _,stats=r.render(scene,cam,640,480,materials,opt);times.append(stats["frame_ms"])
            result[label]={**stats,"median_frame_ms":median(times),"samples_ms":times}
        for metric in ("visible","culled","triangles","lod_counts"):
            if len({str(v[metric]) for v in result.values()})!=1:raise ValueError("benchmark visibility mismatch")
        return {"count":count,"frames_per_mode":frames,"resolution":[640,480],"modes":result,"warning":"Includes readback; environment-specific synthetic preview, not in-game FPS. Warmed cache, sequential runs."}
    finally:r.close()
