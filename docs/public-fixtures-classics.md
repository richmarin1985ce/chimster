# Public test fixtures and classic Elder Scrolls research
## Fixture tiers
1. Synthetic Chimster fixtures for malformed data, deterministic builds and write safety.
2. Ortham/testing-plugins (MIT, copyright Oliver Hamlet, 2014), pinned to d9b28a2062a12f3a40bc9b13be9d6f5731c81249. Fetch separately in CI, retain upstream license. Actual game-format examples for TES3/TES4 headers, dependencies, light/medium/full master variants; Skyrim BPTD samples are also compatible with FO3/FNV layouts. BSA/BA2/DDS corpus is available for subsequent adapters. These are not retail master files.
3. OpenMW Game Template: public domain except Pelagiad.ttf (separate font license). Fetch upstream and follow its settings/resources instructions in a disposable installation; test template.omwgame, rendering, new world content and runtime. Audit per-asset licenses before copying. Example Suite additional modules need separate license checks. No original Morrowind content required.
4. Original Arena and Daggerfall are free official downloads; obtain from Bethesda or authorized stores. Freeware is not public domain; do not add original assets, extracted masters, or proprietary binaries to public Git or public CI artifacts. Test locally from user-provided/extracted authorized data; log counts/checksums only. Later retail games require legally obtained files; public mods require permission and compatible licenses, and may depend on missing masters.
## Classic adapters
Arena (1994): OpenTESArena MIT C++ engine and format research, potential reusable parser/rendering reference. GLOBAL.BSA and MIF/INF maps, palettes/sprites, procedural city/dungeon rules; no ESP, Papyrus, NIF or modern tree LOD assumption.
Daggerfall (1996): Daggerfall Unity MIT game code, Unity engine separately licensed. DaggerfallConnect MIT asset API, Daggerfall Imaging 2 MIT, Daggerfall Modelling for 3D browsing/export (exact source license not established). Daggerfall Unity editor tools include dungeon/quest workflows; modern DFU uses .dfmod, asset bundles and WorldData rather than TES3/TES4 plugins.
ArenaToolBox-BSATool: GPLv3 license file; external integration or compliant GPL distribution only. TESA Toolbox (Nexus): 3D map editor; source/reuse license unverified. Daggerfall Dungeon Maker (Rust): CAD-style editor, viewport, block placement, object properties and test launch; no clear project license identified, so reference only unless permission verified. OpenDF GPLv3 alternative.
## Initial targets
- Add distinct classic engine profiles and archive/record adapters, not aliases for Creation Engine records.
- Read archive inventories and preview original local assets; validate format and byte offsets.
- Reuse MIT parsers or port them with original notices; pin upstream commits and check dependencies and file-level rights. Prefer data APIs independent of Unity where practical.
- Shared editor UX: object palette, grid and snapping, viewport, property inspector, undo/history, deterministic generation, quest/record view, test-launch and release packaging. Implement export formats per engine. Do not port unlicensed editor source.
## Sources
- https://github.com/Ortham/testing-plugins
- https://openmw.readthedocs.io/en/latest/reference/modding/openmw-game-template.html
- https://gitlab.com/OpenMW/example-suite
- https://elderscrolls.bethesda.net/en-US/arena
- https://elderscrolls.bethesda.net/en-US/daggerfall
- https://github.com/afritz1/OpenTESArena
- https://github.com/afritz1/OpenTESArena/wiki
- https://github.com/Interkarma/daggerfall-unity
- https://www.dfworkshop.net/daggerfall-connect-source-code/
- https://www.dfworkshop.net/daggerfall-imaging-2-released/
- https://www.dfworkshop.net/downloads/daggerfall-modelling/
- https://www.dfworkshop.net/projects/daggerfall-unity/modding/
- https://github.com/Dysperia/ArenaToolBox-BSATool
- https://www.nexusmods.com/tesarena/mods/110
- https://github.com/JaeTheBoo/daggerfall-dungeon-maker
- https://github.com/kcat/opendf
