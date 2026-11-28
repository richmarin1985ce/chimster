"""Shared local font rendering for previews and portable raster assets."""
from io import BytesIO
from pathlib import Path
from .font_library import read_font

def render_text(source,text,size=32,width=720,height=400,transparent=False):
    from PIL import Image,ImageDraw,ImageFont
    if not isinstance(text,str) or len(text)>10000 or not 8<=size<=144 or not 64<=width<=4096 or not 64<=height<=4096:
        raise ValueError("Text or canvas exceeds rendering limits")
    data,_=read_font(source)
    font=ImageFont.truetype(BytesIO(data),size)
    image=Image.new("RGBA",(width,height),(255,255,255,0 if transparent else 255))
    draw=ImageDraw.Draw(image)
    lines=[]
    for paragraph in text.split("\n"):
        line=""
        for word in paragraph.split(" "):
            candidate=(line+" "+word) if line else word
            if line and draw.textlength(candidate,font=font)>width-24:
                lines.append(line);line=word
            else:line=candidate
            if draw.textlength(line,font=font)>width-24:
                raise ValueError("A word is wider than the canvas; reduce font size")
        lines.append(line)
    ascent,descent=font.getmetrics()
    step=ascent+descent+4
    if len(lines)*step>height-24:
        raise ValueError("Text exceeds canvas height; reduce font size")
    for i,line in enumerate(lines):
        draw.text((12,12+i*step),line,font=font,fill=(0,0,0,255),anchor="lt")
    return image

def export_text_png(source,path,text,size,width,height,permission=False):
    if not permission:raise ValueError("Confirm rights to distribute rendered text")
    image=render_text(source,text,size,width,height,True)
    path=Path(path)
    if path.suffix.lower()!=".png":raise ValueError("Choose a PNG filename")
    with path.open("xb") as stream:image.save(stream,format="PNG")
    return path
