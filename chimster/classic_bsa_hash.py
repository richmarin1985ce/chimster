"""Classic BSA hash mathematics, ASCII paths only.
Public format reference: TES5Edit Core/wbHash.pas, _TES4.
"""
def native_hash(name,filename=False):
    raw=name.lower().replace("/",chr(92)).encode("ascii")
    stem,ext=raw,b""
    if filename and b"." in raw:
        stem,ext=raw.rsplit(b".",1)
        ext=b"."+ext
    if not 1<=len(stem)<=255:raise ValueError("Invalid BSA hash name length")
    low=stem[-1]|(len(stem)<<16)|(stem[0]<<24)
    if len(stem)>2:low|=stem[-2]<<8
    low|={b".kf":0x80,b".nif":0x8000,b".dds":0x8080,b".wav":0x80000000}.get(ext,0)
    def polynomial(data):
        value=0
        for byte in data:value=(value*0x1003f+byte)&0xffffffff
        return value
    high=(polynomial(stem[1:-2])+polynomial(ext))&0xffffffff
    return low|(high<<32)
