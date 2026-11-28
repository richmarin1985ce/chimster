# Fallout: Flagstaff
Chimster showcase and New Vegas integration testbed. This demo rebuilds from a text recipe and public USGS 3DEP elevations; no original ESM/ESP or game assets required. Original geographic extent and scale were not recovered. The current 8 km square centered at 35.1983 N, 111.6513 W is a provisional sample, not canon. Candidate region classification uses elevation and slope alone; it does not represent measured vegetation, volcanic deposits, roads or land use. No existing Fallout assets are redistributed.

## Rebuild
From repository root with Python 3.12:
    python -m pip install rasterio==1.4.3 numpy==2.2.6
    python -m chimster flagstaff fetch examples/flagstaff/recipe.json flagstaff-dem.tif
    python -m chimster flagstaff build examples/flagstaff/recipe.json flagstaff-dem.tif flagstaff-demo

The source download is explicit, uses the USGS public 3DEP endpoint and validates TIFF shape, floating-point type, CRS, extent, orientation, elevation range and NoData. A saved input TIFF can be reused offline; the SHA-256 is recorded. USGS updates its live service so identical query parameters may yield updated data; keep the retrieved TIFF and source manifest for exact reproduction. Raster samples are north-up; the mesh reverses rows into positive-north coordinates and subtracts a single minimum elevation datum, with no sculpting or vertical exaggeration. Source pixel spacing ~31.25 m. This is a resampled demo, not the highest-resolution source.

## Output
Open preview.html in any browser for the shaded elevation map, candidate regions, placement overlay and isometric terrain preview with LOD control. Entirely offline. Outputs include original sampled elevations in metres, terrain OBJ at four resolutions, candidate region PNG/JSON, deterministic placement proposals, spatial LOD grouping, six procedural flora recipes with intermediate OBJ/PNG/DDS atlas assets, and build manifest. Rock objects are placeholders only. No playable FNV plugin yet; modern NIF conversion, WRLD/CELL/LAND writing, landscape layers, region objects, navmesh, actual roads, settlements, in-game LOD and validation are next. GECK's documented 1024x1024 16-bit RAW import is not interchangeable with our georeferenced 257-sample terrain; its game-unit mapping, tile boundaries and vertical encoding must be verified before exporting it. No synthetic DEM fallback in the public workflow.

USGS reference: https://elevation.nationalmap.gov/arcgis/rest/services/3DEPElevation/ImageServer
GECK heightmaps: https://geckwiki.com/index.php/Heightmap_Editing
FNV LAND records: https://tes5edit.github.io/fopdoc/FalloutNV/Records/LAND.html
