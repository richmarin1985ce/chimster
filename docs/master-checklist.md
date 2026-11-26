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
