"""Bounded Starfield BTDB read-only terrain reader.

Starfield's zero-coordinate header layout, not Fallout 76's layout.
Vertical unit conversion is explicit: no unverified factor is assumed.
"""
import struct,zlib
from math import isfinite
from pathlib import Path
from collections import OrderedDict

class BTD:
    def __init__(self,data):
        if len(data)<44 or len(data)>128*1024*1024:raise ValueError("Invalid BTD size")
        self.data=data;self.cache=OrderedDict()
        magic,ver,low,high,rx,ry,x0,y0,x1,y1,nt=struct.unpack_from("<4sI2f2I4iI",data)
        if magic!=b"BTDB" or ver not in (5,6) or any((x0,y0,x1,y1)) or rx%128 or ry%128 or not 128<=rx<=131072 or not 128<=ry<=131072 or not isfinite(low) or not isfinite(high) or low>high or nt>65536:raise ValueError("Unsupported Starfield BTD header")
        self.nx=rx//128;self.ny=ry//128;self.low=low;self.high=high
        self.min_cell=(-rx//256,-ry//256)
        n=self.nx*self.ny
        self.height4=44+4*nt+40*n
        pos=self.height4+256*n;self.tables={}
        for l in (3,2,1,0):
            step=1<<l;w=(self.nx+step-1)//step;h=(self.ny+step-1)//step
            self.tables[l]=(pos,w,h);pos+=8*w*h
        if pos>len(data):raise ValueError("Truncated BTD tables")
        self.start=pos;self.textures=struct.unpack_from("<"+"I"*nt,data,44)
    @classmethod
    def load(cls,path):
        p=Path(path)
        if p.stat().st_size>128*1024*1024:raise ValueError("BTD preview budget exceeded")
        return cls(p.read_bytes())
    def block(self,x,y,l):
        pos,w,h=self.tables[l]
        if not 0<=x<w or not 0<=y<h:raise ValueError("BTD block outside extent")
        key=(x,y,l)
        if key not in self.cache:
            off,size=struct.unpack_from("<2I",self.data,pos+8*(y*w+x))
            a=self.start+off
            if not size or size>1024*1024 or a+size>len(self.data):raise ValueError("Invalid BTD block extent")
            z=zlib.decompressobj();raw=z.decompress(self.data[a:a+size],65537)
            if len(raw)!=65536 or not z.eof or z.unconsumed_tail or z.unused_data:raise ValueError("Invalid compressed BTD block")
            self.cache[key]=raw
            while len(self.cache)>16:self.cache.popitem(last=False)
        else:self.cache.move_to_end(key)
        return self.cache[key]
    def sample(self,x,y,l=0,texture=False):
        """Coordinates in samples from southwest, not native cell IDs."""
        if type(x) is not int or type(y) is not int or l not in (0,1,2,3,4) or not 0<=x<self.nx*128 or not 0<=y<self.ny*128:raise ValueError("BTD sample outside extent")
        if l==4:
            p=self.height4+(self.nx*self.ny*128 if texture else 0)+2*((y//16)*(self.nx*8)+x//16)
            return struct.unpack_from("<H",self.data,p)[0]
        step=1<<l;bx=x//(128*step);by=y//(128*step)
        sx=(x//step)%128;sy=(y//step)%128
        return struct.unpack_from("<H",self.block(bx,by,l),(32768 if texture else 0)+2*(sy*128+sx))[0]
    def heightfield(self,cell_x,cell_y,cells=1,res=129,lod=0,meters_per_height_unit=1.):
        from .starfield_planets import Heightfield
        if type(cells) is not int or not 1<=cells<=4 or res not in (33,65,129,257) or not isfinite(meters_per_height_unit) or not 0<meters_per_height_unit<=1000:raise ValueError("Invalid BTD preview parameters")
        x=(cell_x-self.min_cell[0])*128;y=(cell_y-self.min_cell[1])*128
        if x<0 or y<0 or x+cells*128>self.nx*128 or y+cells*128>self.ny*128:raise ValueError("BTD patch outside extent")
        rows=[]
        for j in range(res):
            row=[]
            for i in range(res):
                a=min(self.nx*128-1,x+round(i*cells*128/(res-1)))
                b=min(self.ny*128-1,y+round(j*cells*128/(res-1)))
                z=self.sample(a,b,lod)
                row.append((self.low+(self.high-self.low)*z/65535)*meters_per_height_unit)
            rows.append(row)
        return Heightfield(rows)
