"""Receipt-aware native lip jobs. Existing outputs are never replaced."""
import json
from pathlib import Path
from . import lip_pipeline as lp
from .voice_manager import load_manifest,safe_path,stem
from .audio import inventory
import subprocess

def batch(source_root, receipt_root, output_root, manifest, *, tool=None, fonix=None,
          ffmpeg=None, execute=False):
    source=Path(source_root).resolve(strict=True)
    receipts=Path(receipt_root).resolve()
    output=Path(output_root).resolve()
    for a,b in ((source,receipts),(source,output),(receipts,output)):
        if a==b or a.is_relative_to(b) or b.is_relative_to(a):
            raise ValueError("source, receipt and regeneration roots must be disjoint")
    index={r["key"]:r for r in inventory(source)["lines"]}
    result=[]
    for line in manifest["lines"]:
        key=str(stem(line["stem"]))
        row={"stem":key,"record":line["record"]}
        try:
            asset=index.get(key.casefold(),{}).get("files",{}).get(".wav",{})
            if not asset or asset.get("error"):
                raise ValueError("valid source WAV missing")
            wav=safe_path(source,asset["path"])
            old=safe_path(receipts,key)
            target=safe_path(output,key)
            reason="missing"
            if old.exists():
                try:
                    checks=lp.verify(old,wav,line["text"])
                    if all(checks[k] for k in ("lip_matches","audio_matches","transcript_matches")) and not checks["experimental"] and checks.get("game")==manifest["game"]:
                        row.update(status="current");result.append(row);continue
                    reason="stale or experimental receipt"
                except (ValueError,OSError,KeyError,TypeError):
                    reason="invalid receipt"
            if target.exists():raise ValueError("regeneration destination already exists")
            row.update(reason=reason,status="planned")
            if execute:
                if not tool or not fonix:raise ValueError("configure local FaceFXWrapper and Fonix data")
                target.parent.mkdir(parents=True,exist_ok=True)
                lp.build(wav,safe_path(output,key),game=manifest["game"],transcript=line["text"],tool=tool,fonix=fonix,ffmpeg=ffmpeg)
                row["status"]="written"
        except (ValueError,OSError,KeyError,TypeError,subprocess.SubprocessError) as exc:
            row.update(status="blocked",error=str(exc))
        result.append(row)
    return {"execute":execute,"results":result}

def main(argv=None):
    import argparse
    p=argparse.ArgumentParser(prog="python -m chimster.lip_batch")
    p.add_argument("source");p.add_argument("receipts");p.add_argument("output");p.add_argument("manifest")
    p.add_argument("--tool");p.add_argument("--fonix");p.add_argument("--ffmpeg");p.add_argument("--execute",action="store_true")
    a=p.parse_args(argv)
    result=batch(a.source,a.receipts,a.output,load_manifest(a.manifest),tool=a.tool,fonix=a.fonix,ffmpeg=a.ffmpeg,execute=a.execute)
    print(json.dumps(result,indent=2))
    if any(r["status"]=="blocked" for r in result["results"]):raise SystemExit(1)
if __name__=="__main__":main()
