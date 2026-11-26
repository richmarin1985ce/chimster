# LOD Forge development pass
Implemented intermediate geometry, orthographic flat-color z-buffer baking (not texture/alpha sampled), tree view atlases, object material atlases with compatibility checks and UV remapping, PNG and legacy uncompressed single-level DDS output, regular-grid terrain decimation, spatial/material tile planning, content-key/dirty tile detection, vertex clustering and synthetic benchmark harness. Intermediate outputs are not Bethesda worldspace LOD formats. Billboard mesh is an OBJ preview; actual tree LOD atlases and records require the target generator. Geometry-only 4.0.0.2 legacy NIF via optional BSD PyFFI 2.2.3, isolated roundtrip CI; optional texture binding and alpha test for a legacy billboard package; no engine test or later NIF support. Hybrid tree export: simplified 3D intermediate LOD tiers exist; actual engine-specific hybrid rules not implemented. Terrain seams require identical neighbor edge samples and stride; mixed-resolution stitching pending.
## Usage
python -m chimster lod tree output --seed 42 --views 2 --size 128
python -m chimster lod nif tree.nif --level 2 --scale 1
python -m chimster lod legacy-billboard output --size 128 --views 2
python -m chimster lod terrain heights.json terrain.obj --step 2
python -m chimster lod benchmark --count 10 --size 64
python -m chimster lod workflow skyrimse
python -m chimster lod tool profile.json texgen /path/to/TexGen.exe
python -m chimster lod openmw-settings
python -m chimster lod mge /path/to/disposable/Morrowind
## External tools
xLODGen, TexGen and DynDOLOD command plans include explicit data, plugins, INI, temp and new output directories; --execute starts interactive utility, not unattended build. Only supported game mode/utility pairs. Do not start subsequent tools until output reviewed and staged; MGE XE wizard plan is interactive and writes to Data Files. OpenMW emits proposed settings only; do not overwrite existing config. No binaries bundled, no invented unattended CLI flags. For real benchmarks, use a public OpenMW template or user-owned game; test frame time (median/P95/P99), geometry count, draw calls, VRAM, texture residency, camera path and silhouette error. Synthetic CPU metrics not FPS.
## Extra task
Localization audit compares string IDs and common placeholders, escaped newlines and markup. It is advisory; no automatic rewriting.
## References
- https://dyndolod.info/Help/Command-Line-Argument
- https://dyndolod.info/Generation-Instructions
- https://dyndolod.info/Help/xLODGen
- https://openmw.readthedocs.io/en/stable/reference/modding/settings/terrain.html
- https://github.com/Hrnchamd/MGE-XE
- https://www.niftools.org/pyffi/pyffi/formats/nif.html
- https://pypi.org/project/PyFFI/

Initial CI benchmark: 10 unique trees, 40 geometry tiers, 10 distinct 64px bakes in 0.364 seconds on the Linux CI runner. 75 tests discovered, 74 passed and the optional PyFFI test passed separately before adding the textured billboard test. See https://github.com/richmarin1985ce/chimster/actions/runs/45898785107 .
