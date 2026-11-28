"""Classic TES3 reference candidates, not a runtime reference resolver."""
from .native_parser import parse,subrecords

ACTORS={b"NPC_",b"CREA"}
OBJECTS=ACTORS|{b"ACTI",b"DOOR",b"CONT",b"STAT",b"WEAP",b"ARMO",b"CLOT",b"MISC",b"BOOK",b"ALCH",b"INGR",b"LIGH",b"APPA",b"LOCK",b"PROB",b"REPA"}
TYPES=OBJECTS|{b"SPEL",b"ENCH",b"RACE",b"CLAS",b"FACT",b"BODY",b"SCPT",b"LEVI",b"LEVC"}
def string(raw):
    return raw.split(b"\0",1)[0].decode("cp1252")

class Catalog:
    def __init__(self,plugins):
        self.rows={}
        self.plugins=[]
        for plugin,data in plugins:
            if plugin.casefold() in self.plugins:raise ValueError("Duplicate plugin")
            self.plugins.append(plugin.casefold())
            for node in parse("morrowind",data):
                if node.signature not in TYPES:continue
                parts=list(subrecords("morrowind",node))
                ids=[string(v) for k,v in parts if k==b"NAME"]
                if len(ids)!=1 or not ids[0]:continue
                key=(node.signature,ids[0].casefold())
                if any(k==b"DELE" for k,v in parts):
                    self.rows.pop(key,None);continue
                name=next((string(v) for k,v in parts if k==b"FNAM"),"")
                self.rows[key]={"id":ids[0],"name":name,"signature":node.signature,"plugin":plugin}
    def search(self,query="",types=None,limit=100):
        if type(limit)!=int or not 1<=limit<=10000:raise ValueError("Invalid result limit")
        q=query.casefold().strip()
        rows=[r for r in self.rows.values() if (types is None or r["signature"] in types) and (q in r["id"].casefold() or q in r["name"].casefold())]
        rows.sort(key=lambda r:(r["id"].casefold()!=q,not r["id"].casefold().startswith(q),r["id"].casefold(),r["signature"]))
        return [dict(r) for r in rows[:limit]]
    def resolve(self,identity,types=None):
        return [dict(r) for (sig,key),r in self.rows.items() if key==identity.casefold() and (types is None or sig in types)]
    def validate_package(self,tag,properties):
        if tag not in (b"AI_F",b"AI_E",b"AI_A"):return {"status":"not_applicable"}
        target=properties.get("target","")
        rows=self.resolve(target,ACTORS if tag!=b"AI_A" else OBJECTS)
        return {"status":"resolved" if len(rows)==1 else "ambiguous" if rows else "unresolved","target":target,"candidates":rows}
