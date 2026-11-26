"""Original procedural flora to native NIF package.
No Bethesda assets or SpeedTree data. Model paths are candidates, not LOD records."""
from pathlib import Path
from random import Random
from math import sin,pi
import json,shutil,tempfile
from .flora import Recipe,generate,Mesh
from .lod import atlas_billboard
from .lod_assets import write_dds
from .textures import normal_map,mip_dds
from .modern_nif import export,GAMES

def material_images(seed,size=64):
    if not 8<=size<=256:raise ValueError("invalid material size")
    rng=Random(seed);bark=bytearray();height=bytearray();leaf=bytearray()
    for y in range(size):
        for x in range(size):
            # Repeating broad and fine bark ridges.
            ridge=.5+.25*sin(x*2*pi*8/size)+.15*sin(x*2*pi*19/size+.4*sin(y*2*pi/size))
            ridge=max(0,min(1,ridge+rng.uniform(-.08,.08)))
            height.append(round(ridge*255))
            bark.extend((round(65+65*ridge),round(43+46*ridge),round(26+30*ridge),255))
            u=2*(x+.5)/size-1;v=2*(y+.5)/size-1
            # Tapered leaf card with a central vein; deliberately stylized.
            cover=abs(u)<.64*(1-v*v) and abs(v)<.96
            vein=max(0,1-abs(u)*12)
            leaf.extend((round(48+25*vein),round(100+35*vein),round(36+10*vein),255 if cover else 0))
    return bytes(bark),normal_map(size,size,bytes(height),strength=3,wrap=True),bytes(leaf)

def two_sided(mesh):
    # Duplicate vertices, not shared opposite normals.
    out=Mesh(list(mesh.vertices),list(mesh.uv),list(mesh.faces))
    mapping={}
    for tri,mat in mesh.faces:
        if not mat.endswith("__cutout"):continue
        ids=[]
        for i in reversed(tri):
            if i not in mapping:
                mapping[i]=len(out.vertices);out.vertices.append(mesh.vertices[i]);out.uv.append(mesh.uv[i])
            ids.append(mapping[i])
        out.faces.append((tuple(ids),mat))
    return out

def build_native_flora(recipe,game,output,helper,scale=1,size=64):
    if game not in GAMES:raise ValueError("unsupported game")
    if recipe.bark!="bark" or recipe.foliage!="leaves":raise ValueError("default material IDs required")
    out=Path(output).resolve()
    if out.exists():raise FileExistsError(out)
    if not out.parent.is_dir():raise ValueError("output parent must exist")
    stage=Path(tempfile.mkdtemp(prefix=".flora-build-",dir=out.parent))
    try:
        tex=stage/"textures"/"chimster";meshes=stage/"meshes"/"chimster"
        tex.mkdir(parents=True);meshes.mkdir(parents=True)
        bark,normal,leaf=material_images(recipe.seed,size)
        for name,raw,isnormal in (("bark.dds",bark,False),("bark_n.dds",normal,True)):
            (tex/name).write_bytes(mip_dds(size,size,raw,normal=isnormal))
        # Preserve original cutout alpha, without claiming mip alpha coverage.
        write_dds(tex/"leaves.dds",size,size,leaf)
        flat=bytes((128,128,255,255))*size*size
        write_dds(tex/"leaves_n.dds",size,size,flat)
        base={"bark__opaque":{"diffuse":"textures/chimster/bark.dds","normal":"textures/chimster/bark_n.dds"},
              "leaves__cutout":{"diffuse":"textures/chimster/leaves.dds","normal":"textures/chimster/leaves_n.dds","cutout":True}}
        reports=[]
        for level in range(3):
            m=two_sided(generate(recipe,level));mats={k:v for k,v in base.items() if k in {mat for _,mat in m.faces}}
            p=meshes/f"flora_lod{level}.nif"
            report=export(m,game,p,helper,mats,scale)
            reports.append({**report,"output":p.relative_to(stage).as_posix()})
        proxy,rgba,side,layout=atlas_billboard(generate(recipe),2,size)
        proxy.uv=[(u,1-v) for u,v in proxy.uv]
        write_dds(tex/"flora_billboard.dds",side,side,rgba)
        p=meshes/"flora_lod3.nif"
        report=export(two_sided(proxy),game,p,helper,{"tree_atlas__cutout":{"diffuse":"textures/chimster/flora_billboard.dds","cutout":True}},scale)
        reports.append({**report,"output":p.relative_to(stage).as_posix()})
        result={"game":game,"recipe":vars(recipe),"scale":scale,"lods":reports,"atlas_size":side,
          "warning":"Original stylized textures, flat-color billboard bake; no game-native tree/object LOD records, collision or in-game verification. FO4 material assignment not verified."}
        (stage/"manifest.json").write_text(json.dumps(result,indent=2)+"\n",encoding="utf-8")
        if out.exists():raise FileExistsError(out)
        stage.rename(out)
        return result
    finally:
        if stage.exists():shutil.rmtree(stage)
