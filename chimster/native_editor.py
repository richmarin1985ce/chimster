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
                        if self.profile!="morrowind" and struct.unpack_from("<I",node.header,8)[0]&0x20:
                            self.types.pop(key,None)
                        else:self.types[key]=node.signature.decode("ascii")
        walk(self.nodes)
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

    def validation_summary(self):
        issues=self.validate()
        counts={}
        for issue in issues:
            counts[issue[0]]=counts.get(issue[0],0)+1
        return {"records":len(self.rows),"issues":issues,"counts":counts,
                "complete":not issues,"revision":self.revision}

    def remap_preview(self,path,destination):
        node=self.node(path)
        return plan(self.profile,node.signature.decode("ascii"),
                    self.rows[path]["parts"],self.slots,destination)

    def apply(self,revision,edits):
        """All edits succeed or original session remains unchanged."""
        if revision!=self.revision:
            raise ValueError("stale session")
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
