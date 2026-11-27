"""Explicit allocation policy; runtime slots are not disk master slots."""
from dataclasses import dataclass
from collections import defaultdict
import struct
from .formids import KEY

@dataclass(frozen=True)
class AllocationPolicy:
    minimum: int = 0x800
    maximum: int = 0xffffff
    def __post_init__(self):
        if not 1 <= self.minimum <= self.maximum <= 0xffffff:
            raise ValueError("invalid allocation range")

def policy(kind="full", extended=False):
    if kind not in ("full", "light", "medium"):
        raise ValueError("unknown plugin class")
    if extended and kind != "light":
        raise ValueError("extended range only modeled for light plugins")
    return AllocationPolicy(1 if extended else 0x800,
                            {"full":0xffffff,"light":0xfff,"medium":0xffff}[kind])

def header_cursor(hedr):
    if len(hedr) != 12:
        raise ValueError("invalid TES4 HEDR length")
    return struct.unpack_from("<I", hedr, 8)[0] & 0xffffff

def reserve_hierarchy(ledger, parents, allocation=AllocationPolicy(), cursor=0, occupied=()):
    """Reserve new keys by breadth-first ownership order, atomically.
    This is a proposed editor policy, not a claim about native CK allocation.
    Existing and retired identities remain stable.
    """
    parents=dict(parents)
    if any(not isinstance(k,str) or not KEY.fullmatch(k) for k in parents):
        raise ValueError("invalid key")
    children=defaultdict(list)
    for key,parent in parents.items():
        if parent is not None and parent not in parents:
            raise ValueError("unknown parent")
        children[parent].append(key)
    order=sorted(children[None])
    for key in order:
        order.extend(sorted(children[key]))
    if len(order)!=len(parents):
        raise ValueError("ownership cycle")
    if set(parents)&ledger.active:
        raise ValueError("active key")
    if type(cursor) is not int or not 0<=cursor<=0x1000000:
        raise ValueError("invalid cursor")
    occupied=set(occupied)
    if any(type(i) is not int or not 1<=i<=allocation.maximum for i in occupied):
        raise ValueError("invalid occupied ID")
    if any(not 1<=i<=allocation.maximum for i in ledger.entries.values()):
        raise ValueError("existing identity outside policy")
    used=set(ledger.entries.values()) | occupied
    nxt=max(ledger.next,cursor,allocation.minimum,max(used,default=0)+1)
    new={}
    for key in order:
        if key not in ledger.entries:
            if nxt>allocation.maximum:
                raise ValueError("identity space exhausted")
            new[key]=nxt
            nxt+=1
    ledger.entries.update(new)
    ledger.used.update(new.values())
    ledger.next=nxt
    return {key:ledger.entries[key] for key in order}
