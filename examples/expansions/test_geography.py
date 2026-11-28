"""Run explicitly: python -m unittest discover -s examples/expansions -p 'test_*.py'."""
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
import geography as g

try:
    import numpy as np
    import rasterio
    from rasterio.transform import from_origin
    import fiona
    import shapely
    import pyproj
except ImportError:
    HAS_GIS=False
else:
    HAS_GIS=True

@unittest.skipUnless(HAS_GIS,"optional GIS import libraries unavailable")
class GeographyTest(unittest.TestCase):
    def test_distinct_plans(self):
        b,n=g.plan("baltimore"),g.plan("nautica")
        self.assertEqual((b["epsg"],n["epsg"]),(32618,32619))
        self.assertEqual((len(b["urls"]),len(n["urls"])),(4,2))
        self.assertLess(b["xy_scale"],n["xy_scale"])
        for p in (b,n):
            x,y,X,Y=p["bounds"]
            self.assertEqual(X-x,p["width"]*10)
            self.assertEqual(Y-y,p["height"]*10)
            self.assertLessEqual(max(p["width"],p["height"]),4096)

    def test_coastal_mask_and_negative_elevation_preserved(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/"dem.tif"
            spec={"width":2,"height":2,"epsg":32619,"bounds":[100,200,120,220]}
            with rasterio.open(p,"w",driver="GTiff",width=2,height=2,count=1,
                    dtype="float32",crs="EPSG:32619",transform=from_origin(100,220,10,10),
                    nodata=-9999) as ds:
                ds.write(np.array([[3,-9999],[-1,7]],dtype="float32"),1)
            meta=g.validate_dem(p,spec)
            self.assertEqual(meta["valid_samples"],3)
            self.assertEqual(meta["missing_samples"],1)
            self.assertEqual(meta["min_m"],-1)
            with self.assertRaises(ValueError):
                g.validate_dem(p,{**spec,"epsg":32618})

    def test_missing_sources_do_not_publish_output(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d)
            with self.assertRaises(Exception):
                g.import_sources("nautica",root,root/"out")
            self.assertFalse((root/"out").exists())

if __name__=="__main__":
    unittest.main()
