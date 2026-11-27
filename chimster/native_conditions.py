"""Condition operand decoding requires explicit profile and layout."""
from dataclasses import dataclass
import struct

@dataclass(frozen=True)
class Function:
    name: str
    operands: tuple

# Initial common function IDs; candidate definitions require fixture validation.
COMMON={1:Function("GetDistance",("reference","unused")),
        5:Function("GetLocked",("unused","unused")),
        14:Function("GetActorValue",("actor-value","unused")),
        47:Function("GetItemCount",("reference","unused")),
        72:Function("GetIsID",("reference","unused"))}
REGISTRY={p:dict(COMMON) for p in ("oblivion","fallout3","new-vegas","skyrim","skyrim-se","fallout4")}

def decode_operands(profile,function,raw_operands,slots):
    spec=REGISTRY.get(profile,{}).get(function)
    if spec is None or len(raw_operands)!=8:
        return {"function":function,"opaque":raw_operands}
    values=struct.unpack("<II",raw_operands)
    return {"function":function,"name":spec.name,
            "operands":tuple((kind,slots.decode(value) if kind=="reference" else value)
                             for kind,value in zip(spec.operands,values)),
            "raw":raw_operands}
