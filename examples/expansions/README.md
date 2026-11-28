# Baltimore and Nantucket geographic source projects

This is a reusable extension of the Flagstaff source workflow, not a native worldspace exporter. The current environment cannot resolve elevation.nationalmap.gov or www2.census.gov; no source TIFF or road ZIP has been acquired here. No synthetic geographic data replaces it.

## Run locally from the repository root
Use Python 3.12 with rasterio, numpy, fiona, shapely and pyproj. These are development/import libraries, not additional external modding applications. Integrate them into Chimster packaging before a user-facing release. Network access is explicit, only during acquisition. Do not disable TLS or substitute unverified sources.

    python examples/expansions/geography.py baltimore plan
    python examples/expansions/geography.py baltimore fetch --source local-data/baltimore
    python examples/expansions/geography.py baltimore import --source local-data/baltimore --out local-data/baltimore-import
    python examples/expansions/geography.py nautica plan
    python examples/expansions/geography.py nautica fetch --source local-data/nautica
    python examples/expansions/geography.py nautica import --source local-data/nautica --out local-data/nautica-import

Retain the raw sources, SHA-256 and source version. Use a new output directory for each import. Do not commit bulky sources by default. The USGS service may change data over time: only retained source files reproduce an exact import. The DEM is resampled to 10 m spacing, not necessarily native 10 m source resolution. Road data is pinned to Census 2025 TIGER/Line All Roads; actual file availability and geometry remain unverified. County coverage and edge gaps must be audited before world construction.

## Provisional scaling
| Project | projected source grid | horizontal scale | approximate full rectangular game-design extent |
|---|---|---|---|
| Baltimore | 2637 x 2821 (UTM18N) | 0.35 | 9.23 x 9.87 km |
| Nautica | 2792 x 2257 (UTM19N) | 0.70 | 19.54 x 15.80 km |
These include water, not playable land area. Elevation values remain in source meters. Game units and vertical scaling are separate decisions. Local source origin is the southwest outer pixel edge; DEM sample centers are offset by half a pixel. NoData is explicit and not synonymous with water. Separate shoreline and water surfaces are required.

## Road authoring design
TIGER roads are source evidence, not a postwar network or a navigable graph. Preserve unmodified source centerlines, names, classes and source IDs; use generated copies for gameplay. Deduplicate coincident segments, classify primary/secondary/local roads and paths, check county seams, preserve grade-separated crossings, simplify only within a measured tolerance, and mark uncertain geometry for review. Do not infer bridge elevations from bare-earth DEM. Author collapsed bridges, blocked streets and alternate routes only in the design layer. Validate connectivity for chosen quests.

### Baltimore
Preserve Inner Harbor shape, downtown arterial relationships, industrial waterfront routes and residential block structure. Proposed regional spines: harbor-to-downtown, east industrial waterfront, west/inland residential corridors, and south harbor crossing approaches. Initial slice: harbor market/warehouse/service tunnel/refuge. Prioritize block outlines and street junctions before decorative detail; retain selective neighborhood street grids and simplify redundant minor roads away from quest areas. Road widths and building scale are independently authored, not multiplied by regional compression.

### Nautica
Preserve island coastline and town street grain. Candidate travel spines: Nantucket town/harbor toward Surfside, Madaket, Siasconset and Polpis; local town lanes and dune paths remain separate from regional connectors. Initial slice: arrival dock, two town streets, boathouse, marsh path and beacon. Do not imply a vehicle bridge from the mainland. Keep marsh and dune tracks selectively traversable; use authored marine travel connections, not TIGER road segments across water.

## Next integration gates
1. Acquire and inspect actual DEM, county road archives and shoreline polygons.
2. Generate source maps/overlays; measure coverage, terrain range and gaps. Compare with source geography.
3. Develop street graph review, deduplication, junction and bridge/grade separation tools, road surface and terrain alignment.
4. Build graybox street blocks, settlements and coastlines, then test traversal at target scale.
5. Convert independently to native FO3 and FO4 world/cell/land/road records and assets; no relabeled FNV export.
6. Validate native world, collision, LOD, navigation, weather/water and runtime load in each retail game.

Sources: https://elevation.nationalmap.gov/arcgis/rest/services/3DEPElevation/ImageServer
and https://www.census.gov/cgi-bin/geo/shapefiles/index.php?layergroup=Roads&year=2025 .
