"""Bounded TES3 inventory and conservative STAT-only override writer.
No new forms, CELL/LAND edits, deletion records, or reference remapping."""
from pathlib import Path
from dataclasses import dataclass
import struct, hashlib

@dataclass(frozen=True)
class Record:
    signature: str
    unknown: int
    flags: int
    payload: bytes
    def subrecords(self):
        pos=0
        while pos<len(self.payload):
            if len(self.payload)-pos<8: raise ValueError("truncated subrecord")
            code,size=struct.unpack_from("<4sI",self.payload,pos);pos+=8
            if pos+size>len(self.payload): raise ValueError("invalid subrecord size")
            yield code,self.payload[pos:pos+size];pos+=size
    def encode(self):
        return struct.pack("<4sIII",self.signature.encode("ascii"),len(self.payload),self.unknown,self.flags)+self.payload

def records(path,*,max_record=64*1024*1024):
    with Path(path).open("rb") as f:
        first=True
        while True:
            head=f.read(16)
            if not head:
                if first: raise ValueError("empty plugin")
                return
            if len(head)!=16: raise ValueError("truncated TES3 header")
            code,size,unknown,flags=struct.unpack("<4sIII",head)
            if first and code!=b"TES3": raise ValueError("not TES3")
            first=False
            if size>max_record: raise ValueError("record exceeds budget")
            data=f.read(size)
            if len(data)!=size: raise ValueError("truncated record")
            yield Record(code.decode("ascii"),unknown,flags,data)

def field(r,code):
    values=[v for k,v in r.subrecords() if k==code]
    if len(values)>1: raise ValueError("duplicate field")
    return values[0] if values else None

def cstring(raw):
    if raw is None or not raw.endswith(b"\0") or b"\0" in raw[:-1]: raise ValueError("invalid string")
    return raw[:-1].decode("cp1252")

def inventory(path):
    result=[]
    for r in records(path):
        if r.signature=="TES3":continue
        # CELL NAME is not a stable identity for exterior cells; report grid separately.
        row={"signature":r.signature,"flags":r.flags,"sha256":hashlib.sha256(r.encode()).hexdigest()}
        if r.signature in {"STAT","ACTI","CONT","DOOR","NPC_","CREA","WEAP","ARMO","BOOK","MISC","SCPT"}:
            if r.signature!="SCPT":
                name=field(r,b"NAME")
                if name is not None:row["id"]=cstring(name)
        elif r.signature=="LAND":
            grid=field(r,b"INTV")
            if grid is not None and len(grid)==8:row["grid"]=list(struct.unpack("<ii",grid))
        result.append(row)
    return result

def sub(code,payload):return struct.pack("<4sI",code,len(payload))+payload

def write_static_override(base,output,editor_id,model):
    """Make an isolated ESP with one existing base STAT override.
    The selected base is the sole master. Never edits input files."""
    base=Path(base).resolve(strict=True);output=Path(output)
    if base.suffix.lower() not in {".esm",".esp"} or output.suffix.lower()!=".esp":raise ValueError("expected classic TES3 plugin filenames")
    if output.resolve()==base:raise ValueError("cannot overwrite source")
    if not model.lower().endswith(".nif") or model.startswith(("\\","/")) or ":" in model or ".." in model.replace("\\","/").split("/") or "\0" in model:raise ValueError("unsafe model path")
    existing=list(records(base))
    header=existing[0]
    if any(k==b"MAST" for k,_ in header.subrecords()):raise ValueError("base must be self-contained for initial writer")
    candidates=[r for r in existing[1:] if r.signature=="STAT" and cstring(field(r,b"NAME")).casefold()==editor_id.casefold()]
    if len(candidates)!=1:raise ValueError("expected exactly one existing STAT")
    original=candidates[0]
    parts=list(original.subrecords())
    if original.flags or original.unknown or sorted(k for k,_ in parts)!=[b"MODL",b"NAME"]:raise ValueError("unsupported flags/subrecords")
    model_bytes=model.replace("/","\\").encode("cp1252")+b"\0"
    payload=b"".join(sub(k,model_bytes if k==b"MODL" else v) for k,v in parts)
    new=Record("STAT",0,0,payload)
    hedr=struct.pack("<fI32s256sI",1.3,0,b"Chimster",b"Reviewed static model override",1)
    master=base.name.encode("cp1252")+b"\0"
    new_header=Record("TES3",0,0,sub(b"HEDR",hedr)+sub(b"MAST",master)+sub(b"DATA",struct.pack("<Q",base.stat().st_size)))
    with output.open("xb") as f:f.write(new_header.encode()+new.encode())
    try:
        check=list(records(output))
        if check!=[new_header,new]:raise ValueError("round-trip failed")
    except Exception:
        output.unlink()
        raise
    return {"output":str(output),"master":base.name,"id":editor_id,"model":model,"status":"synthetic round-trip only; engine validation required"}
