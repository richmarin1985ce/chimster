"""Native font references are independent of desktop preview fonts."""
import re
from html import escape
from html.parser import HTMLParser

SKYRIM={"skyrim","skyrimse","skyrimvr"}
MORROWIND={"morrowind","openmw"}
OBLIVION=("Kingthings_Regular","Kingthings_Shadowed","Tahoma_Bold_Small","Daedric_Font","Handwritten")
SKY=("$SkyrimBooks","$HandwrittenFont","$DaedricFont","$FalmerFont","$DwemerFont","$MageScriptFont")
MW=("Magic Cards","Century Gothic","Daedric")

def choices(game):
    if game in MORROWIND:return MW
    if game=="oblivion":return tuple(str(n) for n in range(1,6))+OBLIVION
    if game in SKYRIM:return SKY
    return ()

def font_tag(game,face):
    if face not in choices(game):raise ValueError("Font not in documented authoring subset")
    return '<FONT face="'+escape(face,quote=True)+'">'

def preview_family(face):
    f=face.casefold()
    if "hand" in f or f=="5":return "cursive"
    if "tahoma" in f or "gothic" in f or f=="3":return "sans-serif"
    return "serif"

def read_fontconfig(text):
    """Read declared Skyrim aliases and libraries without modifying source."""
    libraries=[];aliases={}
    for line in text.splitlines():
        m=re.fullmatch(r'\s*fontlib\s+"([^"]+)"\s*',line,re.I)
        if m:libraries.append(m[1]);continue
        m=re.fullmatch(r'\s*map\s+"([^"]+)"\s*=\s*"([^"]+)"\s+(\w+)\s*',line,re.I)
        if m:aliases[m[1]]=(m[2],m[3])
    return {"libraries":libraries,"aliases":aliases}

class FontReader(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=False);self.faces=[]
    def handle_starttag(self,tag,attrs):
        if tag=="font":
            self.faces.extend(v for k,v in attrs if k=="face" and v is not None)

def references(body):
    parser=FontReader();parser.feed(body);parser.close()
    return tuple(dict.fromkeys(parser.faces))
