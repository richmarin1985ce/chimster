"""Compare Chimster extraction against independently extracted authorized assets."""
import hashlib
from pathlib import Path
from .archive_reader import directory,read
from .compatibility_asset_lookup import normalize

def compare(archive,reference,*,member_limit=64*1024*1024,total_limit=256*1024*1024,max_members=1000):
    root=Path(reference).resolve()
    if not root.is_dir():raise ValueError("Reference directory required")
    expected={}
    for p in root.rglob("*"):
        if p.is_symlink():raise ValueError("Reference symlink not supported")
        if p.is_file():
            key=normalize(p.relative_to(root).as_posix())
            if key in expected:raise ValueError("Ambiguous reference path")
            expected[key]=p
    actual=directory(archive)
    missing=sorted(expected.keys()-actual.keys())
    extra=sorted(actual.keys()-expected.keys())
    checked=0;used=0;issues=[];skipped=0
    for key in sorted(actual.keys()&expected.keys()):
        size=expected[key].stat().st_size
        if checked>=max_members or size>member_limit or size>total_limit-used:
            skipped+=1;continue
        budget=min(member_limit,total_limit-used)
        try:
            with expected[key].open("rb") as stream:reference_bytes=stream.read(budget+1)
            if len(reference_bytes)>budget:raise ValueError("Reference exceeds budget")
            data=read(archive,key,limit=budget)
            used+=max(len(data),len(reference_bytes))
            if hashlib.sha256(data).digest()!=hashlib.sha256(reference_bytes).digest():
                issues.append({"asset":key,"issue":"byte mismatch"})
        except (OSError,ValueError,ImportError) as exc:
            issues.append({"asset":key,"issue":str(exc)})
            used+=budget
        checked+=1
    return {"checked":checked,"skipped":skipped,"missing":missing,"extra":extra,"issues":issues,
            "reference_match":bool(checked) and not (missing or extra or issues or skipped),
            "reference_provenance":"user supplied; independence not established","retail_verified":False}
