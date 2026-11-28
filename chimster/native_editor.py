"""Editor-facing native session. No disk writes or implicit master changes."""
from hashlib import sha256
from .native_parser import parse
from .native_catalog import inspect_node
from .native_serialization import serialize, replace_payload
from .native_edit import edit_reference
from .native_dependencies import Dependencies
from .native_remap_plan import plan

class NativeSession:
    def __init__(self, profile, data, slots, external_types=None):
        self.profile=profile
        self.data=bytes(data)
        self.slots=slots
        self.external_types=dict(external_types or {})
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
                        self.types[key]=node.signature.decode("ascii")
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
        self.dependencies=Dependencies(edges,self.paths,opaque)
        self.revision=sha256(self.data).hexdigest()

    def node(self,path):
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
            if row["opaque"]:
                issues.append(("incomplete-schema",path,tuple(row["opaque"])))
            for index,offset,target,kinds in row["edges"]:
                actual=self.types.get(target)
                if actual is None:
                    issues.append(("unresolved-target",path,index,offset,target))
                elif kinds and actual not in kinds:
                    issues.append(("wrong-target-type",path,index,offset,target,actual,kinds))
        return issues

    def remap_preview(self,path,destination):
        node=self.node(path)
        return plan(self.profile,node.signature.decode("ascii"),
                    self.rows[path]["parts"],self.slots,destination)

    def apply(self,revision,edits):
        """All edits succeed or original session remains unchanged."""
        if revision!=self.revision:
            raise ValueError("stale session")
        candidate=NativeSession(self.profile,self.data,self.slots,self.external_types)
        for path,index,expected,target in edits:
            path=tuple(path)
            node=candidate.node(path)
            if path not in candidate.rows:
                raise ValueError("not an editable record")
            updated=edit_reference(self.profile,node,self.slots,index,expected,target,candidate.types)
            data=replace_payload(self.profile,candidate.data,path,node.payload,updated.payload)
            candidate=NativeSession(self.profile,data,self.slots,self.external_types)
        self.__dict__.update(candidate.__dict__)
        return self.revision
