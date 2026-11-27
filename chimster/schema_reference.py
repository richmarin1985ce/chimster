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
    target: Identity

def inspect(signature, parts, slots):
    """Return references and coverage; unsupported layouts remain opaque."""
    parts = list(parts)
    sig = signature.encode("ascii")
    if sig in PATTERNS:
        # Validate the entire layout before extracting any exact-layout links.
        try:
            rewrite(sig, parts, lambda raw: raw)
        except (ValueError, UnicodeError, struct.error):
            pass
        else:
            from .remap_schema import OFFSETS
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
                    if target is not None:
                        edges.append(Reference(i, offset, target))
            return edges, ()
    from .record_graph import FIELDS
    edges, opaque = references(signature, parts, slots)
    return [Reference(i, FIELDS[signature, parts[i][0]][1], target)
            for i, target, _ in edges], tuple(opaque)

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
