"""Experimental BA2 packaging for original assets with supplied native hashes."""
import io,os,tempfile
from pathlib import Path
from . import ba2_writer,ba2_general
from .compatibility_asset_lookup import normalize

def package(destination,entries,*,compress=True,limit=256*1024*1024,version=1):
    rows=list(entries)
    data=ba2_writer.build(rows,limit=limit,compress=compress,version=version)
    stream=io.BytesIO(data)
    directory=ba2_general.directory(stream)
    if len(directory)!=len(rows):raise ValueError("Directory verification failed")
    for name,raw,_,_ in rows:
        if ba2_general.read(stream,directory[normalize(name)],limit)!=raw:
            raise ValueError("Payload verification failed: "+name)
    target=Path(destination)
    if target.suffix.lower()!=".ba2":raise ValueError("Expected BA2 destination")
    fd,temp=tempfile.mkstemp(prefix=".chimster-",dir=target.parent)
    try:
        with os.fdopen(fd,"wb") as out:
            out.write(data);out.flush();os.fsync(out.fileno())
        os.link(temp,target)
    finally:
        os.unlink(temp)
    return {"path":str(target),"members":len(rows),"bytes":len(data),"roundtrip_verified":True,"retail_verified":False}

def package_assets(destination,entries,**options):
    from .ba2_hash import prepare
    return package(destination,prepare(entries),**options)

def package_directory(source,destination,*,compress=True,limit=256*1024*1024,format='ba2',ba2_version=1):
    root=Path(source).resolve()
    if not root.is_dir():raise ValueError("Expected asset directory")
    if Path(destination).resolve().is_relative_to(root):raise ValueError("Save archive outside source directory")
    def assets():
        total=0
        for path in sorted(root.rglob("*")):
            if path.is_symlink():raise ValueError("Symlinks are not supported")
            if not path.is_file():continue
            if not path.resolve().is_relative_to(root):raise ValueError("Asset outside source directory")
            name=path.relative_to(root).as_posix()
            total+=path.stat().st_size+36+2+len(name.encode("ascii"))
            if total+24>limit:raise ValueError("Asset directory exceeds budget")
            with path.open("rb") as stream:
                raw=stream.read(limit-total+path.stat().st_size+1)
            if len(raw)!=path.stat().st_size:raise ValueError("Asset changed during read")
            yield name,raw
    if format=='pair':
        from .ba2_split import package_pair
        target=Path(destination)
        return package_pair(target.parent,target.name,assets(),version=ba2_version,compress=compress,limit=limit)
    if format=='tes3':return package_tes3(destination,assets(),limit=limit)
    if format in ('103','104','105'):return package_classic(destination,assets(),version=int(format),compress=compress,limit=limit)
    if format=='dx10':return package_textures(destination,assets(),compress=compress,limit=limit,version=ba2_version)
    if format!='ba2':raise ValueError('Unsupported packaging format')
    return package_assets(destination,assets(),compress=compress,limit=limit,version=ba2_version)

def package_tes3(destination,entries,*,limit=256*1024*1024):
    from . import tes3_bsa_writer,tes3_bsa
    rows=list(entries)
    data=tes3_bsa_writer.build(rows,limit)
    stream=io.BytesIO(data)
    index=tes3_bsa.directory(stream)
    if len(index)!=len(rows):raise ValueError("Directory verification failed")
    for name,raw in rows:
        if tes3_bsa.read(stream,index[normalize(name)],limit)!=raw:
            raise ValueError("Payload verification failed: "+name)
    target=Path(destination)
    if target.suffix.lower()!=".bsa":raise ValueError("Expected BSA destination")
    fd,temp=tempfile.mkstemp(prefix=".chimster-",dir=target.parent)
    try:
        with os.fdopen(fd,"wb") as out:
            out.write(data);out.flush();os.fsync(out.fileno())
        os.link(temp,target)
    finally:
        os.unlink(temp)
    return {"path":str(target),"members":len(rows),"bytes":len(data),"roundtrip_verified":True,"retail_verified":False}

def package_classic(destination,entries,*,version=103,compress=False,limit=256*1024*1024):
    from . import classic_bsa_writer,classic_bsa
    rows=list(entries)
    data=classic_bsa_writer.build(rows,limit,version=version,compress=compress)
    stream=io.BytesIO(data)
    index=classic_bsa.directory(stream)
    if len(index)!=len(rows):raise ValueError("Directory verification failed")
    for name,raw in rows:
        if classic_bsa.read(stream,index[normalize(name)],limit)!=raw:
            raise ValueError("Payload verification failed: "+name)
    target=Path(destination)
    if target.suffix.lower()!=".bsa":raise ValueError("Expected BSA destination")
    fd,temp=tempfile.mkstemp(prefix=".chimster-",dir=target.parent)
    try:
        with os.fdopen(fd,"wb") as out:
            out.write(data);out.flush();os.fsync(out.fileno())
        os.link(temp,target)
    finally:
        os.unlink(temp)
    return {"path":str(target),"members":len(rows),"bytes":len(data),"version":version,"roundtrip_verified":True,"retail_verified":False}

def package_textures(destination,entries,*,compress=True,limit=256*1024*1024,version=1):
    from . import ba2_texture_writer,ba2_texture,dds_texture
    rows=list(entries)
    data=ba2_texture_writer.build(rows,limit=limit,compress=compress,version=version)
    stream=io.BytesIO(data)
    index=ba2_texture.directory(stream)
    if len(index)!=len(rows):raise ValueError("Directory verification failed")
    for name,raw in rows:
        decoded=ba2_texture.read(stream,index[normalize(name)],limit)
        if dds_texture.parse(decoded,limit)!=dds_texture.parse(raw,limit):
            raise ValueError("Texture verification failed: "+name)
    target=Path(destination)
    if target.suffix.lower()!=".ba2":raise ValueError("Expected BA2 destination")
    fd,temp=tempfile.mkstemp(prefix=".chimster-",dir=target.parent)
    try:
        with os.fdopen(fd,"wb") as out:
            out.write(data);out.flush();os.fsync(out.fileno())
        os.link(temp,target)
    finally:
        os.unlink(temp)
    return {"path":str(target),"members":len(rows),"bytes":len(data),"format":"DX10","roundtrip_verified":True,"retail_verified":False}
