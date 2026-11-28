"""Read archive configuration without modifying game INI files."""
import configparser,re

def parse(profile,text):
    cfg=configparser.ConfigParser(interpolation=None,strict=False)
    cfg.read_string(text)
    sections={s.casefold():cfg[s] for s in cfg.sections()}
    archives=[];settings={}
    if profile=="morrowind":
        section=sections.get("archives",{})
        rows=[]
        for key,value in section.items():
            match=re.fullmatch(r"archive\s+(\d+)",key)
            if match:rows.append((int(match.group(1)),value.strip()))
        archives=[v for _,v in sorted(rows) if v]
    else:
        section=sections.get("archive",{})
        for key in ("sarchivelist","sresourcearchivelist","sresourcearchivelist2","sresourcearchivelistbeta","sresourceindexfilelist"):
            if key in section:
                settings[key]=section[key]
                archives.extend(v.strip() for v in section[key].split(",") if v.strip())
        for key in ("binvalidateolderfiles","sarchiveinvalidationfile","busearchives"):
            if key in section:settings[key]=section[key]
    seen=set();ordered=[]
    for name in archives:
        if any(c in name for c in "/\\:") or not name.lower().endswith((".bsa",".ba2")):
            raise ValueError("Invalid configured archive: "+name)
        if name.casefold() not in seen:
            seen.add(name.casefold());ordered.append(name)
    return {"base_archives":ordered,"settings":settings,"engine_verified":False}

def read(profile,path,encoding="cp1252"):
    with open(path,encoding=encoding) as stream:
        text=stream.read(2*1024*1024+1)
    if len(text)>2*1024*1024:raise ValueError("INI exceeds size limit")
    try:return parse(profile,text)
    except configparser.Error as exc:raise ValueError("Invalid INI configuration") from exc
