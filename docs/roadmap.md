# Feature parity roadmap
Status: design unless implemented and tested. Game-specific capabilities are never assumed interchangeable.
## Authoring
- TES3/OpenMW: cells, land, regions, dialogue, journal, scripts, records, NIF and BSA; investigate OpenMW-CS rendering, ESM reader, Qt editor and Lua runtime under GPLv3.
- TES4/GECK: result scripts, compiled scripts, quests, dialogue, worldspace, landscape, path grids/navmesh by game, map markers, AI packages.
- Creation Kit: VMAD script/property/fragment bindings, aliases, scenes, dialogue, perks, terminal fragments where supported, materials, particles, animation, facegen, navmesh, locations, story manager, LOD, precombines/previs, archives, Starfield planets/ships/biomes/Wwise.
## Source control
Git, Git LFS optional, binary checkpoints, Spriggit serialization where supported, TES3-specific serialization, semantic three-way merge, stable local record identity and master mappings. Preserve unknown records and fields. Require round-trip validation before writing.
## Fragments
Store owner plugin + local record identity, type, event/stage/index, generated script/function, source path, compiled path and VMAD bindings. Preserve CK-generated wrappers; edit body separately; validate properties and references; compile with game-specific toolchain and compare plugin binding. Old result scripts and OpenMW Lua are separate adapters.
## Live testing
Launch installed game or extender via explicit profile, isolated data/save/logs, monitor process, test commands. OpenMW reloadlua; Starfield ReloadScript; xNVSE CompileScript for supported UDFs. Full plugin changes and unsafe schema changes require restart. Never silently overwrite original game assets.
## Localization
Native STRINGS/DLSTRINGS/ILSTRINGS codecs, stable IDs, versioned translation memory keyed by language/context, placeholders, encoding per game, terminology, missing/duplicate detection. Legacy embedded strings and OpenMW localization separate.
## Audio
FUZ pack/unpack, WAV/xWMA validation, batch audio conversion, game-specific naming, lip generation via locally installed LipGen/FaceFX where permitted, Wwise for Starfield, transcript/voice line tracking, subtitle timing. No proprietary voice or game assets bundled.
## UI/maps
JPEXS FFDec adapter for SWF/GFx and ActionScript, safe previews and round-trip tests; map marker record placement and custom icon art/atlas, game-specific ID and UI compatibility; source assets editable; no Flash browser plugin dependency.
## Release
Reproducible archive, file manifest/hash, requirements, metadata, changelog, optional FOMOD, game-specific BSA/BA2, platform constraints; Nexus update API with author token, Bethesda Creations via official editor, Steam Workshop where supported, Mod DB and GitHub packaging. Publishing requires explicit approval.
## Reference index
- https://openmw.org/faq/
- https://openmw.readthedocs.io/en/stable/
- https://openmw.readthedocs.io/en/latest/manuals/openmw-cs/index.html
- https://starfield.creationkit.bethesda.net/Creation_Kit_Menu
- https://starfield.creationkit.bethesda.net/Category:Fragments
- https://starfield.creationkit.bethesda.net/ReloadScript
- https://skyrimck.uesp.net/wiki/Main_Page
- https://geckwiki.com/index.php?title=CompileScript
- https://en.uesp.net/wiki/Skyrim_Mod:Mod_File_Format
- https://github.com/morrowind-modding/morrowind-modding.github.io
- https://mutagen-modding.github.io/Spriggit/
- https://mutagen-modding.github.io/Spriggit/backups/
- https://github.com/jindrapetrik/jpexs-decompiler
- https://wiki.beyondskyrim.org/wiki/Arcane_University:Custom_Map_Marker_Implementation
- https://wiki.beyondskyrim.org/wiki/Arcane_University:File_Localization
- https://github.com/Nukem9/FaceFXWrapper
- https://openfacefx.com/docs/api/exporters/
- https://www.nexusmods.com/skyrimspecialedition/news/15454
