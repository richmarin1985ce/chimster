"""Portable TrueType authoring; game registration is a separate step."""
from pathlib import Path
import json
from .font_project import validate, draw_outline
from io import BytesIO

def inspect(path):
    from fontTools.ttLib import TTFont
    p=Path(path)
    if p.stat().st_size>32*1024*1024:raise ValueError("Font exceeds size limit")
    with TTFont(p) as f:
        if "glyf" not in f:raise ValueError("Expected TrueType outlines")
        return {"family":f["name"].getDebugName(1),"glyphs":len(f.getBestCmap() or {}),
                "embedding_flags":f["OS/2"].fsType,"license":f["name"].getDebugName(13)}

def create(family,glyphs,path):
    """Create TrueType outlines from polygon or quadratic control points in em units."""
    from fontTools.fontBuilder import FontBuilder
    from fontTools.pens.ttGlyphPen import TTGlyphPen
    glyphs=validate(family,glyphs)
    outlines={".notdef":TTGlyphPen(None).glyph(),"space":TTGlyphPen(None).glyph()}
    cmap={32:"space"}
    for cp,contours in glyphs.items():
        pen=TTGlyphPen(None)
        for contour in contours:
            draw_outline(pen,contour)
        name=f"uni{cp:04X}";outlines[name]=pen.glyph();cmap[cp]=name
    fb=FontBuilder(1000,isTTF=True)
    fb.setupGlyphOrder(list(outlines));fb.setupCharacterMap(cmap);fb.setupGlyf(outlines)
    fb.setupHorizontalMetrics({n:(500 if n=="space" else 1000,0 if not g.numberOfContours else g.xMin) for n,g in outlines.items()})
    fb.setupHorizontalHeader(ascent=800,descent=-200)
    fb.setupNameTable({"familyName":family,"styleName":"Regular","uniqueFontIdentifier":family+" Regular","fullName":family+" Regular","psName":family.replace(" ","")+"-Regular"})
    fb.setupOS2(sTypoAscender=800,sTypoDescender=-200,usWinAscent=1000,usWinDescent=200)
    fb.setupPost()
    buf=BytesIO();fb.save(buf)
    with Path(path).open("xb") as out:out.write(buf.getvalue())
    return inspect(path)

def export_font(source,folder,license_text,permission=False):
    info=inspect(source)
    if not permission or not license_text.strip():raise ValueError("Confirm redistribution rights and supply license text")
    if info["embedding_flags"] & 2:raise ValueError("Restricted embedding; review font license")
    target=Path(folder);target.mkdir(parents=True,exist_ok=False)
    name=Path(source).name
    (target/name).write_bytes(Path(source).read_bytes())
    (target/"LICENSE.txt").write_text(license_text,encoding="utf-8")
    (target/"font-manifest.json").write_text(json.dumps({"file":name,"font":info,"game_registration":"pending"},indent=2),encoding="utf-8")
    return target/name
