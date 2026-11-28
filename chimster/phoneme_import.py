"""Language-independent timed phoneme import. No guessed phoneme normalization."""
from pathlib import Path
import csv
import json
import math
import re
import tempfile
import unicodedata
from . import audio

def validate(rows, duration):
    if not math.isfinite(duration) or duration<=0 or not isinstance(rows,list) or not rows or len(rows)>100000:
        raise ValueError("invalid timeline or duration")
    out=[];previous=0.0
    for row in rows:
        label=row["phoneme"]
        if not isinstance(label,str) or len(label)>128 or any(unicodedata.category(c)=="Cc" for c in label):
            raise ValueError("invalid phoneme label")
        a,b=float(row["start"]),float(row["end"])
        if not math.isfinite(a) or not math.isfinite(b) or not previous<=a<b<=duration+1e-6:
            raise ValueError("overlapping or out-of-range phoneme interval")
        item={"phoneme":label.strip() or "sil","start":a,"end":min(b,duration)}
        if item["end"]<=a:raise ValueError("empty interval")
        if row.get("confidence") not in (None,""):
            conf=float(row["confidence"])
            if not math.isfinite(conf) or not 0<=conf<=1:raise ValueError("invalid confidence")
            item["confidence"]=conf
        out.append(item);previous=b
    return out

def textgrid(text,tier="phones"):
    blocks=re.split(r"(?m)^\s*item \[\d+\]:\s*$",text)
    selected=[]
    for block in blocks:
        name=re.search(r'(?m)^\s*name\s*=\s*"((?:[^"]|"")*)"\s*$',block)
        if name and name[1].replace('""','"')==tier:
            selected.append(block)
    if len(selected)!=1:raise ValueError("choose a unique interval tier")
    block=selected[0]
    if not re.search(r'(?m)^\s*class\s*=\s*"IntervalTier"',block):raise ValueError("expected interval tier")
    declared=re.search(r"intervals:\s*size\s*=\s*(\d+)",block)
    parts=re.split(r"(?m)^\s*intervals \[\d+\]:\s*$",block)[1:]
    if not declared or int(declared[1])!=len(parts):raise ValueError("unsupported or truncated long TextGrid")
    rows=[]
    for p in parts:
        a=re.search(r"(?m)^\s*xmin\s*=\s*(\S+)\s*$",p)
        b=re.search(r"(?m)^\s*xmax\s*=\s*(\S+)\s*$",p)
        label=re.search(r'(?m)^\s*text\s*=\s*"((?:[^"]|"")*)"\s*$',p)
        if not all((a,b,label)):raise ValueError("incomplete interval")
        rows.append({"start":a[1],"end":b[1],"phoneme":label[1].replace('""','"')})
    return rows

def load(path,duration,tier="phones"):
    p=Path(path)
    if p.stat().st_size>16*1024*1024:raise ValueError("import too large")
    ext=p.suffix.lower()
    if ext==".json":
        rows=json.loads(p.read_text(encoding="utf-8-sig"))
        if isinstance(rows,dict):rows=rows["segments"]
    elif ext in (".csv",".tsv"):
        with p.open(encoding="utf-8-sig",newline="") as f:rows=list(csv.DictReader(f,delimiter="," if ext==".csv" else "\t"))
    elif ext==".textgrid":rows=textgrid(p.read_text(encoding="utf-8-sig"),tier)
    else:raise ValueError("use JSON, CSV, TSV or long TextGrid")
    return validate(rows,duration)

def align(wav,transcript,dictionary,model,tool="mfa",tier="phones",legacy=False):
    wav=Path(wav).resolve(strict=True)
    dictionary=Path(dictionary).resolve(strict=True);model=Path(model).resolve(strict=True)
    if not transcript.strip():raise ValueError("transcript required")
    duration=audio.wav_info(wav.read_bytes())["duration"]
    with tempfile.TemporaryDirectory() as d:
        root=Path(d);txt=root/"line.txt";txt.write_text(transcript,encoding="utf-8")
        out=root/"line.TextGrid"
        audio.run_tool([audio.executable(tool),"align_one_legacy" if legacy else "align_one","--output_format","long_textgrid","--num_jobs","1","--temporary_directory",str(root/"work"),str(wav),str(txt),str(dictionary),str(model),str(out)],timeout=600)
        return load(out,duration,tier)

def save(path,rows,duration):
    audio.publish(Path(path),json.dumps(validate(rows,duration),ensure_ascii=False,indent=2).encode("utf-8"))

def main(argv=None):
    import argparse
    p=argparse.ArgumentParser();s=p.add_subparsers(dest="op",required=True)
    a=s.add_parser("import");a.add_argument("source");a.add_argument("wav");a.add_argument("output");a.add_argument("--tier",default="phones")
    a=s.add_parser("align");a.add_argument("wav");a.add_argument("output");a.add_argument("--transcript",required=True);a.add_argument("--dictionary",required=True);a.add_argument("--model",required=True);a.add_argument("--tool",default="mfa");a.add_argument("--tier",default="phones");a.add_argument("--legacy",action="store_true")
    a=p.parse_args(argv);duration=audio.wav_info(Path(a.wav).read_bytes())["duration"]
    rows=load(a.source,duration,a.tier) if a.op=="import" else align(a.wav,a.transcript,a.dictionary,a.model,a.tool,a.tier,a.legacy)
    save(a.output,rows,duration)
if __name__=="__main__":main()
