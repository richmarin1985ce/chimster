"""Read-only FNV dialogue response extraction; no guessed voice filenames."""
from pathlib import Path
import hashlib
import json
import struct
from .fnv_records import scan, HEADER, subs, text, MAX_RECORD
from .record_editor import unpack_payload
from .audio import publish
from .voice_manager import stem

def responses(parts):
    result=[]
    pending=None
    seen=set()
    for tag,value in parts:
        if tag==b"TRDT":
            if pending is not None or len(value)!=24:
                raise ValueError("unsupported or incomplete FNV response layout")
            number=value[12]
            if not number or number in seen:
                raise ValueError("invalid or duplicate response number")
            seen.add(number)
            pending={"number":number,"emotion":struct.unpack_from("<I",value)[0],
                     "sound_form_id":f"{struct.unpack_from('<I',value,16)[0]:08X}"}
        elif tag==b"NAM1":
            if pending is None:
                raise ValueError("response text without TRDT")
            pending["text"]=text(value)
            result.append(pending);pending=None
    if pending is not None:
        raise ValueError("response missing text")
    return result

def extract(path):
    path=Path(path).resolve(strict=True)
    index=scan(path)
    result=[];errors=[]
    with path.open("rb") as f:
        for record in index["records"]:
            if record["signature"]!="INFO" or record["flags"]&0x20:
                continue
            key=f'{record["origin"]}:{record["local_id"]:06X}'
            try:
                f.seek(record["offset"])
                sig,n,flags,*_=HEADER.unpack(f.read(24))
                if sig!=b"INFO" or n>MAX_RECORD:
                    raise ValueError("invalid INFO header")
                raw=f.read(n)
                if hashlib.sha256(raw).hexdigest()!=record["payload_sha256"]:
                    raise ValueError("record changed since index")
                lines=responses(subs(unpack_payload(raw,flags)))
                for line in lines:
                    result.append({**line,"record":key,"provider":path.name,
                                   "line_id":f'{key}:{line["number"]}'})
            except (ValueError, OSError, struct.error) as exc:
                errors.append({"record":key,"error":str(exc)})
    return {"game":"FalloutNV","provider":path.name,"lines":result,"errors":errors}

def attach_paths(report, mapping):
    """Join exact paths supplied by a GECK export or local asset inventory."""
    if not isinstance(mapping,dict):
        raise ValueError("expected line-ID to list-of-stems mapping")
    ids={row["line_id"] for row in report["lines"]}
    if set(mapping)-ids:
        raise ValueError("mapping references unknown dialogue lines")
    rows=[];unmapped=[];used=set()
    for row in report["lines"]:
        paths=mapping.get(row["line_id"],[])
        if not isinstance(paths,list):
            raise ValueError("expected list of voice stems")
        if not paths:unmapped.append(row["line_id"])
        for value in paths:
            name=str(stem(value))
            if name.casefold() in used:
                raise ValueError("duplicate mapped voice stem")
            used.add(name.casefold())
            rows.append({**row,"stem":name})
    return {"game":"FalloutNV","lines":rows,"unmapped":unmapped,"errors":report["errors"],
            "note":"FNV voice paths only; not a Skyrim/FO4 FUZ batch manifest"}

def main(argv=None):
    import argparse
    p=argparse.ArgumentParser()
    p.add_argument("plugin");p.add_argument("--mapping");p.add_argument("--output")
    a=p.parse_args(argv)
    report=extract(a.plugin)
    if a.mapping:report=attach_paths(report,json.loads(Path(a.mapping).read_text(encoding="utf-8")))
    encoded=json.dumps(report,indent=2,ensure_ascii=False)
    if a.output:publish(Path(a.output),encoded.encode("utf-8"))
    else:print(encoded)

if __name__=="__main__":main()
