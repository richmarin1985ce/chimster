"""Deterministic rectangle packing and RGBA PNG atlas with edge extrusion.
Input images must already be compatible non-tiling textures. No DDS encoder."""
from dataclasses import dataclass
import struct,zlib
from pathlib import Path
@dataclass(frozen=True)
class Tile:
    name:str
    width:int
    height:int
    rgba:bytes

def pack(tiles, width=1024, height=1024, gutter=2):
    if not 1<=width<=4096 or not 1<=height<=4096 or not 1<=gutter<=16:raise ValueError("invalid atlas limits")
    if not tiles or len({t.name for t in tiles})!=len(tiles):raise ValueError("empty or duplicate tiles")
    ordered=sorted(tiles,key=lambda t:(-t.height,-t.width,t.name))
    x=y=row=0;pixels=bytearray(width*height*4);layout={}
    for t in ordered:
        w,h=t.width,t.height
        if w<=0 or h<=0 or len(t.rgba)!=w*h*4:raise ValueError("invalid tile")
        tw,th=w+2*gutter,h+2*gutter
        if tw>width or th>height:raise ValueError("tile exceeds atlas")
        if x+tw>width:x=0;y+=row;row=0
        if y+th>height:raise ValueError("atlas full")
        ox,oy=x+gutter,y+gutter
        for j in range(-gutter,h+gutter):
            sy=min(max(j,0),h-1)
            for i in range(-gutter,w+gutter):
                sx=min(max(i,0),w-1)
                src=4*(sy*w+sx);dst=4*((oy+j)*width+ox+i)
                pixels[dst:dst+4]=t.rgba[src:src+4]
        layout[t.name]={"x":ox,"y":oy,"width":w,"height":h,"u0":ox/width,"v0":oy/height,"u1":(ox+w)/width,"v1":(oy+h)/height}
        x+=tw;row=max(row,th)
    return bytes(pixels),layout

def remap_uv(u,v,rect):
    if not 0<=u<=1 or not 0<=v<=1:raise ValueError("tiling UV cannot be remapped")
    # Atlas coordinates have top-left origin; callers handle game-specific orientation.
    return rect["u0"]+u*(rect["u1"]-rect["u0"]),rect["v0"]+v*(rect["v1"]-rect["v0"])
def write_png(path,width,height,rgba):
    if not 1<=width<=4096 or not 1<=height<=4096 or len(rgba)!=width*height*4:raise ValueError("invalid RGBA")
    def chunk(kind,data):
        return struct.pack(">I",len(data))+kind+data+struct.pack(">I",zlib.crc32(kind+data)&0xffffffff)
    scanlines=b"".join(b"\0"+rgba[y*width*4:(y+1)*width*4] for y in range(height))
    data=b"\x89PNG\r\n\x1a\n"+chunk(b"IHDR",struct.pack(">IIBBBBB",width,height,8,6,0,0,0))+chunk(b"IDAT",zlib.compress(scanlines))+chunk(b"IEND",b"")
    with Path(path).open("xb") as f:f.write(data)
