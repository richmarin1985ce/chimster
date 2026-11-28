"""Bounded production adapters, never write the game directory."""
import hashlib
import json
import secrets
import tempfile
from pathlib import Path
from .project import Project,identifier,read_json,digest

LIMIT=16*1024*1024

class Production:
    def __init__(self,project,recovery,enabled=False):
        self.project=project
        self.recovery=recovery
        self.enabled=enabled
        self.pending=None

    def preview(self,operation,id,output_id,revision,master_ids=(),aux_id=None):
        self.pending=None
        identifier(output_id)
        m=self.project.read()
        if m["revision"]!=revision:raise ValueError("stale revision")
        outputs=[]
        def new_key(key):
            identifier(key)
            if any(k.casefold()==key.casefold() for k in m["artifacts"]):
                raise ValueError("output already exists")
        new_key(output_id)
        def source(key,kind=None,limit=LIMIT):
            a=m["artifacts"][identifier(key)]
            if a["size"]>limit or (kind and a["kind"]!=kind):raise ValueError("invalid input artifact")
            return a,self.project._object(a)
        if operation!="native-build" and master_ids:raise ValueError("unexpected masters")
        if operation not in ("fuz","texture-material") and aux_id is not None:raise ValueError("unexpected auxiliary input")
        with tempfile.TemporaryDirectory(prefix="chimster-production-") as d:
            root=Path(d)
            name="generated-"+output_id
            if operation=="native-build":
                from .project_build import build
                from .mcp_operations import named_plugin
                if m["game"]!="newvegas":raise ValueError("FNV build only")
                new_key(output_id+".ids")
                a,p=source(id,limit=1024*1024)
                if a["kind"] not in ("records","quest"):raise ValueError("expected records or quest JSON")
                if len(master_ids)>4 or len(set(k.casefold() for k in master_ids))!=len(master_ids):
                    raise ValueError("invalid master list")
                if sum(m["artifacts"][identifier(k)]["size"] for k in master_ids)>32*1024*1024:
                    raise ValueError("master size limit")
                # Build in a disposable independent project, then extract exact outputs.
                scratch=Project.create(root/"scratch","Staging","newvegas")
                data=root/"source.json";data.write_bytes(p.read_bytes())
                scratch.add("source",a["kind"],data,0)
                staged=root/"masters";staged.mkdir()
                keys=[]
                for i,k in enumerate(master_ids):
                    source(k,"plugin")
                    q=named_plugin(self.project,k,m,staged)
                    key="master"+str(i)
                    scratch.add(key,"plugin",q,scratch.read()["revision"])
                    keys.append(key)
                if output_id.casefold() in {"source",*(k.casefold() for k in keys)}:raise ValueError("reserved staging ID")
                report=build(scratch,a["kind"],"source",output_id,name+".esp",scratch.read()["revision"],keys,False)
                for key in (output_id,output_id+".ids"):
                    meta=scratch.read()["artifacts"][key]
                    outputs.append((key,meta["kind"],meta["filename"],scratch.object(key).read_bytes()))
                summary={"kind":a["kind"],"requires_game_testing":True,"script_draft":False}
            elif operation=="navmesh":
                from .navmesh import generate
                _,p=source(id,limit=512*1024)
                spec=read_json(p,512*1024)
                report=generate(spec)
                raw=json.dumps(report,allow_nan=False,separators=(",",":")).encode()
                outputs.append((output_id,"other",name+".navmesh.json",raw))
                summary={"vertices":len(report["vertices"]),"triangles":len(report["triangles"]),
                         "scope":report["scope"],"native_registration":False}
            elif operation=="font":
                from .font_forge import create
                _,p=source(id,limit=256*1024)
                spec=read_json(p,256*1024)
                if set(spec)!={"family","glyphs"} or not isinstance(spec["glyphs"],dict) or len(spec["glyphs"])>512:
                    raise ValueError("invalid glyph specification")
                glyphs={int(k):v for k,v in spec["glyphs"].items()}
                if len(glyphs)!=len(spec["glyphs"]):raise ValueError("duplicate codepoint")
                target=root/(name+".ttf")
                summary=create(spec["family"],glyphs,target)
                outputs.append((output_id,"other",target.name,target.read_bytes()))
            elif operation=="fuz":
                from .audio import pack_fuz,xwma_info
                a,p=source(id,"audio")
                if Path(a["filename"]).suffix.lower()!=".xwm":raise ValueError("XWM input required")
                raw=p.read_bytes()
                lip=b""
                if aux_id is not None:
                    b,q=source(aux_id,limit=1024*1024)
                    if Path(b["filename"]).suffix.lower()!=".lip":raise ValueError("LIP input required")
                    lip=q.read_bytes()
                summary={**xwma_info(raw),"lip_bytes":len(lip),"lip_validated":False}
                outputs.append((output_id,"audio",name+".fuz",pack_fuz(raw,lip)))
            elif operation=="texture-material":
                from PIL import Image
                from .textures import build_material
                _,p=source(id,"texture")
                _,q=source(aux_id,"texture")
                for image in (p,q):
                    with Image.open(image) as im:
                        if max(im.size)>1024 or min(im.size)<1:raise ValueError("image dimension limit")
                target=root/"maps"
                summary=build_material(p,q,target)
                summary.pop("output",None)
                for suffix in ("n","s"):
                    for ext in ("png","dds"):
                        key=output_id+"."+suffix+"."+ext
                        new_key(key)
                        outputs.append((key,"texture",name+"_"+suffix+"."+ext,(target/("material_"+suffix+"."+ext)).read_bytes()))
            elif operation in ("mesh-lod","mesh-preview"):
                from .scene import load_obj
                from .asset_forge import Session
                a,p=source(id,"mesh",8*1024*1024)
                if Path(a["filename"]).suffix.lower()!=".obj":raise ValueError("OBJ required")
                s=Session(load_obj(p))
                if operation=="mesh-lod":
                    from .lod import bounds
                    before=s.report()
                    span=max(b-a for a,b in bounds(s.mesh))
                    if span<=0:raise ValueError("degenerate mesh")
                    s.simplify(span/32)
                    target=root/(name+".obj");s.export_obj(target)
                    Session(load_obj(target))
                    outputs.append((output_id,"mesh",target.name,target.read_bytes()))
                    summary={"before":before,"after":s.report(),"native_export":False}
                else:
                    from .lod import bake
                    from .atlas import write_png
                    if len(s.mesh.faces)>2000:raise ValueError("preview triangle budget")
                    rgba,summary=bake(s.mesh,size=128)
                    target=root/(name+".png");write_png(target,128,128,rgba)
                    outputs.append((output_id,"texture",target.name,target.read_bytes()))
                    summary["scope"]="flat-color orthographic mesh preview; not full scene rendering"
            else:raise ValueError("unsupported production operation")
        if sum(len(r[3]) for r in outputs)>LIMIT:raise ValueError("output size limit")
        if self.project.read()["revision"]!=revision:raise ValueError("project changed while staging")
        token=secrets.token_urlsafe(24) if self.enabled else None
        if token:self.pending=(token,revision,outputs)
        return {"operation":operation,"revision":revision,"summary":summary,"apply_enabled":self.enabled,
                "proposal_token":token,"outputs":[{"id":k,"kind":kind,"filename":n,"size":len(raw),
                   "sha256":hashlib.sha256(raw).hexdigest()} for k,kind,n,raw in outputs]}

    def apply(self,token):
        if not self.enabled or self.pending is None or not token.isascii() or not secrets.compare_digest(token,self.pending[0]):
            raise ValueError("invalid production proposal")
        _,revision,outputs=self.pending
        self.pending=None
        with tempfile.TemporaryDirectory(prefix="chimster-production-apply-") as d:
            changes=[]
            for key,kind,name,raw in outputs:
                p=Path(d)/name;p.write_bytes(raw)
                changes.append({"op":"add","id":key,"kind":kind,"source":str(p),"replace":False})
            after=self.project.batch(changes,revision)
        self.recovery.pending=None
        self.recovery.record_commit(revision,after["revision"])
        return {"revision":after["revision"],"outputs":[{"id":k,**after["artifacts"][k]} for k,_,_,_ in outputs],
                "undo_target_revision":revision}
