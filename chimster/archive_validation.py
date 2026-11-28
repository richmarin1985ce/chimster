"""Read-only archive integrity audit with explicit resource budgets."""
from pathlib import Path
from .archive_reader import reader

def audit(path,max_members=1000,max_bytes=256*1024*1024,member_limit=64*1024*1024):
    if min(max_members,max_bytes,member_limit)<1:raise ValueError("Invalid audit budget")
    checked=0;total=0;issues=[];skipped=0
    with Path(path).open("rb") as stream:
        adapter=reader(stream);entries=adapter.directory(stream)
        for name,entry in entries.items():
            if checked>=max_members or total>=max_bytes:
                skipped+=1;continue
            checked+=1
            try:
                data=adapter.read(stream,entry,min(member_limit,max_bytes-total))
                total+=len(data)
            except (ValueError,OSError,ImportError) as exc:
                issues.append({"member":name,"error":str(exc)})
    return {"members":len(entries),"checked":checked,"decoded_bytes":total,"skipped":skipped,"issues":issues,"all_members_decoded":not issues and not skipped}
