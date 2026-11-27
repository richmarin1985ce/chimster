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
