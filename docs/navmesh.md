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

## Native finalization candidate and rotated collision extraction
    python -m chimster navmesh-finalize mesh.json candidate.json --cell 0x800 --version 12 --divisor 2 --count-width 2 --bindings bindings.json
    python -m chimster navmesh-grid-compare local-native-fields.json --count-width 2

Numbers are illustrative; choose version, divisor and grid framing from locally obtained independent reference data. The candidate writes native NAVM subrecord payloads, including explicit external edge metadata and doors, cover triangle indices and a conservative XY grid. It verifies counts, flags, local triangle topology and grid coverage. It rejects unresolved portable off-mesh links instead of treating stair transitions as game-native edges. Bindings may contain doors (reference, triangle, tail_hex), external (triangle, edge, target, target_triangle, prefix_hex), cover (triangle indices), and flags (per-triangle words, external bits derived). Unknown external/door bytes must be supplied explicitly. Reference comparison reports exact-byte and per-bucket differences for a supplied native fields file. NAVI inspection identifies documented NVMI prefix references and preserves opaque suffix/NVCI data; world-check --navmesh reports missing registration, external reciprocity and XNDP backlinks. A candidate is not a playable ESP: NAVI generation, independent grid framing/membership, cover semantics, external topology, door linkage and GECK runtime validation remain release gates.

The pinned FO3/FNV Nifly extraction bridge now applies rigid-body XYZW quaternion rotation and nested proper rigid transform matrices before unit conversion. Reflections, nonrigid transforms, nonidentity root, nonstatic/multiple collision objects and unsupported shape families remain rejected. Packed data, rotated shapes and extraction scale require independent fixtures. No native helper compilation or regression execution was performed in this pass (local GitHub DNS resolution blocked). 
References: https://tes5edit.github.io/fopdoc/FalloutNV/Records/NAVM.html ; https://tes5edit.github.io/fopdoc/FalloutNV/Records/NAVI.html ; xEdit dev-4.1.5 Core/wbDefinitionsFNV.pas (format research, no copied implementation).

## Convex cores, compressed collision and native registration review
The optional Nifly helper now emits transformed convex core point sets for bhkConvexVerticesShape and handles bhkConvexListShape. The Python bridge reconstructs outward-oriented manifold core surfaces from at most 64 unique points per hull with strict total work limits. The three isolated local fixtures (cube with redundant points, tetrahedron, coplanar rejection) passed. Rounded Havok margins are not reconstructed; this is the collision core, not a full physical shape simulation. The bridge itself has not been rebuilt.

An experimental static-root Skyrim LE/SE path decodes bhkCompressedMeshShape big triangles and nonreferenced quantized chunks with translation-only chunk transforms, unit shape scale and strip/list index validation. It uses the 0.001 Havok-unit quantization convention, direct vertex indices and alternating strip winding. It rejects unsupported chunk references, convex pieces, rotated chunk transforms and unsupported body or shape types. This path needs independent asset fixtures and bridge compilation; it is not certified extraction. Format references: https://github.com/BadDogSkyrim/PyNifly/blob/main/docs/mopp_format.md and https://github.com/blu12335/skyrimconversion/blob/master/docs/commentary/asset_convert_nif.md .

    python -m chimster navmesh-native-review project.json
    python -m chimster navmesh-registration project.json

Project JSON contains meshes (native candidate fields with form_id, optional expected location and grid), navi (locally sourced native fields), and optional explicit door_backlinks (reference, mesh, triangle; caller must verify actual XNDP convention). Review checks known fields, grid framing, reciprocal external edges and shared edge coordinates with opposite winding, exact known NAVI registration location/grid and door backlink consistency. Registration manifests include candidate payload hashes and expected IDs for a native finalizer. Neither command synthesizes unknown NVMI tails or NVCI data. Full NAVI generation and playable ESP finalization remain pending. New integration fixtures are committed but unexecuted; local GitHub DNS prevents full checkout/build.

## Native staging, XNDP triangle bindings and optional FO4 backend
Interior projects can explicitly include a cell-level navmesh_stage object: mesh (vertices and triangles, no unresolved portable off-mesh links), version, divisor, count_width, optional cover and flags, and doors (placement, triangle, tail_hex, backlink_tail_hex). The existing fnv-interior command writes NAVM into the temporary child group and assigns stable FormIDs. Door bindings require a persistent DOOR placement and emit matching NVDP and XNDP signed triangle indices. Large subrecords use XXXX framing. This produces an unfinalized ESP, not a game-ready plugin. Preserve a separate untouched stage copy, open another copy with the identical filename and master order in GECK, finalize the new cells, save, then run:

    python -m chimster navmesh-verify-stage staging/Stage.esp finalized/Stage.esp --master /path/to/FalloutNV.esm

The review compares record identities, NAVM geometry, NAVI registrations and load-order diagnostics. It does not generate unknown NAVI data or execute GECK. GECK may legitimately make other changes; the review reports these for inspection. Native game traversal remains required. See https://geckwiki.com/index.php/Finalize_Cell_NavMeshes .

Skyrim compressed collision now accepts the absent-transform sentinel 65535 and applies a proper quaternion rotation when a transform is present. Referenced chunks are still rejected because their semantics and fixture coverage are incomplete. An optional local PyNifly adapter supports a restricted Fallout 4 static root physics body, validated triangle meshes and nested compound transforms; it rejects dynamic/trigger bodies, nonidentity root transforms, unsupported shape types and multiple collision bodies/nodes. The compatible local PyNifly backend is required, not bundled or installed by Chimster.

    python -m chimster navmesh-fo4 asset.nif mesh.json --unit-scale 1 --spacing 1

Unit scale and spacing are illustrative, not native recommendations. New synthetic regression fixtures were committed; native compilation, full suite execution, GECK finalization and real asset tests remain outstanding. Additional primitives and referenced chunks remain pending.

## Native NAVI generation and curved collision primitives
An experimental native NAVI override stage is available:

    python -m chimster navmesh-navi-stage staging/Stage.esp /path/to/FalloutNV.esm candidate/Stage.esp

The source is a new-interior-only stage containing exactly one master (a locally supplied self-contained FalloutNV.esm), and the destination is a new path with the same ESP filename. The implementation preserves all existing master NVMI/NVCI payloads and their order, creates ordinary 32-byte non-island interior NVMI entries with mesh/cell identities and approximate vertex centroid, and derives counted NVCI neighbor/door arrays from native NVEX/NVDP. Preferred and island variants, exterior coordinates, and edits that require updating existing master mesh connections are rejected. Reciprocal new-mesh edges and seam coordinates, grid framing, persistent door backlinks and unchanged original record hashes are checked; the writer does not remap opaque master NAVI data. Review checks NVCI connection and door lists against the candidate NAVM records. **This is an experimental candidate ESP, not a game-certified replacement for GECK finalization.** Format research: xEdit FNV definitions, https://tes5edit.github.io/fopdoc/FalloutNV/Records/NAVI.html and independent ordinary-NVMI/NVCI layout research in https://github.com/slfx77/bethesda-multitool/blob/main/src/BethesdaMultitool/Core/Formats/Esm/Plugin/Nav/NavInfoMapBuilder.cs . No upstream implementation copied.

Native sphere, capsule, cylinder and multisphere shapes now produce conservative enclosing solid AABBs (not exact curved triangle geometry); FO4 optional PyNifly sphere/capsule support also emits these boxes. The collision source accepts solid_obstacles (min/max XYZ); these block floor candidates and stair sweeps, cannot generate walkable surfaces, and are included in incremental tile cache fingerprints and halo context. Obstacle-only assets must be combined with floor collision before generating navigation. Bounds may over-reject narrow spaces; native extraction is uncompiled and must be checked against local assets.

Referenced Skyrim compressed chunks remain intentionally unsupported until the geometry reuse/transform convention is confirmed. The bridge now provides `chimster-nifbridge inspect-collision-chunks asset.nif` to inventory block/chunk index, reference, transform, offset and array lengths for independent fixture research. Do not infer shared geometry or transform order from a reference index alone. Five isolated Python checks of the new connection codec, ordinary map entry and obstacle bounds passed on copied functions; repository integration fixtures were added but not run, and native C++ compilation remains blocked by local GitHub DNS.

## Exterior and preferred NAVI payload candidates
    python -m chimster navmesh-navi-candidate project.json candidate.json
    python -m chimster navmesh-navi-inspect candidate.json --grid-order yx
    python -m chimster navmesh-native-review review.json --grid-order yx --require-connections

The candidate project contains base (existing NAVI fields), meshes (native NAVM candidates with form_id and fields), optional registrations (form_id, world, grid, preferred_value, preferred_neighbors), and grid_references (nvmi_hex, grid). Exterior generation requires a supplied local base NAVI entry with independently established XCLC coordinates that distinguish XY from YX, and all supplied references must agree. The exterior NVMI references the parent worldspace and signed cell grid. Preferred value and neighbor class are explicitly supplied; the engine's preferred weighting convention is not inferred. Standard/preferred lists must partition actual external NAVM neighbors; generated fields are decoded again to check registration and door/neighbor coverage. Existing base entries remain unchanged. The direct ESP stage writer is still interior-only; exterior/preferred output is payload-only and experimental. The inspection command decodes candidate ordinary/island layouts with bounded counts, triangle indices and finite bounds, and reports unparsed entries. Island generation remains disabled. The native batch reviewer has explicit grid order and optional strict NVCI coverage, with duplicate/overlapping classes diagnosed. See independent format research in https://github.com/slfx77/bethesda-multitool/blob/main/src/BethesdaMultitool/Core/Formats/Esm/Conversion/Processing/EsmSubrecordConverter.cs . Five isolated tests passed on the variant codec; integrated candidate, full suite, real reference calibration and engine behavior are not verified. Local repository checkout still fails DNS.

## Reference-backed island candidate pass
The branch comparison from commit 44ca9d7 to the pre-pass main found 87 intervening commits (audio, character preview and worldspace/environment tooling); NAVI sources were unchanged. This pass adds restricted island NVMI payload encoding. An optional registration island_reference object contains nvmi_hex (an exact entry of base NAVI) and navm (form_id and native fields for its corresponding source mesh). The serializer requires the supplied reference to reproduce byte-for-byte from its native NAVM vertices, indices, bounds, centroid and flags (0x20 only) before encoding a new island candidate. No automatic island detection, simplified island geometry or ESP installation is implied. Unsupported reference conventions fail closed. This is experimental payload-only output.

    python -m chimster navmesh-navi-reference FalloutNV.esm references.json --mesh 0x00136567

The reference command reads selected master-local NAVM identities, matches their NAVI entries and checks CELL ownership, WRLD ancestry, and signed XCLC coordinates against the source records. It extracts grid and island calibration inputs without modifying the master; the example ID is illustrative. Nine isolated codec tests passed (five existing and four new island tests); integration, actual native asset calibration and GECK/game testing remain outstanding. The local GitHub checkout again failed DNS. Existing master topology editing and exterior ESP integration are still pending.
