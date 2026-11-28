# LOD Forge

Chimster's Worldspace Browser now has built-in native candidate generation for Fallout 3 and Fallout New Vegas. No external LOD applications or helper executables are used by these generators. The original Python implementation serializes NIF stream 34, writes DDS and a 24-byte DLODSettings file, groups terrain at levels 4/8/16/32, and builds static-object companion and segmented macro meshes. Source game assets may be read from loose Data directories or classic BSAs.

## Usage
- Worldspace Browser: Build native LOD; choose a new output directory.
- Build object LOD: select source game Data or configured BSA archives.
- Audit LOD: inspect candidate output inventory.
- `python -m chimster lod world-native newvegas MyWorld output MyWorld.esp`
- `python -m chimster lod world-objects newvegas MyWorld object-output MyWorld.esp --data /path/to/Data`
- `python -m chimster lod tree output --seed 42 --views 2 --size 128`
- `python -m chimster lod terrain heights.json terrain.obj --step 2`

Always supply source plugins in master-first load order. Outputs are experimental candidates, not verified installable packages. Terrain textures are procedural slope maps rather than actual LAND material blends; native object candidates preserve original diffuse and normal references but do not yet bake a shared atlas. Unsupported shapes, transforms and shader layouts are reported rather than silently replaced. Runtime coordinate conventions, settings semantics, terrain morphing, native shader behavior, mipmaps, texture atlas generation and native coverage for additional games still require validation. Existing portable LOD geometry, atlas and benchmark tools remain available.

Format references (binary layout facts, no third-party implementation bundled):
- https://github.com/niftools/nifxml
- https://github.com/TES5Edit/TES5Edit/blob/dev-4.1.6/Core/wbDataFormatMisc.pas
- https://geckwiki.com/index.php/World_LOD
