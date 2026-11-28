"""Shared reference inspection for known generated FNV layouts.

Uses the same validation and offsets as master remapping, including conditional
PERK fields. This is not a complete native schema or deletion safety proof.
"""
from dataclasses import dataclass
from collections import defaultdict, deque
from .remap_schema import PATTERNS, rewrite
from .record_graph import references, Identity
import struct

@dataclass(frozen=True)
class Reference:
    field: int
    offset: int
    target: Identity | None
    expected_types: tuple = ()

def inspect(signature, parts, slots, include_null=False):
    """Return references and coverage; unsupported layouts remain opaque."""
    parts = list(parts)
    sig = signature.encode("ascii")
    from .quest_remap_schema import PATTERNS as QUEST_PATTERNS, fields as quest_fields
    from .world_remap_schema import PATTERNS as WORLD_PATTERNS, fields as world_fields
    if sig==b"NAVM":
        from .fnv_navmesh import inspect as inspect_navmesh
        try:report,offsets=inspect_navmesh(parts)
        except (ValueError,struct.error):return [],tuple(range(len(parts)))
        edges=[]
        for i,offset,kinds in offsets:
            target=slots.decode(struct.unpack_from("<I",parts[i][1],offset)[0])
            if target is not None or include_null:edges.append(Reference(i,offset,target,kinds))
        opaque=tuple(i for i,(tag,raw) in enumerate(parts) if tag in (b"NVCA",b"NVGD",b"NVEX",b"NVDP"))
        if report["issues"]:opaque=tuple(range(len(parts)))
        return edges,opaque
    exact = quest_fields if sig in QUEST_PATTERNS else world_fields if sig in WORLD_PATTERNS else None
    if exact is not None:
        try:
            offsets = exact(sig, parts)
        except (ValueError, UnicodeError, struct.error):
            pass
        else:
            edges = []
            for i, offset, kinds in offsets:
                target = slots.decode(struct.unpack_from("<I", parts[i][1], offset)[0])
                if target is not None or include_null:
                    edges.append(Reference(i, offset, target, kinds))
            return edges, ()
    if sig in PATTERNS:
        # Validate the entire layout before extracting any exact-layout links.
        try:
            rewrite(sig, parts, lambda raw: raw)
        except (ValueError, UnicodeError, struct.error):
            pass
        else:
            from .remap_schema import OFFSETS
            from .record_graph import FIELDS
            edges = []
            perk = None
            for i, (tag, raw) in enumerate(parts):
                offsets = OFFSETS.get(sig, {}).get(tag, ())
                if sig == b"PERK":
                    if tag == b"PRKE":
                        perk = raw[0]
                    elif tag == b"DATA" and perk is not None:
                        offsets = (0,)
                for offset in offsets:
                    target = slots.decode(struct.unpack_from("<I", raw, offset)[0])
                    if target is not None or include_null:
                        spec = FIELDS.get((signature, tag))
                        kinds = tuple(sorted(spec[2])) if spec and spec[1] == offset and spec[2] else ()
                        if sig == b"PERK" and tag == b"DATA":
                            kinds = ("QUST",) if perk == 0 else ("SPEL",)
                        elif sig == b"ALCH" and tag == b"ENIT":
                            kinds = ("SPEL",) if offset == 8 else ("SOUN",)
                        edges.append(Reference(i, offset, target, kinds))
            return edges, ()
    from .record_graph import FIELDS
    edges, opaque = references(signature, parts, slots)
    result = [Reference(i, FIELDS[signature, parts[i][0]][1], target, tuple(sorted(kinds or ())))
              for i, target, kinds in edges]
    if include_null:
        for i, (tag, raw) in enumerate(parts):
            spec = FIELDS.get((signature, tag))
            if spec and len(raw) == spec[0] and struct.unpack_from("<I", raw, spec[1])[0] == 0:
                result.append(Reference(i, spec[1], None, tuple(sorted(spec[2] or ()))))
    return result, tuple(opaque)

class ReferenceIndex:
    """In-memory bidirectional index of caller-selected winning records.

    Replacing a record removes its old edges. Traversal is cycle-safe and
    includes unresolved targets; incomplete coverage is reported separately.
    """
    def __init__(self):
        self.forward = {}
        self.reverse = defaultdict(set)
        self.opaque = {}

    def add(self, owner, signature, parts, slots):
        edges, opaque = inspect(signature, parts, slots)
        for edge in self.forward.get(owner, ()):
            self.reverse[edge.target].discard(owner)
            if not self.reverse[edge.target]:
                del self.reverse[edge.target]
        self.forward[owner] = tuple(edges)
        self.opaque[owner] = opaque
        for edge in edges:
            self.reverse[edge.target].add(owner)

    def closure(self, root, reverse=False):
        seen = {root}
        queue = deque([root])
        while queue:
            node = queue.popleft()
            neighbors = (self.reverse.get(node, ()) if reverse else
                         (edge.target for edge in self.forward.get(node, ())))
            for neighbor in neighbors:
                if neighbor not in seen:
                    seen.add(neighbor)
                    queue.append(neighbor)
        seen.remove(root)
        return sorted(seen)

    def review(self, root):
        dependencies = self.closure(root)
        return {"dependencies": dependencies,
                "dependents": self.closure(root, reverse=True),
                "unindexed": [x for x in [root, *dependencies] if x not in self.forward],
                "opaque": sorted(x for x in [root, *dependencies] if self.opaque.get(x)),
                "global_opaque": sorted(x for x, fields in self.opaque.items() if fields)}
