"""Portable SPT authoring project: immutable source, explicit edits, native export.

The project is intentionally not a replacement procedural tree generator.
Unknown SPT variants can be archived and exported byte-for-byte, not edited.
"""
import json,struct,hashlib,shutil
from pathlib import Path
from .speedtree import parse,edit_scalars

LIMIT=64*1024*1024
TEXTURE_TAGS={2000,4003,14002,18005,20002,60006,*range(70002,70009)}
SCHEMA=1

def digest(raw):return hashlib.sha256(raw).hexdigest()

def read_bounded(path,limit=LIMIT):
    path=Path(path)
    with path.open("rb") as f:raw=f.read(limit+1)
    if len(raw)>limit:raise ValueError("File size limit")
    return raw

def header(raw):
    if not 8<=len(raw)<=LIMIT:raise ValueError("SPT size limit")
    tag,n=struct.unpack_from("<II",raw)
    if tag!=1000 or not 1<=n<=128 or 8+n>len(raw):raise ValueError("Invalid SPT header")
    sig=raw[8:8+n].rstrip(b"\0").decode("ascii")
    if not sig.startswith("__IdvSpt_"):raise ValueError("Unrecognized SPT signature")
    return sig

def inspect_source(raw):
    signature=header(raw)
    try:info=parse(raw)
    except (ValueError,UnicodeError,struct.error) as exc:
        return {"signature":signature,"parse_complete":False,"issue":str(exc),"fields":{},"textures":[]}
    # A known signature is a prerequisite for edits, not proof of runtime compatibility.
    textures=[]
    for i,t in enumerate(t for t in info["tokens"] if t["tag"] in TEXTURE_TAGS):
        value=raw[t["payload"]+4:t["end"]].rstrip(b"\0").decode("latin-1")
        textures.append({"index":i,"tag":t["tag"],"value":value})
    return {"signature":signature,"parse_complete":info["complete"] and signature=="__IdvSpt_02_",
            "issue":info["unknown"],"fields":info["fields"],"textures":textures}

def relink(raw,replacements):
    """Replace indexed texture strings only. Preserve original terminator convention."""
    info=parse(raw)
    if not info["complete"] or header(raw)!="__IdvSpt_02_":raise ValueError("Texture editing requires supported complete parse")
    tokens=[t for t in info["tokens"] if t["tag"] in TEXTURE_TAGS]
    if not isinstance(replacements,dict) or len(replacements)>4096:raise ValueError("Texture edit limit")
    edits=[]
    for key,value in replacements.items():
        if not isinstance(key,str) or not key.isascii() or not key.isdecimal() or len(key)>6:raise ValueError("Texture index must be decimal")
        index=int(key)
        if str(index)!=key or not 0<=index<len(tokens):raise ValueError("Invalid texture index")
        if not isinstance(value,str):raise ValueError("Texture path must be text")
        normalized=value.replace("\\","/")
        if not normalized or len(normalized)>1024 or any(not p or p in (".","..") or ":" in p for p in normalized.split("/")) or any(ord(ch)<32 for ch in value):raise ValueError("Unsafe texture reference")
        if not normalized.lower().endswith((".dds",".tga",".png",".bmp",".jpg",".jpeg")):raise ValueError("Unsupported texture extension")
        t=tokens[index];old=raw[t["payload"]+4:t["end"]]
        encoded=value.encode("latin-1")+b"\0"*(len(old)-len(old.rstrip(b"\0")))
        edits.append((t["payload"],t["end"],struct.pack("<I",len(encoded))+encoded))
    out=raw
    for start,end,encoded in sorted(edits,reverse=True):out=out[:start]+encoded+out[end:]
    after=parse(out)
    if not after["complete"] or [t["tag"] for t in after["tokens"]]!=[t["tag"] for t in info["tokens"]]:raise ValueError("Texture edit changed token structure")
    # Compare every untouched token's bytes after variable-length edits.
    changed={start for start,_,_ in edits}
    for old,new in zip(info["tokens"],after["tokens"]):
        if old["payload"] not in changed and raw[old["offset"]:old["end"]]!=out[new["offset"]:new["end"]]:raise ValueError("Unrelated token changed")
    return out

def import_bytes(raw,output,source_name="Tree.spt"):
    info=inspect_source(raw)
    out=Path(output);out.mkdir(exist_ok=False)
    try:
        (out/"source.spt").write_bytes(raw)
        meta={"schema":SCHEMA,"source_name":Path(source_name).name,"source_sha256":digest(raw),
              "source_bytes":len(raw),**info,"runtime_verified":False}
        (out/"manifest.json").write_text(json.dumps(meta,indent=2,allow_nan=False),encoding="utf-8")
        (out/"edits.json").write_text(json.dumps({"scalars":{},"textures":{}},indent=2),encoding="utf-8")
    except Exception:shutil.rmtree(out);raise
    return meta

def import_file(source,output):
    return import_bytes(read_bounded(source),output,Path(source).name)

def export_project(project,output):
    root=Path(project)
    raw=read_bounded(root/"source.spt")
    meta=json.loads(read_bounded(root/"manifest.json",4*1024*1024))
    changes=json.loads(read_bounded(root/"edits.json",1024*1024))
    if not isinstance(meta,dict):raise ValueError("Invalid project manifest")
    if meta.get("schema")!=SCHEMA or meta.get("source_sha256")!=digest(raw) or meta.get("source_bytes")!=len(raw):raise ValueError("Project source integrity mismatch")
    if not isinstance(changes,dict) or set(changes)!={"scalars","textures"} or any(not isinstance(v,dict) for v in changes.values()):raise ValueError("Invalid edits schema")
    original=raw;info=inspect_source(raw)
    if changes["scalars"] or changes["textures"]:
        if not info["parse_complete"]:raise ValueError("Opaque SPT permits unchanged export only")
        if changes["scalars"]:raw=edit_scalars(raw,changes["scalars"])
        if changes["textures"]:raw=relink(raw,changes["textures"])
    out=Path(output)
    if out.suffix.casefold()!=".spt":raise ValueError("Expected SPT output")
    with out.open("xb") as f:f.write(raw)
    return {"output":str(out),"source_sha256":digest(original),"output_sha256":digest(raw),
            "byte_identical":original==raw,"parse_complete":inspect_source(raw)["parse_complete"],
            "runtime_verified":False,"external_tools":False}
