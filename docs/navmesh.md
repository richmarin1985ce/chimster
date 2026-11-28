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

## Collision triangle AutoNav (experimental)
The same navmesh-auto command and editor now detect schema-1 sources with vertices, triangles, spacing and optional agent/min_region_cells. Supply Z-up XYZ vertices and CCW upward-facing collision floor triangles; all other surfaces participate in collision tests. No retail asset data is bundled. Each sparse raster column retains independent floor candidates, and full coplanar floor coverage is computed as polygon union (duplicate overlapping triangles cannot fill a gap). Overhead surfaces and walls reject unsafe cells. Agent clearance erodes candidate floors; short boundary risers allow explicit bounded step transitions. Sloped surfaces are triangulated and continuous matching edges welded. The editor exposes per-column elevation layer filtering and triangle exclusions preserve layer metadata. Stacked floors remain separate unless geometrically connected; no automatic links across vertical gaps. The layer number is a local ordinal, not a globally identified building story.

Limitations: conservative whole-cell sampling drops partial cells and noncoplanar seams; narrow stairs or openings may need finer spacing; geometry must be correctly wound and supplied in a consistent coordinate system. Short-step links are portable and need independent swept-agent verification before game export. This is not full Recast contour simplification, a complete NIF collision extractor, or finalized native NAVM authoring. Input budgets reject very dense columns and oversized scenes. Synthetic fixtures cover stacked floors, ramps, steps, wall splitting, clearance and duplicate coverage; execution remains deferred.

## Simplification and NIF collision import
    python -m chimster navmesh-auto collision.json mesh.json --simplify
    python -m chimster navmesh-simplify mesh.json reduced.json
    python -m chimster navmesh-nif building.nif mesh.json /path/to/chimster-nifbridge --unit-scale 7 --spacing 8 --radius 16 --height 96 --max-step 16

The last command uses explicit caller-provided world units; numbers are illustrative only. The optional separately compiled GPL Nifly helper reads native FO3/FNV static root collision rather than visual meshes. Supported source paths: box, translated transform, list, MOPP wrapper and uncompressed packed triangles with unit shape scale. Unsupported formats, multiple collision objects, rotated body/child transforms and nonidentity root transforms are rejected. The packed path and scale assumptions still require independent fixtures; rebuild the helper from pinned source. No retail assets included.

Simplification removes coplanar interior vertex fans with convex contours, preserves all outer boundary vertices, per-triangle room/layer metadata and transition endpoints, and verifies boundary and component counts. It is available as an optional automatic pass or explicit editor action with undo. It does not simplify irregular outer contours or alter slope breaks. Step links now require width and swept rectangular clearance at the higher edge, conservatively rejecting nearby upright/overhead collision. This is not a complete capsule controller or native stair-finalization system. Regression fixtures added; no execution or native compilation claimed.

## Incremental tiled AutoNav
    python -m chimster navmesh-tiled collision.json first.json --tile-cells 32
    python -m chimster navmesh-tiled edited.json second.json --previous first.json --tile-cells 32
    python -m chimster navmesh-route second.json 0 100

Tiled mode uses a fixed global raster origin, hashes source collision geometry and settings per expanded tile, and recomputes only dirty tiles. The halo includes radius and step clearance context. Core ownership is assigned by triangle centroid; matching shared edges are checked in both neighboring halo meshes before welding. Cross-tile stair links require both tiles to independently report the same cleared crossing. Stable geometry-derived link IDs survive triangle reindexing. Simplification protects tile seams and ownership; manual triangle removal preserves tile/area metadata. The desktop Incremental tiles option reuses its in-session cache. CLI output contains the assembled mesh, local cache, rebuilt/reused/removed tile lists. Only reuse trusted project-local cache data; hashes are for invalidation, not authentication. Changing agent settings invalidates the cache. World-wide region pruning beyond threshold 1, native NAVM tiling, streaming and collision extraction improvements remain separate tasks.

Short walls are no longer accepted as risers merely because they are low: a supported higher adjacent floor must exist. Multi-cell stair apertures can accommodate larger agents if corresponding neighboring floor edges match; sweep checks still apply. Fixtures cover tiled/non-tiled geometry equivalence, local edits, negative world coordinates, settings invalidation, cross-tile stairs and low-wall rejection. Regression execution and independent engine validation remain outstanding.

## Resolution refinement and areas
    python -m chimster navmesh-adaptive collision.json refined.json --levels 3 --triangle-budget 250000
    python -m chimster navmesh-areas refined.json classified.json --policy areas.json
    python -m chimster navmesh-route classified.json 0 100 --avoid-area hazard

Refinement tries the source grid spacing and successively halves it, using a globally aligned tiled build at each level. The finest nonempty candidate within the raw triangle budget is selected, then area-classified and simplified. A previous bundle may supply a trusted local cache for the matching spacing. The report records tried spacings, raw/simplified triangle counts, surface area, and stopping reason. This is not yet local mixed-resolution rasterization. Simplification can remove simple concave planar interior fans while preserving boundaries, seam vertices and area boundaries; it rejects self-intersections and existing unrelated diagonals.

Default areas are ground, ramp, steep and stair. A policy can supply ramp_degrees, steep_degrees, positive costs, and zones with min/max XYZ and area label. Zone overrides apply only when all triangle vertices are in a zone; partial AABB overlaps are reported for manual review. These are portable routing semantics, not verified native game flags or material classes. The route API supports cost overrides and avoided areas. Desktop Classify areas displays area colors; manual area painting is available through Python. Regression fixtures added, not run.
