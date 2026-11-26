# Flora Forge (experimental)
Original MIT procedural asset generator; no SpeedTree source or assets.
Generate seeded tree, shrub and grass intermediate meshes. Four tiers retain progressively fewer branches and leaf cards; last tier is a crossed-plane placeholder, not a baked billboard. The OBJ includes UVs and logical material IDs, not texture files or MTL. Geometry is Z-up and dimensionless until a game-specific conversion; no normals, wind weights, collision, roots, texture atlas baking, or native NIF export yet. Near geometry is an experimental single-level branching model, not production quality.

## Measured local baseline
100 seeds, 4 tiers each, 155600 triangles total. Five CPU-only generation runs: median 0.370 seconds. One batch OBJ export including generation and manifest: 1.348 seconds. Default per-tier triangles: 980,396,176,4. This is not an FPS comparison or a SpeedTree benchmark. No game runtime tested.

## Game-specific adapter roadmap
- Morrowind/OpenMW: verify Blender Morrowind/Niftools or pinned nifly backend; OpenMW native object paging vs MGE XE distant land. Do not fabricate a legacy tree LOD file.
- Oblivion/Fallout 3/NV: native SpeedTree SPT is distinct; static NIF + _lod.nif alternative, plus xLODGen worldspace build and record settings. Verify collision and material flags.
- Skyrim: NIF exporter via PyNifly/Nifly, TexGen billboards + dedicated tree LOD, and object LOD/hybrid routes via DynDOLOD. Preserve plugin/FormID naming.
- Fallout 4: verify NIF + BGSM/BGEM material adapters and object LOD. Starfield separate unsupported asset adapter.
- Direct reuse of GPL nifly in a combined distribution requires GPL compliance. Keep original core MIT and evaluate external helper.

## Texture grouping
Current manifest groups by LOD tier + logical material ID and opaque/cutout/proxy class. No texture hash or physical atlas yet. Next add grouping keyed by diffuse/normal/specular maps, shader flags, alpha mode, UV repeat and color space. Atlas compatible textures only, pack with gutters, remap UVs, preserve alpha coverage in mipmaps, separate tiling textures and billboard atlas constraints. Merge geometry by cell/LOD tile only where culling, transforms, collision, gameplay and engine formats permit. Do not merge the entire world into one mesh.
## Benchmark plan
Compare equal-scene baseline vs generated meshes for silhouette error, alpha overdraw, draw calls, texture residency, frame times, LOD popping and file sizes. Use actual game captures; report hardware, settings and variance. Test bark and leaf materials separately. Native NIF export must be reimported and checked in NifSkope and target engine before it is declared supported.

References:
- https://docs.unity.com/en-us/speedtree-modeler/10/level-of-detail
- https://dyndolod.info/Help/Tree-LOD
- https://dyndolod.info/Help/Object-LOD
- https://dyndolod.info/Help/3D-Tree-LOD-Model
- https://openmw.readthedocs.io/en/stable/reference/modding/settings/terrain.html
- https://geckwiki.com/index.php/Tree
- https://github.com/ousnius/nifly
- https://github.com/BadDogSkyrim/PyNifly
- https://github.com/niftools/blender_niftools_addon
