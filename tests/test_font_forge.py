import tempfile
import tkinter
import unittest
from pathlib import Path
from chimster.font_forge import create
from chimster.font_library import FontLibrary, drop_paths, read_font, MAX_BYTES

class FontForgeTests(unittest.TestCase):
    def test_create_import_duplicate_and_reload(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp)
            font=root/"My Font.ttf"
            create("Test Family",{65:[[(0,0),(300,700),(600,0)]]},font)
            library=FontLibrary(root/"library")
            target,info=library.import_font(font)
            self.assertEqual(info["family"],"Test Family")
            self.assertEqual(info["characters"],2)
            self.assertEqual(library.import_font(font)[0],target)
            self.assertEqual(len(list(FontLibrary(root/"library").entries())),1)
            self.assertEqual(font.read_bytes(),target.read_bytes())
    def test_reject_bad_and_oversize(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp)
            bad=root/"invalid.otf"
            bad.write_bytes(b"not a font")
            with self.assertRaises(ValueError):
                FontLibrary(root/"library").import_font(bad)
            self.assertFalse((root/"library").exists())
            with bad.open("wb") as stream:
                stream.truncate(MAX_BYTES+1)
            with self.assertRaises(ValueError):
                read_font(bad)
    def test_tcl_drop_paths(self):
        root=tkinter.Tcl()
        self.assertEqual(drop_paths(root,"{/tmp/My Font.ttf} /tmp/other.otf"),(Path("/tmp/My Font.ttf"),Path("/tmp/other.otf")))

    def test_quadratic_project_roundtrip(self):
        from chimster.font_project import save_project,load_project,segments
        from fontTools.ttLib import TTFont
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp)
            project=root/"curves.json"
            glyphs={65:[[(0,0,True),(300,700,False),(600,0,True)]]}
            save_project(project,"Curve Family",glyphs)
            family,loaded=load_project(project)
            self.assertEqual((family,loaded),("Curve Family",glyphs))
            self.assertEqual(list(segments(loaded[65][0]))[0],((0,0),(300,700),(600,0)))
            font=root/"curves.ttf"
            create(family,loaded,font)
            with TTFont(font) as f:
                g=f["glyf"][f.getBestCmap()[65]]
                self.assertIn(0,[flag & 1 for flag in g.flags])
    def test_reject_invalid_curve_and_project(self):
        from chimster.font_project import save_project,load_project
        with tempfile.TemporaryDirectory() as temp:
            path=Path(temp)/"bad.json"
            with self.assertRaises(ValueError):
                save_project(path,"Test",{65:[[(0,0,False),(1,1,True),(2,2,True)]]})
            self.assertFalse(path.exists())
            path.write_text('{"version":1,"family":"Test","glyphs":{"065":[]}}')
            with self.assertRaises(ValueError):load_project(path)

    def test_otf_import(self):
        from fontTools.fontBuilder import FontBuilder
        from fontTools.pens.t2CharStringPen import T2CharStringPen
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp)
            path=root/"Example.otf"
            names=[".notdef","A"]
            fb=FontBuilder(1000,isTTF=False)
            fb.setupGlyphOrder(names)
            fb.setupCharacterMap({65:"A"})
            glyphs={}
            for name in names:
                pen=T2CharStringPen(600,None)
                if name=="A":
                    pen.moveTo((20,0))
                    pen.lineTo((300,700))
                    pen.lineTo((580,0))
                    pen.closePath()
                glyphs[name]=pen.getCharString()
            fb.setupCFF("Example-Regular",{"FullName":"Example Regular","FamilyName":"Example","Weight":"Regular"},glyphs,{})
            fb.setupHorizontalMetrics({name:(600,20 if name=="A" else 0) for name in names})
            fb.setupHorizontalHeader(ascent=800,descent=-200)
            fb.setupNameTable({"familyName":"Example","styleName":"Regular","uniqueFontIdentifier":"Example Regular","fullName":"Example Regular","psName":"Example-Regular"})
            fb.setupOS2(sTypoAscender=800,sTypoDescender=-200,usWinAscent=1000,usWinDescent=200)
            fb.setupPost()
            fb.save(path)
            target,info=FontLibrary(root/"library").import_font(path)
            self.assertEqual(info["format"],"OTF")
            self.assertEqual(target.read_bytes(),path.read_bytes())

    def test_freehand_pressure_and_export(self):
        from chimster.font_strokes import Sample,outline
        from chimster.font_render import render_text,export_text_png
        from PIL import Image
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp)
            contour=outline([Sample(100,100,0),Sample(300,100,1),Sample(500,100,None)],100,0)
            self.assertEqual(contour[0][1],110)
            self.assertEqual(contour[1][1],150)
            font=root/"stroke.ttf"
            create("Stroke",{65:[contour]},font)
            image=render_text(font,"A A",32,200,100,True)
            self.assertEqual(image.size,(200,100))
            self.assertEqual(image.getpixel((0,0))[3],0)
            self.assertIsNotNone(image.getbbox())
            target=root/"asset.png"
            with self.assertRaises(ValueError):export_text_png(font,target,"A",32,200,100)
            export_text_png(font,target,"A",32,200,100,True)
            with Image.open(target) as result:self.assertEqual(result.mode,"RGBA")
            with self.assertRaises(FileExistsError):export_text_png(font,target,"A",32,200,100,True)
            with self.assertRaises(ValueError):outline([Sample(1,1,2),Sample(10,10)])

    def test_spacing_kerning_and_outline_copy(self):
        from chimster.font_project import save_project,load_project
        from chimster.font_metrics import import_outline
        from fontTools.ttLib import TTFont
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);font=root/"metrics.ttf";project=root/"metrics.json"
            glyphs={65:[[(0,0),(300,700),(600,0)]],86:[[(0,700),(300,0),(600,700)]]}
            advances={65:680,86:700,32:300};kerning={(65,86):-80}
            save_project(project,"Metrics",glyphs,advances,kerning)
            family,loaded,a,k=load_project(project,True)
            self.assertEqual((a,k),(advances,kerning))
            create(family,loaded,font,a,k)
            with TTFont(font) as f:
                self.assertEqual(f["hmtx"]["uni0041"][0],680)
                self.assertIn("GPOS",f)
                lookup=f["GPOS"].table.LookupList.Lookup[0]
                self.assertEqual(lookup.SubTable[0].PairSet[0].PairValueRecord[0].Value1.XAdvance,-80)
            before=font.read_bytes()
            with self.assertRaises(ValueError):import_outline(font,"A")
            contours,width=import_outline(font,"A",True)
            self.assertEqual(width,680)
            self.assertEqual(len(contours),1)
            self.assertEqual(font.read_bytes(),before)
            with self.assertRaises(ValueError):create("Invalid",glyphs,root/"invalid.ttf",{65:-1})
