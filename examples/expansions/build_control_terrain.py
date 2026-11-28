"""Build portable OBJ and elevation grid from a committed procedural control map.
Interpolation adds samples, not measured or newly modeled terrain detail.
"""
import argparse
import hashlib
import json
import math
from pathlib import Path

def build(data, samples=513):
    if data.get("schema")!="chimster.procedural-terrain-control.v1":
        raise ValueError("unsupported control map")
    n=data["samples"]; rows=data["elevation_m"]; extent=data["extent_m"]
    if n!=129 or len(rows)!=n or data["row_order"]!="south-to-north" or data["units"]!="meters" or extent!=8192:
        raise ValueError("unexpected source grid")
    if any(len(r)!=n or any(not isinstance(z,(int,float)) or isinstance(z,bool) or not math.isfinite(z) for z in r) for r in rows):
        raise ValueError("invalid source heights")
    if samples not in (129,257,513): raise ValueError("unsupported output sample count")
    ratio=(n-1)/(samples-1)
    grid=[]
    for y in range(samples):
        v=y*ratio;j=min(int(v),n-2);fy=v-j
        row=[]
        for x in range(samples):
            u=x*ratio;i=min(int(u),n-2);fx=u-i
            z=(rows[j][i]*(1-fx)+rows[j][i+1]*fx)*(1-fy)+(rows[j+1][i]*(1-fx)+rows[j+1][i+1]*fx)*fy
            row.append(round(z,4))
        grid.append(row)
    return grid

def export(source,out,samples):
    raw=source.read_bytes(); data=json.loads(raw); grid=build(data,samples)
    out.mkdir(parents=True,exist_ok=False)
    step=data["extent_m"]/(samples-1)
    with (out/"elevation-meters.json").open("x",encoding="utf-8") as f:
        json.dump(grid,f,separators=(",",":"),allow_nan=False)
    with (out/"terrain.obj").open("x",encoding="ascii") as f:
        f.write("# Portable control terrain; meters, +Y north, +Z up\n")
        for y,row in enumerate(grid):
            for x,z in enumerate(row): f.write(f"v {x*step:.4f} {y*step:.4f} {z:.4f}\n")
        for y in range(samples-1):
            for x in range(samples-1):
                a=y*samples+x+1;b=a+1;c=a+samples;d=c+1
                f.write(f"f {a} {b} {d}\nf {a} {d} {c}\n")
    manifest={"project":data["project"],"source_sha256":hashlib.sha256(raw).hexdigest(),
        "samples":samples,"spacing_m":step,"vertices":samples*samples,
        "triangles":2*(samples-1)**2,"row_order":"south-to-north",
        "water_level_m":data["water_level_m"],"status":"portable interpolated terrain; no native plugin, water mesh, detailed landscaping or engine validation"}
    with (out/"manifest.json").open("x",encoding="utf-8") as f:
        json.dump(manifest,f,indent=2);f.write("\n")

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("source",type=Path);p.add_argument("output",type=Path)
    p.add_argument("--samples",type=int,default=513,choices=(129,257,513))
    a=p.parse_args();export(a.source,a.output,a.samples)

if __name__=="__main__": main()
