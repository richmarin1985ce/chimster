"""Classic TES3 binary layout facts independently implemented in Python.
References: OpenMW/openmw components/esm3/loadnpc.cpp, loadcrea.cpp,
loadnpc.hpp, loadcrea.hpp, aipackage.hpp (GPL-3.0 repository).
No OpenMW implementation code incorporated.
"""
import struct

ATTRIBUTES=("strength","intelligence","willpower","agility","speed","endurance","personality","luck")
SKILLS=("block","armorer","medium_armor","heavy_armor","blunt_weapon","long_blade","axe","spear","athletics","enchant","destruction","alteration","illusion","conjuration","mysticism","restoration","alchemy","unarmored","security","sneak","acrobatics","light_armor","short_blade","marksman","mercantile","speechcraft","hand_to_hand")

def layout(signature,size):
    fields={}
    def add(names,offset,fmt):
        for i,name in enumerate(names):fields[name]=(offset+i*struct.calcsize(fmt),fmt)
    if signature==b"NPC_" and size in (12,52):
        add(("level",),0,"<h")
        if size==52:
            add(ATTRIBUTES,2,"<B");add(SKILLS,10,"<B")
            add(("health","magicka","fatigue"),38,"<H")
        add(("disposition","reputation","rank"),44 if size==52 else 2,"<B")
        add(("gold",),size-4,"<i")
    elif signature==b"CREA" and size==96:
        add(("type","level")+ATTRIBUTES+("health","magicka","fatigue","soul","combat","magic","stealth","attack1_min","attack1_max","attack2_min","attack2_max","attack3_min","attack3_max","gold"),0,"<i")
    else:raise ValueError("Unsupported actor layout")
    return fields

def decode(signature,raw):
    return {k:struct.unpack_from(fmt,raw,offset)[0] for k,(offset,fmt) in layout(signature,len(raw)).items()}

def edit(signature,raw,**changes):
    fields=layout(signature,len(raw));out=bytearray(raw)
    if set(changes)-set(fields):raise ValueError("Unsupported actor property")
    for k,v in changes.items():
        if type(v)!=int or v<0 or (k=="type" and v>3):raise ValueError("Invalid "+k)
        offset,fmt=fields[k]
        try:struct.pack_into(fmt,out,offset,v)
        except struct.error as e:raise ValueError("Actor property out of range") from e
    if signature==b"CREA":
        values=decode(signature,out)
        for i in range(1,4):
            if values[f"attack{i}_min"]>values[f"attack{i}_max"]:raise ValueError("Inverted attack range")
    return bytes(out)

def ai_decode(raw):
    if len(raw)!=12:raise ValueError("Invalid AIDT")
    return dict(zip(("hello","fight","flee","alarm"),struct.unpack_from("<HBBB",raw)))

def ai_edit(raw,**changes):
    values=ai_decode(raw)
    if set(changes)-set(values):raise ValueError("Unknown AI property")
    for k,v in changes.items():
        if type(v)!=int or not 0<=v<=(65535 if k=="hello" else 100):raise ValueError("Invalid AI property")
    values.update(changes)
    return struct.pack("<HBBB",*(values[k] for k in ("hello","fight","flee","alarm")))+raw[5:]

FLAGS={b"NPC_":("female","essential","respawn","base","autocalc"),b"CREA":("bipedal","respawn","weapon","base","swims","flies","walks","essential")}
def flags_edit(signature,raw,**changes):
    if len(raw)!=4 or signature not in FLAGS:raise ValueError("Invalid actor flags")
    names=FLAGS[signature];value=int.from_bytes(raw,"little")
    for k,v in changes.items():
        if k not in names or type(v)!=bool:raise ValueError("Invalid actor flag")
        bit=1<<names.index(k);value=(value&~bit)|(bit if v else 0)
    return struct.pack("<I",value)
