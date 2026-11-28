# Master checklist — production reassessment (2026-11-26)

## Active release scope — 2026-11-27
Active: Morrowind, classic Oblivion, Fallout 3, New Vegas, classic Skyrim, Skyrim SE/AE, Skyrim VR, Fallout 4 and Fallout 4 VR. VR variants require explicit capability profiles and independent format/runtime verification; do not assume desktop parity.
Deferred: Arena, Daggerfall, Oblivion Remastered (legacy and Unreal), Starfield and Fallout 76 (including offline asset replacement). Preserve existing code and documentation; no new title-specific development until explicitly reopened. Shared improvements remain in scope. Exclude deferred-only tasks from active release readiness, but retain them in the lifetime roadmap. Continue easiest-first sweeps across active sections, with testing deferred as directed.

## Rendering and asset architecture — 2026-11-27
Prioritize sections 8 then 9. Panda3D is the preferred experimental advanced renderer, bundled in self-contained releases with no separate user installation or runtime downloads. Retain ModernGL and CPU fallbacks. Audit exact distributed binaries and license notices; require offline clean-machine launch before release. Engine features are candidates for integration, not completed Chimster capabilities.
Unify Flora Forge and Asset Forge as one model creation subkit; pause new procedural modeling features, preserve existing generators. Mesh import, native conversion, materials, placement, rendering and LOD integration remain active.
Current prototype: optional Panda3D dependency, scene adapter and offscreen preview. Desktop hookup, packaging and execution validation pending.

Current baseline: PR23 merged at 7c356fbde0c879c0de46c47290e0bd7cb812635e; eight CI workflows green. Retail engine validation remains outstanding.
| Area | Working foundation / limited implementation | Next production milestones |
|---|---|---|
| 1 Core | Shared project store, revision transactions, extension protocol and three-platform installer smoke tests | Project dashboard, dependency manager, signed installers and updates |
| 2 Compatibility | Profiles, public fixtures, NIF roundtrips, Remastered package classification, FO76 read-only metadata, release snapshots | Independent format/engine validation, Arena/DF, Remastered dual asset adapters, Starfield, versioned capabilities |
| 3 Records | Stable FormID ledgers, typed FNV edits, guarded master permutation and 24 project record types | Persistent FormIDs, typed schemas, unknown-field preservation, master remapping, visual comparison |
| 4 Mod management | Profiles, ZIP/FOMOD subset, dependency order, loose-file overlay, patch proposals | LOOT validation, archive precedence, VFS, safe merge and save checks |
| 5 World editor | Terrain import, sculpt/paint, native FNV world fixture, snapped placements, portable chunk storage | Continuous streaming, direct 3D brushes, roads, settlements, native interiors, persistent IDs, navigation, weather/water |
| 6 Landscape | Blended portable brush, undo and quadrant budget checks; native writer limit unchanged | Coverage/consolidation, boundary consistency, merge-winner audit, texture-aware LOD; classic Oblivion 9, FO3/FNV 7, writer 4 alpha + base until verified |
| 7 Validation | Hierarchy, cell/group/record/reference checks and export gate | Source-to-merge preservation, LOD chunks, navmesh, game-specific schemas, review-only repair |
| 8 Rendering | CPU/GL, textures, picking, instancing/BVH, LOD, portable room/portal filtering | Live chunk streaming, direct GPU surface, recursive portal clipping, occlusion, shadows/reflections, hardware benchmark |
| 9 Mesh/assets | Flora, NIF bridge, modular rectangular buildings, portable collision recipes | Native architectural packages, modular roads/interiors, editable topology, animations/skin/materials |
| 10 Collision/spatial | Native FO3/FNV static boxes/compound list, material IDs, room/portal/trigger/node models and trigger preview | Native room/portal/multibound/occlusion/trigger records, collision visualization, MOPP/mesh, convex decomposition, material behavior in game |
| 11 Textures | CPU BC1/BC3, alpha coverage mipmaps and height packing | Additional BC formats, HDR, parallax, advanced materials |
| 12 LOD | Flora tiers, billboards, atlas, terrain seams, culling, dirty tile planning, external tool plans | Native LOD files, texture baking, tool validation, stream integration |
| 13 Version control | Immutable revisions, rollback and record comparison | Semantic 3-way merge, rollback UI, LFS |
| 14 Quest/dialogue | Portable graph, state analysis, native QUST/DIAL/INFO, actor/faction/stage conditions, objective refs, GECK script source | Compile/attach scripts, runtime stage progression, reputation, NPC integration, scenes/aliases on applicable games |
| 15 Scripting | Fragment inventory, Papyrus lexical checks, GECK result sources, external compiler plans | Verified compile/decompile, script IDE, VMAD, GECK/OpenMW, debugging |
| 16 Books/notes | Illustrated portable previews, native FNV text books and notes | Native markup, illustrated books, fonts, inventory/quest links, cross-game formats |
| 17 Characters | Template-based actor authoring, speaker references, stats and schedules | Native NPC records, FaceGen, appearances, stats, factions, AI packages, companions and creatures |
| 18 Gameplay | GMST patches, skill books, typed inventory, faction, perk and leveled-list records | Items, inventory, weapons, armor, perks, leveled lists, combat, vendors/economy |
| 19 Audio/voice | Basic FUZ | Audio codecs, lip sync, voice profiles, local casting, batch generation, consent/license metadata |
| 20 Localization | Portable catalogs, exact-context memory, glossary audit and desktop workbench | Native dialogue integration, translation/terminology, encodings |
| 21 Interface/minigames | Portable grid authoring/playtest, FFDec plan | Native holotape adapters, visual tile tools, HUD/menu/icons, GFx verification |
| 22 Testing | Synthetic/public tests, NIF/GL roundtrips, DEM and benchmark | Retail test profile, independent xEdit/GECK, game smoke and saves, performance on low-end hardware, crash logs |
| 23 AI | Structured advisory actions, retrieval, Ollama adapter | Actual inference, validated edit transactions, rollback, multi-step project tools |
| 24 Wiki | Formatted offline manual, navigation, HTML export and link audit | Rich links, game-specific verified format catalog |
| 25 Distribution | Versioned offline installs and rollback, three-platform installer smoke tests | Archive validation, signed installers, conditional packages, dependency manifests, publishing |
| 26 Flagstaff | Campaign design, original cast/quests, provisional DEM, native terrain fixture, original minigame | Playable slaver-pit slice, city/road/ranch production, Legion politics, Enclave reconnaissance, endgame, full New Vegas-scale campaign |
## Sections 2 and 3 — active-scope closure pass (2026-11-27)
- Section 2: centralized active profile aliases, including SE/AE file-family alias and both VR desktop identifiers. Compatibility and native record workbenches share the resolver; deferred Remastered is not offered in the native workbench. Runtime identities remain gated for VR and deferred profiles. The partial reference catalog capability is distinct from exact generated FNV schema support; no retail verification or AE runtime-version certification is implied.
- Section 3: exact generated FNV perk effects now carry QUST/SPEL type constraints, and consumable ENIT offsets carry SPEL/SOUN constraints. Shared graph and native catalog use these constraints; one-pass field iterables are materialized and existing catalog type information is retained. Synthetic regression tests added.
- Open release gates: independent local retail plugin/archive/engine validation for all nine active targets, version-specific VR and AE behavior, comprehensive per-game native field and nested record schemas, general master addition/removal/renumbering, unknown layouts, and full typed reference traversal. CI execution remains deferred under the existing quota policy. No section-wide completion claim.

### Active-scope milestone estimate (2026-11-27)
Equal-weight engineering milestones: implemented = 1, partial = 0.5, pending = 0. This is a source-inspection estimate, not a measured code-coverage or retail-readiness percentage. Implemented means the bounded milestone exists, not that new regression tests have passed.

| Section | Implemented | Partial | Pending | Estimate |
|---|---:|---:|---:|---:|
| 2 Compatibility | 5 | 3 | 2 | 65% |
| 3 Records | 3 | 6 | 1 | 60% |

Section 2 implemented milestones: active profile routing, local installation detection, structural parser, dependency audit, archive read/package infrastructure. Partial: asset/string/NIF adapters, precedence/independent comparison, version-specific capability coverage. Pending: independent retail format validation and runtime verification.

Section 3 implemented milestones: structural read/raw preservation, staged reference edit transactions, regression fixture infrastructure. Partial: persistent identity coverage, typed field schemas, native creation, forward/reverse dependency coverage, master remap, record comparison/editor coverage. Pending: independent retail validation. No deferred game families counted.

Follow-up code: VR catalog entries explicitly empty rather than crashing or inheriting desktop field offsets; deferred manifest aligns with release policy; remap previews fingerprint all source fields and reject stale payloads or absent disk slots; typed nullable FNV slots available to the edit path without adding null graph edges. New regression fixtures added; execution remains deferred.

### Follow-up: bounded master-set changes
Section 3 now supports explicitly opted-in master addition/removal for the same generated flat New Vegas layouts as the existing reorder operation. Removed live references, incompatible override origins, duplicate/deleted identities and known wrong-type targets are rejected. Same-name staging and dependency checks retained. Synthetic tests cover insertion, removal, live-reference rejection and removing the last unused master; execution deferred. Nested groups, opaque schemas, general cross-game remapping and runtime equivalence remain pending. The equal-weight estimates remain 65% / 60%: remapping has advanced within the partial milestone, not completed it.

### Follow-up: nested exterior world and compressed remapping
The New Vegas master-set writer now covers the exact generated WRLD/CELL/LAND/REFR hierarchy plus TXST/LTEX and generated BOOK/NOTE layouts, with typed base-object/terrain-texture links. World and cell group owners are remapped; block/subblock coordinate labels are preserved and checked on reopen. Bounded compressed known-schema records are decoded and recompressed. Unknown layouts, unsupported hierarchy types, non-text notes, and unsupported flags remain blocked. Synthetic world insertion and compressed reference fixtures added; execution deferred. This advances the partial master-remapping milestone; estimates remain 65% compatibility and 60% records.

### Follow-up: native dialogue and quest remapping
Exact generated FNV QUST/DIAL/INFO layouts, topic-owned INFO groups and supported CTDA conditions (stage, actor, faction, reputation) are now supported by the staged master-table writer. Typed objective, quest, topic, previous-response, audio, animation and speaker references are remapped. Nonempty script source or bytecode, unrecognized condition functions and layouts remain blocked. Shared exact generated world and quest reference offsets are now also used in graph/catalog inspection. Synthetic tests cover semantic identity preservation, script rejection, unknown conditions and graph coverage; execution remains deferred. General nested interiors, native script remapping, wider cross-game schemas and independent verification remain open; same milestone estimates 65% / 60%.

## Connected core systems — active-scope tracking
The five connected sections are now tracked together using the existing ten equal-weight milestones per section (implemented = 1, partial = 0.5, pending = 0). Estimates are engineering source-review estimates, not tested retail readiness.

| Section | Implemented | Partial | Pending | Estimate |
|---|---:|---:|---:|---:|
| 2 Game compatibility | 5 | 3 | 2 | 65% |
| 3 Native records | 3 | 6 | 1 | 60% |
| 5 World editor | 4 | 4 | 2 | 60% |
| 7 Validation | 4 | 5 | 1 | 65% |
| 14 Quests/dialogue | 4 | 4 | 2 | 60% |
| Combined, equal section weights | 20 | 22 | 8 | 62% |

5 implemented: terrain import, portable sculpt/paint, snapped placement, portable chunk storage. Partial: native exterior authoring, persistent identity/world inspection, interior layout/native integration, roads/settlement tools. Pending: continuous native streaming/3D editing; native navigation/weather/water integration.
7 implemented: structural bounds checks, group/owner checks, dependency/load-order checks, read-only issue reporting/export gate. Partial: typed reference checks, merged-world/override preservation, landscape/LOD coverage, game-specific schema coverage. Partial addition: native FNV navigation geometry and link validation. Pending: independent retail validation/repair workflow.
14 implemented: portable quest graph/editor, bounded state analysis, generated FNV stage/objective/dialogue authoring, GECK source draft planning. Partial: native typed quest references/conditions, actor/reputation integration, compilation attachment tooling, scenes/aliases/cross-game adapters. Pending: verified runtime progression and independent retail/GECK validation.

Cross-section pass: native quest inspection now shares generated CTDA and dialogue reference offsets, validates duplicate IDs and topic/previous-response ownership. Native world inspection exposes LAND, owning world/cell, persistent flag and reference bucket. Opt-in world-check --quest-links audits generated quest links against merged winners; unknown layouts remain opaque warnings. Integration fixtures added, execution remains deferred. No change to prior Section 2/3 milestone scores.

### Follow-up: native interiors and persistent placements
Section 5 now includes a bounded experimental New Vegas interior fixture writer, with explicit named cells, local/static master references, stable ledger keys and temporary/persistent reference buckets. Section 3 remaps the same generated interior schema and type-2/3/6/8/9 hierarchy, preserving origin-local IDs and interior block labels. Section 7 reports interior and persistent reference counts; Section 14 regression fixture binds a quest objective to a staged interior reference through its master-origin identity. CLI: fnv-interior PROJECT OUTPUT [--master PATH] [--ledger-in PATH --ledger-out PATH]. Tests added, not executed. Native lighting, doors, room/portal/trigger data, navmesh, additional base classes and retail engine validation remain open. The five estimates remain 65/60/60/60/60: the existing interior integration milestone advanced but is still partial.

### Follow-up: door links and portal integration
Generated FNV interior exports accept DOOR bases, reciprocal persistent XTEL door pairs with explicit destination transform, and local XLKR reference links. The native schema, remapper, inspector and merged validator share typed links and destination checks. Portable same-cell room portals can bind non-teleport door placements on their rectangle; the visibility preview consumes explicit open/closed states keyed by stable local ID, with missing state conservatively open. This is not native XPOD/XPTL/XRMR authoring or live engine state. Cross-master linked targets, native room/portal marker export, navmesh, engine testing and test execution remain pending. Five-section estimates unchanged (65/60/60/60/60).

Format reference: https://tes5edit.github.io/fopdoc/FalloutNV/Records/REFR.html and https://tes5edit.github.io/fopdoc/FalloutNV/Records/DOOR.html .

### Follow-up: template-derived native room and portal markers
New Vegas REFR marker codec validates documented XPRM, XTRI, XRMR/XLRM, XPOD/XPTL and XNDP field sizes and types, preserving unknown bytes. Exact supported layouts share multi-offset references with the graph/remapper, inspector and validator. Native interior export accepts explicit locally supplied RoomMarker/PortalMarker STAT master references and raw template geometry, binds markers to portable room/portal IDs, allocates stable FormIDs and checks topology. Optional explicit quaternion/plane/extent conventions compare native portal corners to the portable layout; no default convention is assumed. Native marker and navigation-link validation is limited; generated native markers and door visibility preview remain separate from live engine state. Synthetic regression fixtures committed but not executed. Independent GECK/game validation, actual navmesh writing, engine-specific room extent conventions and live door/portal integration remain open. Existing five milestone estimates unchanged (65/60/60/60/60).

### Ordered interior development pass (navmesh deferred)
User priority: visual room/door/portal editor → connectivity diagnostics → trigger activation chains → lighting/acoustic spaces → occlusion/multibounds. Navmesh development on hold. Desktop Interior editor supports top-down selection, room/placement creation, shared-face portal creation, editable properties, door bindings, project open/save, undo/redo and experimental FNV export. Connectivity audit detects broken links, reciprocal teleport/persistence failures, arrival ambiguity, disconnected components and unreachable rooms. Portable trigger event dispatch supports finite acyclic chains, transactional door state, and closed-portal binding; no native script execution. Portable room environments support ambient/fog/light and scalar portal acoustic preview. Portable occluder/multibound review checks room containment, ambiguous membership and portal overlap. These last three systems are stored as project metadata and explicitly omitted from ESP exports; native game serialization, renderer hookup and runtime verification remain pending. Estimates remain 65/60/60/60/60. Regression execution deferred.

### Navmesh reopened — automatic authoring first
Navmesh is active again at the user's direction. Implemented portable single-layer heightfield auto generation with per-agent slope, step, headroom, radius, blocked-cell, collision-proxy and region thresholds; deterministic welded grid triangulation; reciprocal edge checks and region analysis. Room layouts build separate floor meshes and explicit clearance-checked portal links, preventing automatic wall crossing. Route review supports disabled door/portal transitions; quality reports and manual triangle exclusion are available. Desktop Navmesh editor and CLI support generation, review, routes and portable saving.
Native FNV NAVM inspection reads documented NVER/DATA/NVVX/NVTR/NVCA/NVDP/NVGD/NVEX, validates counts and known topology, exposes typed cell/door/external links, and integrates opt-in world-check --navmesh. Unknown grid and auxiliary fields are explicitly not certified. Native geometry draft emits documented header/vertex/triangle fields only, not a playable ESP; native NVGD/NVCA/NAVI finalization, cross-cell stitching, XNDP reconciliation, GECK/runtime verification, full arbitrary geometry and stacked floors, pathgrid adapters for older games, and other NAVM families remain open. No native navigation readiness claim. Section 7 advances from pending to partial on the navmesh-validation milestone (+5 points); 2/3/5/14 remain 65/60/60/60. Combined 62%. Regression fixtures committed, execution deferred.

### Collision-based AutoNav pass
AutoNav now accepts Z-up triangle geometry and produces a portable multi-layer mesh with sparse collision columns, coplanar polygon-union floor coverage, upward slope filtering, conservative headroom and radius clearance, continuous-edge welding, short-step links, and region pruning. CLI and desktop auto-detect the triangle source; editor layer filter uses local elevation ordinals. Synthetic fixtures cover bridge/stacked floors, headroom, ramp, wall, gap, riser and overlap rejection. Tests committed, not executed. Arbitrary noncoplanar seams, swept-agent verification, collision extraction from native assets, contour simplification, tile stitching, and native finalization remain open. Connected milestone estimates unchanged (65/60/60/65/60; combined 62%).

### AutoNav simplification, native collision and steps
Implemented conservative coplanar interior fan simplification with boundary, region, metadata and link checks; CLI optional auto pass and editor undo. Extended pinned FO3/FNV Nifly bridge with restricted direct collision extraction (fixed root box/list/translation and uncompressed packed geometry via MOPP), explicit Havok unit scale and rejection of unsupported transforms/shapes. Direct navmesh-nif pipeline produces portable simplified output. Step links now check seam width and swept collision aperture. Added synthetic simplification/stair regressions and native bridge box/compound roundtrip extraction fixtures. Native helper rebuild, packed triangle fixtures, full collision-family extraction, arbitrary contour simplification, robust stair controller/runtime verification and final NAVM export remain pending. Test/compile execution deferred.

### Incremental collision AutoNav and seam stitching
Implemented bounded globally aligned raster windows; tile-local source and settings hashes, collision halos, reuse/rebuild/removal reporting, reciprocal shared-edge and cross-tile stair evidence, deterministic core ownership and stable seam-link IDs. CLI navmesh-tiled and desktop Incremental tiles option. Simplification protects tile seams; manual edits preserve tile/area metadata. Tightened low-wall rejection to require supported higher adjacent floor and extended stair width checks across matching neighboring cells. Tiled fixtures cover full-build equivalence, negative coordinates, edit-local invalidation and stair seams. Native cross-cell NAVM/NAVI finalization, large-world streaming and independent performance/engine verification remain outstanding. Tests committed, not executed; no change to the five-section milestone scores from 65/60/60/65/60.

### AutoNav refinement and weighted navigation
Added bounded globally aligned resolution trials (finest nonempty candidate within a raw triangle budget), area classification for slope/stair geometry and explicit world-coordinate zones, positive weighted routing and area exclusions, transactional triangle area painting API, and simple concave coplanar fan simplification with self-intersection/diagonal checks. CLI navmesh-adaptive/navmesh-areas and route --avoid-area; desktop classification and area colors. Cache version bumped to invalidate old raster builds. Refinement is global per trial, not mixed-resolution local tiles; native area flags, physical collision material classification, streaming, advanced NIF collision and native NAVM finalization remain pending. Synthetic tests committed but not executed; percentages unchanged.

### Native navigation finalization and collision extraction
Added native NAVM candidate generation of counts, geometry, edge/door flags, cover indices, explicit external/door bytes and configurable conservative spatial grid; local reference comparison and review gates. Read-only NAVI prefix inspection and opt-in cross-record registration, external reciprocal link and door backlink diagnostics. Expanded FO3/FNV Nifly collision extraction for rigid-body quaternion and nested proper child rotation. Native helper rebuild, independent grid and NAVI unknown data verification, actual playable ESP finalization, more collision families and runtime tests remain outstanding. Synthetic test fixtures committed but not executed; local GitHub DNS failed. Existing milestone percentages unchanged.

### Native collision and registration review continuation
Added convex collision core extraction and manifold reconstruction (three isolated local Python fixtures passed), experimental Skyrim static compressed mesh chunks/strips/big triangle reader, and native candidate batch review with reciprocal geometric seams, NAVI registration/location/grid checks and door backlink inventory. Registration manifests carry candidate payload fingerprints; no invented opaque NAVI fields. Native helper compilation, compressed/convex retail fixtures, unknown NAVI suffix/NVCI generation and playable export remain unverified. Full integration regressions not executed; no milestone score change.

### Native navigation staging and collision pending items
Added opt-in interior NAVM ESP staging, XXXX framing, stable mesh IDs, native NVDP/XNDP triangle bindings, reciprocal index diagnostics and read-only GECK-finalized-copy review. Skyrim compressed no-transform sentinel and quaternion transforms now supported in source; optional Fallout 4 native physics backend handles restricted static identity-root triangle meshes and compound transforms. Native bridge and backend integration unverified; full suite blocked by local GitHub DNS, no actual GECK execution. Referenced compressed chunks, additional primitives, fully independent NAVI generation and native runtime verification still open. Existing milestone estimates unchanged.

### Pending native AutoNav continuation
Added ordinary non-island interior NVMI/NVCI generation, counted connection reference decoding, candidate master-NAVI extension ESP copy (exactly FalloutNV.esm, new interior cells, preserve all base registrations), reciprocal seam/door checks and NVCI graph review. Added obstruction-only sphere/capsule/cylinder/multisphere conservative bounds to Nifly and optional FO4 sphere/capsule adapter; raster/stair filtering and incremental tile fingerprint integration. Referenced compressed chunks remain unsupported; new native chunk inventory command aids fixture research. Five isolated Python codec/bounds tests passed; full repository and native bridge tests unexecuted due GitHub DNS. Exterior/island/preferred navigation, master topology edits, independent native fixtures and game-runtime certification remain open. No score change.

### NAVI variant review pass
Added explicit exterior NVMI payload candidates with reference-calibrated signed XY/YX grid order, preferred neighbor partition and explicit preferred value, bounded read-only island payload decoding, roundtrip registration/door/connection checks, CLI inspection and strict NVCI review. Five isolated codec unit tests passed; integrated repository and retail/GECK tests not run. Exterior and preferred output remains payload-only, island emission and existing-master topology modification remain gated. Direct ESP writer remains new-interior-only. Milestone estimates unchanged.

## Critical path
1. Stable project FormID allocation, typed native record schema and dependency-safe edits.
2. Integrated native interior cells, architectural assets, room/portal/trigger volumes, placed references and collision.
3. NPC records, inventories and AI packages; quest actor bindings.
4. Verified GECK compilation and result-script attachment, runtime quest stages, objective markers and dialogue.
5. Native navmesh/door links; in-game vertical slice and independent xEdit/GECK inspection, saves and traversal.
6. Blended terrain authoring, live chunk streaming, native LOD and portal visibility; hardware measurements before broad content generation.
7. Expand remaining content editors, audio and native cross-game adapters; prioritize local original voices later.
These priorities are proposed engineering decisions, not a promise of full compatibility. Fallout 76 remains offline, no backend emulation or online modification. No retail assets in repository. Flagstaff remains contemporary to 2281 and original characters only.

## Historical development notes
Earlier entries are retained for provenance; pending CI statements may have been superseded by merged PRs.

# Master development checklist — 2026-11-26
Status key: **V** verified by a completed CI run or public-fixture build; **I** implementation exists but scope/engine testing is limited; **B** external bridge/plan, not an independently verified integration; **P** pending. A CI pass does not establish retail-game compatibility. Instancing, books and their tests passed CI; native worldspace experiments remain I until verification.
| Area | V / I / B | Pending production milestones |
|---|---|---|
| 1. Infrastructure | V: MIT core, source/CLI, Windows/Linux/macOS portable builds, bundled wiki, CI. I: desktop tabs, tool detection, declarative extension manifests | Installers, updates, signed releases, executable SDK, dependency management |
| 2. Engine coverage | V: public TES3/TES4 fixtures and legacy/modern NIF roundtrips. I: game profiles. B: OpenMW launch | Retail game smoke tests, Arena/Daggerfall readers/editors, Oblivion Remastered and Starfield special formats |
| 3. Records | I: TES3 inventory and static override, FNV SQLite record index and GMST writer. B: xEdit audit/launch | General typed schema/record writes, stable references, master remapping, Mutagen, visual record inspector |
| 4. Mod management | I: header cache, topological order, conflict chains, patch proposals, ZIP installation, profiles and loose-file staging | libloot, archive precedence, VFS, full AutoPatch, save checks, mod source integration |
| 5. World editor | V: public Flagstaff DEM build. I: scene transforms, OBJ import, terrain geometry, region/placement proposals; OpenGL viewport, instancing/BVH, native FNV terrain ESP experiment and sculpt history | Independent WRLD/CELL/LAND validation and general editing, streaming chunks, sculpt/paint, snapping/gizmos, roads, settlements, maps, regions, navmesh/path grids, precombines/previs |
| 6. Asset Forge | V: legacy and modern native NIF roundtrip, generated foliage package, material texture generation. I: atlas, mipmaps, UV remap, normals/specular/cubemaps | Native collision, animation, wind, architecture, mesh/material editing, modern shader/BGSM and Starfield .mesh |
| 7. LOD Forge | V: billboard/atlas, terrain mesh, GL LOD tests. V: instancing/BVH tests and 2,500-tree benchmark. I: dirty tile planning. B: xLODGen/TexGen/DynDOLOD, MGE XE, OpenMW paging settings | Native worldspace LOD serialization, texture-aware bake, BC compression/mipmap coverage, terrain seams, streaming, in-game benchmark |
| 8. Version control | I: Git checkpoints, history, branches, diffs, checksums. B: Spriggit | Semantic record diff/merge, conflict editor, LFS, rollback UI |
| 9. Content and scripting | I: fragment inventory, books/notes/journals, page preview and localization. B: Caprica/Champollion | Native BOOK/NOTE, covers/fonts/markup, skill books/tomes, quests/dialogue/scenes, VMAD, script IDE, AI packages, spells/perks/recipes, inventory/leveled lists |
| 10. Audio/localization | I: FUZ and string codecs, translation memory and placeholder checks | WAV/XWM, lip sync, Wwise, voice workflow, machine translation, game-specific string encodings |
| 11. Interface | B: FFDec SWF import/export | GFx validation, HUD/menu editor, custom map markers, fonts and icons |
| 12. Testing | V: CI public fixtures, generated NIFs, USGS and Mesa render tests. I: asset audit, frame-time comparison, forest benchmark. B: game launch/reload plans | Engine smoke tests, save/log management, runtime debugging, hardware profiling, crash interpretation |
| 13. AI and documentation | V: offline wiki bundled/tested. I: FTS search, template planner, local advisory model interface and retrieved references | Actual local inference smoke test, verified executable actions, transaction/undo, richer local wiki links, licensed technical reference expansion |
| 14. Distribution | V: portable builds. I: ZIP manifests, simple FOMOD. B: BSArch | Native archive verification, conditional installers, dependency manifests, changelogs, explicit approval for public publishing |
## Next major work blocks
1. Native worldspace editing: shared terrain/cell model, FNV write/validate, real data roundtrip.
2. Production rendering: terrain chunks/streaming, direct GPU surface, material/shadow/reflection rendering, collision visualization.
3. Content editor: native book/note records, generic records, quests/dialogue and script bindings.
4. Asset pipeline: collision, modern materials, native LOD assets; integrate licensed existing tools where practical.
5. Mod manager: libloot, archive precedence, profile activation and safe patch creation.
Flagstaff remains a regression testbed; creative design is separate. Keep original game assets out of the repository. Source changes and tests are not claims of game compatibility.

## Verified rendering benchmark
2,500 instances, 1,550 visible, 16,004 triangles in all modes. Draws 1,607 -> 3; median 61.28 -> 36.35 ms with instancing. Hierarchy tested 1,970 objects rather than 2,500, but median 37.11 ms (no gain over flat instanced culling in this scene). Mesa software, five frames per mode, no physical GPU benchmark. See https://github.com/richmarin1985ce/chimster/actions/runs/45903626073 .

## Current development branch
- Experimental native static placement (STAT/REFR), landscape base texture records (TXST/LTEX/BTXT), desktop terrain sculpt/paint brushes and undo/redo, FNV book and text-note writers, portable collision proxy and experimental native static box collision. Pending CI and independent game validation.
- Oblivion Remastered separate legacy/Unreal package classification and release snapshot comparison. Fallout 76 offline client-file metadata inspection only; no backend emulation, live integration or online modification.
- Minigame editor: portable original grid adventure, map validation, desktop editing and playable standalone browser export. Native game integrations pending; neutral feature names across the application.

- Worldspace Validator: New Vegas group hierarchy, ownership and coordinates, master-relative FormID resolution and merged-load-order conflict checks. CLI/desktop, Flagstaff CI gate; pending verification. Source-versus-merge preservation, other game schemas, navmesh connectivity and external LOD chunk checking remain outstanding.

- Five-task follow-up: terrain-snapped static/readable placements, sparse alpha layer encoding, smooth/flatten and terrain project reopening, compound portable collision proxies, same-plugin book/note placements. Validator gate on native world output. All new changes await CI; actual game compatibility is still unverified.

## Latest verified baseline — PR 12
All seven workflows passed, merged at 4bc8005ddb4a69204fdc285e809b2baab6b55f05. Foundation: 143 discovered, 132 passed, 11 optional skips. Separate workflows exercise native NIF, OpenGL, public fixtures and preview packaging. Native FNV static/placement records, base and sparse alpha landscape layers, terrain snapping, smooth/flatten, portable compound collision, experimental static Havok box, native books/notes and their placement, hierarchy validator, compatibility inventory and portable minigames are implemented and CI-tested within their scope. Desktop interaction and retail engine behavior still need independent tests. Neutral tool names; no Fallout 76 online/backend emulation.
## Landscape quadrant texture budgets — next
The user clarified that quads means per-cell landscape texture quadrants, not mesh topology. Classic Oblivion supports nine textures per quad; FO3/FNV GECK supports seven. Reference: https://geckwiki.com/index.php/Category:Landscape and https://www.gamesas.com/how-prevent-lines-between-exterior-cells-t46244.html . Four quadrants per exterior cell, with separate base and alpha layer allocations. Existing FNV writer deliberately limits alpha layers to four plus base; that is a conservative implementation constraint, not the engine maximum. Do not raise it until native layer indexing and rendering have been checked.
- Add explicit game-specific limits; unverified titles (including Oblivion Remastered) remain unknown, not inherited blindly.
- Count all allocated texture layers, even zero-opacity layers; report distinct texture IDs and repeated IDs separately.
- Prevent over-budget brush/procedural edits; expose per-quad slot inspector, usage estimates, explicit replace/remove operations and review-only consolidation suggestions.
- Check final merged LAND records and shared quad/cell boundaries; never silently discard or normalize authored layers.
- Test limit and limit+1, zero-alpha allocations, duplicate layers, four independent quadrants, merge overrides and deterministic terrain LOD compositing.
- Native classic Oblivion landscape writing remains pending.

## Sections 1–16 development pass
See checklist-01-16-progress.md. Implemented narrow native staged record edits and payload comparison, quadrant budget checks/desktop inspector, modular buildings and collision recipes, mixed-LOD shared-perimeter terrain tiles, chunk storage and selective loading, portable quest/dialogue authoring/playtest, skill book fields and Papyrus structural checks. New CI pending. Do not mark broader categories complete.

## Native compound collision
Implemented explicit static multi-box Havok list serialization for FO3/FNV, separate component material and list material assignments, 128 game-specific material IDs, shared geometry/collision scale and native reopen validation. Original building recipes include editable material defaults. CI and independent engine behavior remain to be verified. Per-child sound/FX may be overridden by the list material; no promise of mixed-material runtime fidelity. Complex triangle/MOPP collision and other engine families pending. See compound-collision.md.

## Quest and interior development
PR15 native compound collision passed seven workflows and merged. Current branch: visual quest graph, bounded exact portable state exploration, experimental QUST/DIAL/INFO stage/objective/response/choice/condition serialization; portable room/portal/trigger/node layout and conservative visibility candidate validation. Pending CI. Native runtime stage progression, actor/faction/reputation conditions, additional game aliases/scenes, native room/portal/multibound/occlusion/trigger records and renderer portal clipping are still outstanding. See quest-dialogue-interiors.md.

- Quest follow-up: explicit master-origin reference binding with validated types, NPC speaker assignment, actor/faction conditions, objective target records, GECK result-script source plans, portable trigger enter/exit and camera frustum portal filtering. CI pending; compiled scripts, native trigger/room records, recursive aperture clipping and actual engine tests remain open.

## Section 3 focused pass
PR16 merged after seven successful CI workflows (159 foundation tests passed, 12 skipped). New branch adds stable FormID ledgers for world/quest/record projects, typed native field editing with unknown-byte preservation, selected top-level native record creation, guarded draft removal, visual side-by-side comparison and fail-closed master slot permutation. No blanket renumbering, unknown-schema remap, arbitrary deletion or direct Mutagen integration. Pending fresh CI, retail game validation and broader schemas. See record-editor-completion.md.

## Extended records, characters and gameplay pass
PR18 passed seven workflows and merged at 00ad4b7745089065089d2312d2ca05b98fd76d8d. Current branch: 24 FNV top-level record project types (18 direct, six template-based), native reputation/faction ranks/relations, containers, leveled lists, ammunition, encounter zones, effects, perks, classes, voice types, keys and consumables; bounded template-based actor/equipment/race/AI/magic-effect authoring; merchant service flags, stats, schedules and fame/infamy conditions. Compressed typed record edits, additional master permutation schemas, typed references and local list cycle checks. Original Flagstaff gameplay fixture. CI and retail-game verification pending. NPC FaceGen/full scratch generation, complete merchant wiring, general remapping and Mutagen bridge remain pending. See gameplay-records.md.

## Section 14 Quest Studio follow-up
PR19 merged after seven green workflows. Added native FNV quest flags/conditions/script links, multi-line response records, response flags and speech challenge/animation binding, explicit embedded source drafts and guarded external compiled-script attachment, indirect stage recursion checks; actual CK DialogueViews v12 XML inspect/remap/reposition and desktop editor, portable alias/scene timeline. Pending CI. Native compiler execution, game verification, scratch XML generation and native Skyrim/FO4 alias/SCEN/DLBR/DLVW records remain open. See quest-studio.md.

## Section 1 core infrastructure
PR20 merged after seven successful workflows, foundation 179 passed/12 skipped. New shared project store, artifact hashes/deduplication, revision transactions and rollback, native FNV quest/record build + ledger integration, unified desktop dashboard, dependency pin/check and readiness reports, explicit executable extension protocol, offline verified versioned app installs/activation/rollback, core management UI, three-platform installer build/smoke workflow. Pending new CI. Remaining: direct edit-session integration of every tool, dependency version/runtime probes and automatic installation, network update discovery, OS-specific signed installers and publisher authentication, extension isolation/sandboxing. Scope is local-first and no public publishing. See core-infrastructure.md.

## Completion sequence
PR21 merged, eight CI workflows green, 188 foundation passes/12 skips, three installer platform smoke tests. Follow order 24, 20, 16, 11, 6, 13, 25. Current development adds formatted wiki navigation/HTML export/link audit, portable localization catalogs and workbench, illustrated book previews, BC1/BC3 compression and alpha coverage/height packing, interactive budgeted blended landscape painting. See [completion pass](completion-pass-24-20-16-11-6.md). New CI pending; no blanket completion or engine verification. Next close remaining scope gaps, then semantic comparison/merge and packaging.

## Reconciliation
PR23 supersedes overlapping PR22 architecture; retain main catalog schema and selectively port missing features with regression tests. PR17 roadmap numbering is canonical. No retail certification.

### Section 14 — DialogueViews generation
PR26 merged at 4c333a74222f23283d525a42dd318b4dce9fc3d1. Observed v12 subset scratch generation implemented; regression tests added, execution deferred by user due to Actions quota. Explicit graph binding adapter added in follow-up; desktop integration, native DLBR/DLVW synchronization, resource templates and official editor verification remain open. No compatibility certification.

Section 14 follow-up: PR27 merged at 1e63b5752a24967d5d446b4fd2f670b7ed74ff1f (graph adapter); PR28 merged at 7e07aad99f8847b7111c344e68dbb1e1a8ed6a2f (branch layout). Both await regression execution. CLI generation and CLI regression fixture added in subsequent change; desktop controls and native record synchronization remain open.

Section 14: PR29 merged at 87aa7a6b0883009e80c8699d5d3a273a4dce1520; CLI regression execution deferred. Follow-up adds same-topology resource-preserving template generation API and synthetic regression fixture; execution deferred. Arbitrary topology/style synthesis, desktop integration and native record synchronization remain open.
