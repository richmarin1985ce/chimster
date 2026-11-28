"""Strict subset of DDS: single 2D block-compressed textures."""
import struct
from .ba2_texture import BLOCKS

LEGACY={b"DXT1":71,b"DXT3":74,b"DXT5":77,b"ATI1":80,b"ATI2":83,b"BC4U":80,b"BC5U":83}

def parse(data,limit=64*1024*1024):
    if len(data)>limit or len(data)<128 or data[:4]!=b"DDS ":raise ValueError("Invalid DDS extent")
    size,flags,h,w,pitch,depth,mips=struct.unpack_from("<7I",data,4)
    pfsize,pfflags,fourcc=struct.unpack_from("<II4s",data,76)
    caps,caps2=struct.unpack_from("<II",data,108)
    mips=mips or 1
    if size!=124 or pfsize!=32 or not pfflags&4 or not caps&0x1000 or caps2 or depth>1:
        raise ValueError("Unsupported DDS layout")
    if not 1<=w<=65535 or not 1<=h<=65535 or not 1<=mips<=max(w,h).bit_length():
        raise ValueError("Invalid texture dimensions")
    start=128
    if fourcc==b"DX10":
        if len(data)<148:raise ValueError("Truncated DX10 header")
        fmt,dimension,misc,array,alpha=struct.unpack_from("<5I",data,128)
        if dimension!=3 or misc or array!=1 or alpha:raise ValueError("Unsupported DX10 metadata")
        start=148
    else:fmt=LEGACY.get(fourcc)
    if fmt not in BLOCKS:raise ValueError("Unsupported block format")
    levels=[]
    for i in range(mips):
        length=((max(1,w>>i)+3)//4)*((max(1,h>>i)+3)//4)*BLOCKS[fmt]
        if start+length>len(data):raise ValueError("Truncated mip chain")
        levels.append(data[start:start+length]);start+=length
    if start!=len(data):raise ValueError("Unexpected DDS trailing data")
    return {"width":w,"height":h,"mips":mips,"dxgi_format":fmt,"levels":levels}
