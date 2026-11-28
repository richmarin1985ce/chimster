"""Editor-facing native session. No disk writes or implicit master changes."""
from hashlib import sha256
import struct
from .native_identity import token, parse_token
from .native_parser import parse
from .native_catalog import inspect_node
from .native_serialization import serialize, replace_payload
from .native_edit import edit_reference
from .native_dependencies import Dependencies
from .native_remap_plan import plan

class NativeSession:
    def __init__(self, profile, data, slots, external_types=None, external_records=None):
        self.profile=profile
        self.data=bytes(data)
        self.slots=slots
        self.external_types=dict(external_types or {})
        self.external_records=dict(external_records or {})
        self.refresh()

    def refresh(self):
        self.nodes=parse(self.profile,self.data)
        self.rows={}
        self.paths={}
        self.types=dict(self.external_types)
        def walk(nodes,prefix=()):
            for i,node in enumerate(nodes):
                path=prefix+(i,)
                if node.signature==b"GRUP":
                    walk(node.children,path)
                elif node.signature not in (b"TES3",b"TES4"):
                    row=inspect_node(self.profile,node,self.slots)
                    self.rows[path]=row
                    key=row["key"]
                    if key is not None:
                        self.paths.setdefault(key,[]).append(path)
                        deleted=(any(k==b"DELE" for k,_ in row["parts"]) or bool(struct.unpack_from("<I",node.header,12)[0]&0x20)) if self.profile=="morrowind" else bool(struct.unpack_from("<I",node.header,8)[0]&0x20)
                        if deleted:
                            self.types.pop(key,None)
                        else:self.types[key]=node.signature.decode("ascii")
        walk(self.nodes)
        for key,paths in self.paths.items():
            if len(paths)!=1:self.types.pop(key,None)
        edges=[]
        opaque=set()
        for path,row in self.rows.items():
            key=row["key"]
            if key is None:
                continue
            edges.extend((key,e[2]) for e in row["edges"])
            if row["opaque"]:
                opaque.add(key)
        external={k:v for k,v in self.external_records.items() if k not in self.paths}
        for key,row in external.items():
            edges.extend((key,e[2]) for e in row["edges"])
            if row["opaque"]:opaque.add(key)
        self.dependencies=Dependencies(edges,set(self.paths)|set(external),opaque)
        self.revision=sha256(self.data).hexdigest()

    def identity_token(self,path):
        return token(self.profile,self.rows[tuple(path)]["key"])

    def resolve_identity(self,value):
        _,key=parse_token(value,self.profile)
        matches=self.paths.get(key,())
        if len(matches)!=1 or key not in self.types:
            raise ValueError("missing, deleted or ambiguous persistent identity")
        return matches[0]

    def node(self,path):
        if not path or any(type(i) is not int or i<0 for i in path):
            raise ValueError("invalid record path")
        nodes=self.nodes
        for i in path:
            node=nodes[i]
            nodes=node.children
        return node

    def review(self,key,reverse=False):
        return self.dependencies.closure([key],reverse)

    def validate(self):
        """Read-only diagnostics; unresolved external records are not presumed invalid."""
        issues=[]
        for key,paths in self.paths.items():
            if len(paths)>1:
                issues.append(("duplicate-identity",key,tuple(paths)))
        for path,row in self.rows.items():
            key=row["key"]
            if key is None:
                issues.append(("unidentified-record",path))
            elif key in self.external_types:
                actual=self.node(path).signature.decode("ascii")
                if actual!=self.external_types[key]:
                    issues.append(("override-type-conflict",path,key,self.external_types[key],actual))
            if row["opaque"]:
                issues.append(("incomplete-schema",path,tuple(row["opaque"])))
            for index,offset,target,kinds in row["edges"]:
                actual=self.types.get(target)
                if actual is None:
                    issues.append(("unresolved-target",path,index,offset,target))
                elif kinds and actual not in kinds:
                    issues.append(("wrong-target-type",path,index,offset,target,actual,kinds))
        return issues

    @staticmethod
    def diagnostic_severity(code):
        if code in ("incomplete-schema","unresolved-target","unidentified-record"):
            return "warning"
        return "error"

    def validation_summary(self):
        issues=self.validate()
        counts={}
        for issue in issues:
            counts[issue[0]]=counts.get(issue[0],0)+1
        severity_counts={"error":0,"warning":0}
        for issue in issues:severity_counts[self.diagnostic_severity(issue[0])]+=1
        return {"records":len(self.rows),"issues":issues,"counts":counts,"severity_counts":severity_counts,
                "complete":not issues,"revision":self.revision}

    def remap_preview(self,path,destination):
        node=self.node(path)
        return plan(self.profile,node.signature.decode("ascii"),
                    self.rows[path]["parts"],self.slots,destination)

    def apply(self,revision,edits):
        """All edits succeed or original session remains unchanged."""
        if revision!=self.revision:
            raise ValueError("stale session")
        if not isinstance(edits,(list,tuple)) or not 1<=len(edits)<=256:raise ValueError("expected bounded reference edit batch")
        candidate=NativeSession(self.profile,self.data,self.slots,self.external_types,self.external_records)
        for edit in edits:
            if len(edit)==4:
                path,index,expected,target=edit
                offset=None
            elif len(edit)==5:
                path,index,expected,target,offset=edit
            else:raise ValueError("invalid edit tuple")
            path=candidate.resolve_identity(path) if isinstance(path,str) else tuple(path)
            node=candidate.node(path)
            if path not in candidate.rows:
                raise ValueError("not an editable record")
            key=candidate.rows[path]["key"]
            if key is None or len(candidate.paths.get(key,()))!=1 or key not in candidate.types:
                raise ValueError("missing, deleted or ambiguous record identity")
            updated=edit_reference(self.profile,node,self.slots,index,expected,target,candidate.types,offset=offset)
            data=replace_payload(self.profile,candidate.data,path,node.payload,updated.payload)
            candidate=NativeSession(self.profile,data,self.slots,self.external_types,self.external_records)
        self.__dict__.update(candidate.__dict__)
        return self.revision

    def typed_fields(self,path):
        """Show only explicitly supported typed property adapters."""
        from .native_typed_edit import property_fields
        path=tuple(path)
        if path not in self.rows:raise ValueError("Select a record")
        root=self.nodes[0]
        localized=root.signature==b"TES4" and bool(struct.unpack_from("<I",root.header,8)[0]&0x80)
        return property_fields(self.profile,self.node(path),localized)

    def apply_typed(self,revision,edits):
        """Apply a typed batch atomically; never change identity or write files."""
        from .native_typed_edit import edit
        if revision!=self.revision:raise ValueError("stale session")
        if not isinstance(edits,(list,tuple)) or not 1<=len(edits)<=256:
            raise ValueError("expected bounded nonempty edit batch")
        candidate=NativeSession(self.profile,self.data,self.slots,self.external_types,self.external_records)
        for selector,tag,occurrence,changes in edits:
            path=candidate.resolve_identity(selector) if isinstance(selector,str) else tuple(selector)
            if path not in candidate.rows:raise ValueError("not an editable record")
            key=candidate.rows[path]["key"]
            if key is None or len(candidate.paths.get(key,()))!=1 or key not in candidate.types:
                raise ValueError("missing, deleted or ambiguous record identity")
            if not isinstance(tag,bytes) or len(tag)!=4:raise ValueError("invalid field tag")
            data=edit(self.profile,candidate.data,path,tag,occurrence,changes,candidate.revision)
            updated=NativeSession(self.profile,data,self.slots,self.external_types,self.external_records)
            if updated.paths!=candidate.paths or updated.types!=candidate.types:
                raise ValueError("typed edit changed record identities or types")
            candidate=updated
        self.__dict__.update(candidate.__dict__)
        return self.revision

    def reference_fields(self,path):
        """Discover explicitly typed links, including null links; never infer unknown offsets."""
        from .native_catalog import references
        path=tuple(path)
        if self.slots is None or path not in self.rows:return []
        row=self.rows[path];key=row["key"]
        if key not in self.types or len(self.paths.get(key,()))!=1:return []
        edges,opaque=references(self.profile,self.node(path).signature.decode("ascii"),row["parts"],self.slots,include_null=True)
        return [{"index":i,"offset":offset,"tag":row["parts"][i][0].decode("ascii"),"target":target,"types":kinds}
                for i,offset,target,kinds in edges if i not in opaque]

    def reference_targets(self,path,index,offset,query="",limit=200):
        """Return bounded matching persistent identities, not runtime FormIDs."""
        if type(limit)!=int or not 1<=limit<=1000:raise ValueError("invalid result limit")
        matches=[f for f in self.reference_fields(path) if (f["index"],f["offset"])==(index,offset)]
        if len(matches)!=1:raise ValueError("unsupported reference")
        allowed=matches[0]["types"]
        q=query.casefold();result=[]
        for key,kind in sorted(self.types.items()):
            if allowed and kind not in allowed:continue
            if key.origin not in self.slots.index:continue
            label=""
            paths=self.paths.get(key,())
            row=self.rows[paths[0]] if len(paths)==1 else self.external_records.get(key,{})
            for tag,raw in row.get("parts",()):
                if tag==b"EDID":
                    label=raw.rstrip(bytes(1)).decode("cp1252",errors="replace");break
            if q not in f"{key.origin} {key.local:06X} {kind} {label}".casefold():continue
            result.append({"identity":token(self.profile,key),"origin":key.origin,"local_id":key.local,"signature":kind,"editor_id":label})
            if len(result)>=limit:break
        return result

    def create_or_duplicate(self,revision,operation,**args):
        """Use registered creation templates; never replace existing records."""
        if revision!=self.revision:raise ValueError("stale session")
        from .native_transactions import apply
        if operation not in ("create","duplicate","native_misc","native_key","native_static","native_container","native_duplicate"):
            raise ValueError("unsupported creation operation")
        data=apply(self.profile,self.data,[{"kind":operation,**args}],revision)
        candidate=NativeSession(self.profile,data,self.slots,self.external_types,self.external_records)
        new=set(candidate.paths)-set(self.paths)
        if len(new)!=1 or not set(self.paths)<=set(candidate.paths):
            raise ValueError("creation changed existing identities")
        for key,paths in self.paths.items():
            newer=candidate.paths[key]
            if len(paths)!=len(newer):raise ValueError("creation changed identity multiplicity")
            for before,after in zip(paths,newer):
                a,b=self.node(before),candidate.node(after)
                if a.header!=b.header or a.payload!=b.payload:
                    raise ValueError("creation altered existing record")
        key=next(iter(new))
        if key in self.external_types or len(candidate.paths[key])!=1:raise ValueError("new identity collides with a known record")
        self.__dict__.update(candidate.__dict__)
        return self.identity_token(self.paths[key][0])
