# Navigation workbench
World → Navmesh editor. Generate from a rectangular sampled floor or portable room layout, select two triangles to review a corridor, toggle portal transitions, exclude selected triangles, undo, inspect quality, save portable mesh JSON. Large meshes are bounded and may exceed the interactive drawing limit.

## Automatic heightfield source
A schema-1 JSON object includes spacing, heights (rectangular rows of vertex elevations, null for absent floor), optional XYZ origin, per-cell ceilings (relative to origin Z; null means unspecified), blocked XY cell indices, world-coordinate collision obstacle boxes, agent radius/height/max_slope/max_step, and min_region_cells. All lengths use consistent caller world units. Whole-cell support, conservative clearance and slope/step rejection avoid unsupported bridges; obstacle boxes are explicit proxies. Coarse spacing can reject narrow valid corridors; refine input. Output is deterministic and reports rejected cells and connected triangle regions. This is not full collision triangle rasterization or multilevel Recast.

    python -m chimster navmesh-auto floor.json mesh.json
    python -m chimster navmesh-auto rooms.json mesh.json --rooms --spacing 0.5 --radius 0.3 --height 1.8
    python -m chimster navmesh-route mesh.json 0 12 --closed DoorPortal

Room floors are separately triangulated; portals must have sufficient width, height, step allowance and a collision-proxy-clear approach. A portal link can be closed in route review. No automatic connection across walls. The Python room generator accepts explicit obstacles and portal-door bindings; the CLI room preset currently accepts the portable layout only.

## Native FNV
    python -m chimster world-check Base.esm Patch.esp --navmesh
    python -m chimster navmesh-draft mesh.json draft.json --cell 0x800 --version 12

Choose the native version from a locally verified template; example version is illustrative, not a certification. Native draft JSON contains documented fields only. It is deliberately not a playable plugin. Final NVGD spatial-grid encoding, unknown NVCA and external metadata, door triangle entries, NAVI registration, XNDP reconciliation, cross-cell links, and independent GECK validation must be completed before native output is enabled. Read-only NAVM inspection exposes geometry, native adjacency, door references, external mesh references and opaque fields. Other game-specific layouts are not inferred from FNV.

## Remaining scope
- Robust arbitrary collision geometry and stacked surfaces; optional verified Recast-style backend, tile generation and stitching.
- Native finalized FNV export, NAVI, door links and safe staged edits; independently verify Fallout 3, Skyrim families and Fallout 4 families.
- Older Morrowind/Oblivion pathgrid adapters; do not pretend those use the later NAVM format.
- NPC radius/height presets, cost and area painting, manual vertex/edge editing, seam review, collision/terrain/world integration, incremental regeneration, runtime and performance tests.

Format reference: https://tes5edit.github.io/fopdoc/FalloutNV/Records/NAVM.html
Automatic generation concepts: https://recastnav.com/structrcConfig.html
Synthetic regression fixtures added; execution deferred. No game-runtime certification.
