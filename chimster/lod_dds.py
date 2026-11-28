"""Original bounded DDS decoder for classic landscape textures (no external packages)."""
import struct
def rgb565(v):
    return ((v>>11&31)*255//31,(v>>5&63)*255//63,(v&31)*255//31)
def decode(raw):
    if len(raw)<128 or raw[:4]!=b"DDS " or struct.unpack_from("<I",raw,4)[0]!=124:raise ValueError("Invalid DDS")
    h,w,pitch=struct.unpack_from("<3I",raw,12)
    if not 1<=w<=4096 or not 1<=h<=4096 or w*h>4194304:raise ValueError("DDS pixel budget")
    pf,flags,fourcc,bits,rm,gm,bm,am=struct.unpack_from("<8I",raw,76)
    if pf!=32:raise ValueError("Invalid DDS pixel format")
    out=bytearray(w*h*4);data=memoryview(raw)[128:]
    if flags&4:
        kind=struct.pack("<I",fourcc)
        if kind not in (b"DXT1",b"DXT3",b"DXT5"):raise ValueError("Unsupported DDS compression")
        stride=8 if kind==b"DXT1" else 16
        bx=(w+3)//4;by=(h+3)//4
        if len(data)<bx*by*stride:raise ValueError("Truncated DDS blocks")
        for y in range(by):
            for x in range(bx):
                block=data[(y*bx+x)*stride:(y*bx+x+1)*stride]
                c0,c1,indices=struct.unpack_from("<HHI",block,stride-8)
                a,b=rgb565(c0),rgb565(c1)
                if c0>c1 or kind!=b"DXT1":
                    pal=[(*a,255),(*b,255),(*( (2*i+j)//3 for i,j in zip(a,b)),255),(*( (i+2*j)//3 for i,j in zip(a,b)),255)]
                else:pal=[(*a,255),(*b,255),(*( (i+j)//2 for i,j in zip(a,b)),255),(0,0,0,0)]
                if kind==b"DXT3":alpha=int.from_bytes(block[:8],"little")
                elif kind==b"DXT5":
                    a0,a1=block[:2]
                    al=[a0,a1]+([( (7-i)*a0+i*a1)//7 for i in range(1,7)] if a0>a1 else [((5-i)*a0+i*a1)//5 for i in range(1,5)]+[0,255])
                    alpha=int.from_bytes(block[2:8],"little")
                for i in range(16):
                    px=x*4+i%4;py=y*4+i//4
                    if px>=w or py>=h:continue
                    rgba=pal[(indices>>(2*i))&3]
                    if kind==b"DXT3":rgba=(*rgba[:3],((alpha>>(4*i))&15)*17)
                    if kind==b"DXT5":rgba=(*rgba[:3],al[(alpha>>(3*i))&7])
                    j=(py*w+px)*4;out[j:j+4]=bytes(rgba)
    elif flags&0x40 and bits in (24,32):
        masks=(rm,gm,bm,am)
        if not all(masks[:3]) or any(a&b for i,a in enumerate(masks) for b in masks[i+1:]):raise ValueError("Invalid DDS masks")
        for mask in masks:
            if mask and (mask>>((mask&-mask).bit_length()-1)) & ((mask>>((mask&-mask).bit_length()-1))+1):raise ValueError("Noncontiguous DDS mask")
        unit=bits//8;row=max(w*unit,pitch)
        if row>w*unit+4096 or len(data)<row*h:raise ValueError("Truncated DDS pixels")
        for y in range(h):
            for x in range(w):
                val=int.from_bytes(data[y*row+x*unit:y*row+(x+1)*unit],"little")
                for i,mask in enumerate(masks):
                    out[(y*w+x)*4+i]=((val&mask)*255//mask) if mask else 255
    else:raise ValueError("Unsupported DDS format")
    return w,h,bytes(out)
