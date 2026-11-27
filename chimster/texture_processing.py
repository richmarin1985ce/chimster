"""Portable image processing: alpha coverage mips, height packing, BC1/BC3 blocks.
The simple endpoint compressor favors reproducibility and correctness over quality."""
import struct,math
from .textures import shape,mip_chain
def coverage(raw,threshold):
    return sum(a>=threshold for a in raw[3::4])/(len(raw)//4)
def coverage_mips(w,h,raw,threshold=128):
    shape(w,h,raw,4)
    if type(threshold) is not int or not 1<=threshold<=255:raise ValueError("invalid alpha threshold")
    levels=mip_chain(w,h,raw);desired=coverage(raw,threshold);out=[levels[0]]
    for a,b,p in levels[1:]:
        # Pick closest attainable discrete coverage; cannot recover all subpixel foliage.
        histogram=[0]*256
        for v in p[3::4]:histogram[v]+=1
        candidates=[0.,1.]+[threshold/v for v in range(1,256) if histogram[v]]
        def score(scale):
            count=sum(n for v,n in enumerate(histogram) if min(255,round(v*scale))>=threshold)
            return abs(count/(a*b)-desired),abs(scale-1)
        s=min(candidates,key=score);q=bytearray(p)
        for i in range(3,len(q),4):q[i]=min(255,round(q[i]*s))
        out.append((a,b,bytes(q)))
    return out
def height_alpha(w,h,rgba,height):
    shape(w,h,rgba,4);shape(w,h,height,1)
    out=bytearray(rgba);out[3::4]=height
    return bytes(out)
def rgb565(rgb):
    r,g,b=rgb
    return ((r*31+127)//255<<11)|((g*63+127)//255<<5)|((b*31+127)//255)
def rgb888(v):
    r=(v>>11)&31;g=(v>>5)&63;b=v&31
    return ((r<<3)|(r>>2),(g<<2)|(g>>4),(b<<3)|(b>>2))
def colors(block,alpha=False):
    opaque=[p[:3] for p in block if not alpha or p[3]>=128]
    if not opaque:return struct.pack("<HHI",0,0,0xffffffff)
    low=min(opaque,key=lambda p:sum(p));high=max(opaque,key=lambda p:sum(p))
    a,b=rgb565(high),rgb565(low)
    if alpha:
        a,b=min(a,b),max(a,b)
    else:
        a,b=max(a,b),min(a,b)
        if a==b:
            if a<65535:a+=1
            else:b-=1
    x,y=rgb888(a),rgb888(b)
    if a>b:palette=[x,y,tuple((2*u+v)//3 for u,v in zip(x,y)),tuple((u+2*v)//3 for u,v in zip(x,y))]
    else:palette=[x,y,tuple((u+v)//2 for u,v in zip(x,y)),(0,0,0)]
    bits=0
    for i,p in enumerate(block):
        index=3 if alpha and p[3]<128 else min(range(3 if alpha else 4),key=lambda k:sum((p[j]-palette[k][j])**2 for j in range(3)))
        bits|=index<<(2*i)
    return struct.pack("<HHI",a,b,bits)
def alphas(block):
    values=[p[3] for p in block];a=max(values);b=min(values)
    if a==b:return bytes([a,b])+bytes(6)
    palette=[a,b]+[((7-i)*a+i*b)//7 for i in range(1,7)]
    bits=sum(min(range(8),key=lambda k:abs(v-palette[k]))<<(3*i) for i,v in enumerate(values))
    return bytes([a,b])+bits.to_bytes(6,"little")
def compress(w,h,raw,kind):
    shape(w,h,raw,4)
    if kind not in {"BC1","BC1A","BC3"}:raise ValueError("unsupported BC format")
    out=bytearray()
    for y in range(0,h,4):
        for x in range(0,w,4):
            block=[tuple(raw[4*(min(y+j,h-1)*w+min(x+i,w-1)):4*(min(y+j,h-1)*w+min(x+i,w-1))+4]) for j in range(4) for i in range(4)]
            if kind=="BC3":out+=alphas(block)
            out+=colors(block,kind=="BC1A" and any(p[3]<128 for p in block))
    return bytes(out)
def dds(w,h,raw,kind="BC3",mips=True,alpha_coverage=False):
    if kind not in {"BC1","BC1A","BC3"}:raise ValueError("unsupported BC format")
    if alpha_coverage and not mips:raise ValueError("coverage requires mipmaps")
    levels=(coverage_mips(w,h,raw) if alpha_coverage else mip_chain(w,h,raw)) if mips else [(w,h,raw)]
    data=[compress(a,b,p,kind) for a,b,p in levels];header=bytearray(128)
    header[:4]=b"DDS ";struct.pack_into("<7I",header,4,124,0x81007|(0x20000 if len(levels)>1 else 0),h,w,len(data[0]),0,len(levels))
    struct.pack_into("<II4s",header,76,32,4,b"DXT5" if kind=="BC3" else b"DXT1")
    struct.pack_into("<I",header,108,0x401008 if len(levels)>1 else 0x1000)
    return bytes(header)+b"".join(data)
