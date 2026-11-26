# Development pass: sections 1–16
All work is staged on dev/checklist-01-16; no retail game verification. Neutral tool names. The previous PR12 and documentation PR13 are merged after their CI passes.
## New capabilities
- Landscape budget: classic Oblivion (20-byte headers), FO3/FNV (24-byte headers), raw and compressed LAND inspection. Counts allocated base/alpha slots including zero-opacity, explicit vs implicit base, repeated textures, malformed layer headers and VTXT vertex data. FNV world validation enforces overflow checks. Existing FNV writer keeps conservative four alpha slots; no assumption of Remastered limit.
- Record editor: FNV field inspection and allowlisted staged text edits, identical plugin filename in separate directory, stale-hash check, unchanged raw fields and all other record payloads, recursive enclosing group size fixups. No arbitrary field edits, record creation, compressed writes, FormID remapping, plugin activation or general semantic schema.
- Revision comparison: added/removed/changed records by origin and local FormID with payload hashes; use identical filenames for revision identity. Not semantic merging.
- Building generator: original parametric rectangular building with doorway and separate wall/floor/roof collision pieces. OBJ and recipe, no native compound Havok output yet.
- Terrain tiles: 32-interval cell tiles keep full-resolution outer perimeter at all supported strides, use transition fans to avoid T-junctions between same-size adjacent mixed-resolution tiles. Not a full terrain renderer or game LOD format.
- Chunk store: deterministic signed XY buckets, SHA-256 manifest and selective loading. Not yet continuous viewport streaming.
- Quest editor: local JSON stage/choice editor and branching playtest, boolean condition/set flags, structural reachability and exit checks, localization IDs. No native QUST/DIAL/INFO, visual node graph or complete state-space proof yet.
- Native books: optional New Vegas skill enum and cannot-take flag. In-engine effect unverified.
- Script checker: advisory Papyrus block matching, not compilation or semantic analysis.
## Commands
    python -m chimster landscape-budget oblivion Mod.esp
    python -m chimster record-inspect Mod.esp Mod.esp 0x800
    python -m chimster record-edit-text Mod.esp staged/Mod.esp Mod.esp 0x800 FULL "New title" EXPECTED_SHA256
    python -m chimster record-compare old/Mod.esp staged/Mod.esp
    python -m chimster building building-output --width 8 --depth 6 --height 3
    python -m chimster terrain-tile heights.json tile.obj --spacing-m 4 --step 8
    python -m chimster chunk-build placements.json chunks --size 128
    python -m chimster chunk-load chunks 0 0 --radius 1
    python -m chimster quest-check quest.json
    python -m chimster script-check Example.psc
    python -m chimster book native book.json book.esp --model book.nif --skill 8 --untakeable
See https://tes5edit.github.io/fopdoc/FalloutNV/Records/Values/Skills.html for the skill enum.
## Scope still pending by checklist section
1 installers/update/SDK; 2 wider game adapters; 3 generalized typed record writes; 4 libloot/VFS/archive precedence; 5 native editing, roads/interiors/navmesh; 6 blended brush and texture consolidation; 7 merge preservation, external LOD/navmesh; 8 direct GPU surface/continuous streaming; 9 native architectural packages, animation/materials; 10 native compound collision; 11 advanced texture processing; 12 native LOD tiles; 13 semantic merge; 14 native quests and visual graph; 15 script IDE/compiler integration; 16 native book markup/other engines.
