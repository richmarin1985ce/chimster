"""Resolve explicit localized fields without guessing table assignments."""
import struct
from .compatibility_strings import parse

class Catalog:
    def __init__(self,tables,encoding="utf-8"):
        self.tables={}
        for kind,data in tables.items():
            key=kind.upper().lstrip(".")
            if key in self.tables:raise ValueError("Duplicate table")
            self.tables[key]=parse(data,key,encoding)
    def resolve(self,raw,kind,localized=True,encoding="cp1252"):
        if not localized:
            if not raw.endswith(b"\0") or b"\0" in raw[:-1]:raise ValueError("Invalid inline text")
            return {"text":raw[:-1].decode(encoding),"resolved":True,"id":None}
        if len(raw)!=4:raise ValueError("Invalid localized ID")
        key=struct.unpack("<I",raw)[0]
        table=self.tables.get(kind.upper().lstrip("."),{})
        return {"text":table.get(key),"resolved":key in table,"id":key}
