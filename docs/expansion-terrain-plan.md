# Expansion terrain production
Skyrim's expansion is The Pits (Peryite), replacing Realm of Order/Jyggalag in earlier planning. Oblivion remains The Hunting Grounds. Six original expansion testbeds, each targeting 10–15 hours main story, 20–30 total, and 25–40 locations.

| Project | Terrain | Source |
|---|---|---|
| Morrowind Coldharbour | Distorted volcanic basin, faults, mountains | Original procedural |
| Oblivion The Hunting Grounds | Island-like highlands, forest valleys, river corridors | Original procedural |
| Skyrim The Pits | Mineral terraces, deep intersecting ravines, toxic channels | Original procedural |
| Fallout Baltimore | Harbor, urban lowlands and inland hills | USGS 3DEP |
| Fallout Route 66 Flagstaff | Existing DEM testbed | Existing recipe |
| Fallout: Nautica | Nantucket dunes, moors, wetlands and coastline | USGS 3DEP |

Initial procedural drafts use 513x513 float elevations, 16 m sample spacing, seeds 81, 93, 117 respectively. These are independent source maps, not native plugins. Tune playable scale after traversal testing.

USGS acquisition: https://apps.nationalmap.gov/downloader/ ; public-domain 1/3 arc-second bare-earth elevation, approximately 10 m native resolution. Suggested initial WGS84 bounding boxes (west,south,east,north): Baltimore [-76.75,39.18,-76.45,39.43], Nantucket [-70.27,41.20,-69.94,41.40]. Crop/reproject, preserve nodata mask, retain shoreline separately, resample to consistent metric grid, document vertical datum and source. Never treat missing ocean elevations as verified bathymetry. Native FO3 and FO4 exports require independent validation; do not relabel FNV output.

Status: preliminary procedural maps generated outside repository; USGS download blocked by DNS in execution environment. No retail game assets or promotional claims of native engine rendering.
