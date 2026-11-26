# Native worldspace experiment
New Vegas masterless ESP fixture writer creates a new WRLD, persistent CELL, exterior CELL records, nested block/sub-block groups and LAND records with height deltas, normals and white vertex colors. Independent game or xEdit verification is required; no actual game-ready claim. No master assets, texture references, climate, navmesh, placed objects or LOD tile records. Default land flags and optional fields remain subject to verification. The writer does not modify existing plugins.
## Terrain
Portable square grid of 32*cells+1 samples, south-to-north rows. Shared edges are sliced from the same grid. Sculpting is a pure brush operation with bounded undo/redo history; there is no brush UI yet. Globally quantize to eight-game-unit height increments and reject signed-byte delta overflow rather than silently clamp. Normals are calculated from the shared global grid. One FNV cell is 4096 units, 32 intervals of 128 units. Physical scale is explicitly derived from input sample spacing; the Flagstaff demo uses 31.25 m source spacing, meaning 4.096 game units per meter and 8 cells across the 8 km area, not real-world game scale. A constant source datum is subtracted; optional vertical scale is explicit. Source DEM is untouched. Quantization error is reported in game units.
    python -m chimster fnv-world elevation-meters.json terrain.esp --spacing-m 31.25 --editor-id ChimsterFlagstaffDemo --title "Flagstaff terrain fixture"
## Acceptance
Round-trip verify WRLD/CELL/LAND counts and every height sample with Chimster's reader. CI exercises public USGS Flagstaff data; independent xEdit and GECK tests are outstanding. Inspect the output in a disposable profile before any runtime use.
References:
- https://tes5edit.github.io/fopdoc/FalloutNV/Records/WRLD.html
- https://tes5edit.github.io/fopdoc/FalloutNV/Records/CELL.html
- https://tes5edit.github.io/fopdoc/FalloutNV/Records/LAND.html
- https://tes5edit.github.io/fopdoc/FalloutNV/Groups.html
- https://stepmodifications.org/wiki/Guide:Plugins_Files
- https://github.com/fo76utils/fo76utils/blob/main/src/landdata.cpp
