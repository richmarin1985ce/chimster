"""In-memory structural transactions. No disk writes or semantic certification."""
import hashlib
from .native_parser import parse
from .native_payload_edit import replace,remove,insert_adjacent
from .native_typed_edit import edit

def revision(data):
    return hashlib.sha256(data).hexdigest()

def apply(profile,data,operations,expected_revision,validate=None):
    if revision(data)!=expected_revision:raise ValueError("Stale transaction")
    candidate=data
    for operation in operations:
        args=dict(operation)
        kind=args.pop("kind")
        fn={"replace":replace,"remove":remove,"insert":insert_adjacent,"typed":edit}.get(kind)
        if fn is None:raise ValueError("Unknown operation")
        key="revision"
        candidate=fn(profile,candidate,**args,**{key:revision(candidate)})
    parse(profile,candidate)
    if validate is not None:validate(profile,candidate)
    return candidate

class History:
    def __init__(self,profile,data,limit=32):
        if type(limit)!=int or not 1<=limit<=256:raise ValueError("Invalid history limit")
        parse(profile,data)
        self.profile=profile
        self.data=bytes(data)
        self.limit=limit
        self._undo=[]
        self._redo=[]
    def commit(self,operations,expected_revision,validate=None):
        candidate=apply(self.profile,self.data,operations,expected_revision,validate)
        if candidate!=self.data:
            self._undo.append(self.data)
            self._undo=self._undo[-self.limit:]
            self._redo.clear()
            self.data=candidate
        return self.data
    def undo(self):
        if not self._undo:raise ValueError("Nothing to undo")
        self._redo.append(self.data)
        self.data=self._undo.pop()
        return self.data
    def redo(self):
        if not self._redo:raise ValueError("Nothing to redo")
        self._undo.append(self.data)
        self.data=self._redo.pop()
        return self.data
