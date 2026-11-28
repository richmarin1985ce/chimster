"""Cache original game resources; archive reader supplied by game asset loader."""
from collections import OrderedDict
from pathlib import PurePosixPath
from io import BytesIO
class SessionAssets:
    def __init__(self,reader,budget=64*1024*1024):
        if not 1<=budget<=256*1024*1024:raise ValueError("Invalid cache budget")
        self.reader=reader;self.budget=budget;self.size=0;self.cache=OrderedDict()
    def get(self,path):
        path=path.replace("\\","/")
        if ":" in path or any(p in ("",".","..") for p in path.split("/")):raise ValueError("Unsafe asset path")
        key=path.casefold()
        if key in self.cache:
            self.cache.move_to_end(key);return self.cache[key]
        raw=self.reader(path)
        if not isinstance(raw,bytes) or len(raw)>self.budget:raise ValueError("Invalid or oversized asset")
        while self.size+len(raw)>self.budget:
            _,old=self.cache.popitem(last=False);self.size-=len(old)
        self.cache[key]=raw;self.size+=len(raw);return raw
    def font(self,path,size):
        from PIL import ImageFont
        if PurePosixPath(path).suffix.lower() not in (".ttf",".otf"):raise ValueError("Native bitmap or SWF decoder required")
        if not 6<=size<=256:raise ValueError("Invalid font size")
        return ImageFont.truetype(BytesIO(self.get(path)),size)
    def clear(self):
        self.cache.clear();self.size=0
