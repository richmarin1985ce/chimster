import unittest,struct
from chimster.texture_processing import compress,dds,height_alpha,coverage_mips,coverage
class TextureProcessingTests(unittest.TestCase):
    def test_blocks(self):
        raw=bytes([255,0,0,255])*16
        self.assertEqual(len(compress(4,4,raw,"BC1")),8)
        self.assertEqual(len(compress(4,4,raw,"BC3")),16)
        raw=bytes([255,0,0,0])*16
        self.assertEqual(compress(4,4,raw,"BC1A"),struct.pack("<HHI",0,0,0xffffffff))
        blob=dds(4,4,raw,"BC3")
        self.assertEqual(blob[84:88],b"DXT5");self.assertEqual(len(blob),128+3*16)
    def test_coverage_and_height(self):
        raw=bytes([255,255,255,255,255,255,255,0])*8
        levels=coverage_mips(4,4,raw);self.assertEqual(len(levels),3)
        self.assertEqual(height_alpha(4,4,raw,bytes(range(16)))[3::4],bytes(range(16)))
        self.assertEqual(coverage(raw,128),.5)
