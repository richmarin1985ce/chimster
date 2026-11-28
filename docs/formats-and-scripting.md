# Scripting, audio and localization
## Papyrus and legacy scripts
The fragment inventory tracks script bindings but does not yet generate engine-specific wrappers or edit VMAD. Keep PSC source alongside compiled PEX and preserve generated fragment names/properties. Caprica and Champollion adapters construct external compilation and decompilation commands; they require separately installed versions and appropriate game script libraries. Native compilation has not been tested in actual games. TES3 and GECK script languages are distinct from Papyrus and OpenMW Lua.

### Staged Papyrus builds (Section 15)
Use an independently installed trusted Creation Kit compiler or Caprica, plus the appropriate local game script libraries and flags. No compiler binaries or proprietary scripts are bundled. Preview is the default:
    
    python -m chimster papyrus-build skyrimse ck /path/to/PapyrusCompiler.exe source/Example.psc source/TESV_Papyrus_Flags.flg build --import /path/to/game/Source
    python -m chimster papyrus-build skyrimse ck /path/to/PapyrusCompiler.exe source/Example.psc source/TESV_Papyrus_Flags.flg build --import /path/to/game/Source --execute
    python -m chimster pex-inspect skyrimse build/Example.pex

The output must be a new directory outside the source/import/flags directories. The build uses a private staging directory, captures compiler messages with file/line/column where recognized, checks PEX magic, game-family ID, major version and bounded header strings, then publishes the artifact plus compile.json. The source, flags and executable hashes are recorded; imported libraries are not yet fingerprinted. A successful header check is not full PEX validation or runtime certification. Only unnamespaced single-file scripts are supported; Skyrim/SE/AE/VR and Fallout 4/VR use family checks, not version-specific certification. The existing GECK donor attachment remains separate for legacy games. Compiler execution is explicit and unsandboxed. Synthetic regression fixtures are committed; execution remains deferred under the current testing policy. Real compiler/engine verification, namespaces, batch/dependency builds, script editor, VMAD, decompile verification, legacy compiler and runtime debugging remain open.

References: https://open-papyrus.github.io/docs/Creation_Kit/Skyrim/Compiler_Reference.html and https://github.com/Orvid/Caprica/blob/master/Caprica/main_options.cpp .

### Script editor and syntax definitions
Open Narrative → Script editor. Supports local source opening, new-copy saves, undo, line numbers, scoped highlighting, Papyrus advisory checks, explicit local compilation of unchanged saved source and compiler results. The game determines the default language for ambiguous extensions when opening a file; manual selection is available. UTF-8 sources only.

The original grammar library uses the Sublime Text v2 model: ordered regular-expression matches, scopes and named push/pop contexts. Initial grammars cover Papyrus, GECK, Oblivion, Morrowind and OpenMW Lua. These are bounded highlighting definitions, not complete language parsers. No arbitrary third-party grammar imports or existing Sublime package code are included. Lua long brackets are covered through four equals signs. Versioned game API symbol libraries are pending.

    python -m chimster script-syntax-export papyrus Papyrus.sublime-syntax
    python -m chimster script-syntax-export geck GECK.sublime-syntax

Copy exports into Sublime Text's User packages folder. Actual Sublime loading, desktop execution and compiler execution remain unverified; synthetic regression fixtures are committed but execution deferred. Reference: https://www.sublimetext.com/docs/syntax.html

### API symbols, completion and local libraries
Use Ctrl+Space for an explicit completion chooser; F12 displays matching signatures and descriptions, and navigates to a unique declaration in the current file. The initial original API seed catalog separates game families and requires explicit opt-in to SKSE, F4SE, OBSE, FOSE or xNVSE symbols. It is not a comprehensive or version-certified function dictionary. Unknown symbols are not compilation errors.

Index local PSC reads an explicitly selected local Papyrus library (up to 2,000 files and 32 MiB), skips symlink entries, records declaration source paths and line numbers, and associates the results with the current game profile in memory. No proprietary sources are bundled or uploaded by the indexer. The selected library may contain extender or mod functions; provenance is displayed, but runtime compatibility is not inferred. Indexing is synchronous in this prototype. No persistent index, type inference, cross-file go-to-definition, full symbol parser or external version audit yet. Regression fixtures added; test execution deferred.

### Papyrus project builds
The Script editor's Build project action compiles saved flat PSC sources from a chosen project directory. CLI preview is the default:

    python -m chimster papyrus-batch skyrimse ck /path/to/PapyrusCompiler.exe project-source flags/Game.flg build --import /path/to/game/Source
    python -m chimster papyrus-batch skyrimse ck /path/to/PapyrusCompiler.exe project-source flags/Game.flg build --import /path/to/game/Source --execute

The dependency inventory records explicit Scriptname extends and Import links, unresolved names, deterministic ordering and import cycles/blocked nodes. Duplicate case-insensitive script names and inheritance cycles are rejected; missing names and import cycles are advisory. The native compiler remains authoritative. All selected flat source libraries are hashed and copied to private staging, then each project script is compiled using the same snapshot. Artifacts are published only after every compilation passes the existing bounded PEX header check and input inventory is rechecked. The output directory contains PEX files and batch.json; failure before publication produces no output directory. Publication is not crash-atomic. No in-game files are modified.

Only unnamespaced flat sources are included; subdirectories are not searched. Maximum 2,000 PSC files and 32 MiB per inventory. No incremental cache, full type dependency resolution, compiler verification or native engine validation yet. Synthetic regression cases committed; execution deferred.

### Native VMAD inspection and scalar editing
Skyrim-family VMAD version 5, object formats 1 and 2: inspect existing attached script names, status bytes, scalar properties and basic arrays. Object references expose raw on-disk FormIDs and bytes, not resolved load-order identities. Fragment/alias tails are reported as opaque and are not edited.

    python -m chimster vmad-inspect skyrimse Example.esp 0x00000800
    python -m chimster vmad-edit skyrimse Example.esp staged/Example.esp 0x00000800 ExampleScript Count 4 PLUGIN_SHA256 VMAD_SHA256

The second command requires the hashes from the inspection and a separate, new same-name plugin path. Only existing scalar string, int, float and bool values on selected uncompressed record families may be changed. Unrelated bytes, record IDs, master tables, and group labels are preserved; affected record/group lengths are adjusted and the resulting VMAD reopened. Unsupported versions, unknown property types, compressed target records, and opaque fragment tails fail closed. No object reference writing, new script attachment, alias/fragment generation, VMAD remapping, Fallout 4 structs, or runtime certification yet. Synthetic fixtures committed, execution deferred.

Format references: https://github.com/BadDogSkyrim/BethesdaLibrary/blob/main/docs/file-formats/scripts.md and https://github.com/TES5Edit/meta/blob/master/UESPWiki/QUSTDef.wiki .

### Compiler integrations and diagnostics
Papyrus single-file builds accept explicit optimization and backend-dependent release/final switches. Caprica additionally accepts warnings-as-errors. Compiler launch failures and timeouts return structured diagnostics. Recognized compiler locations include filename, line and column where available; the original log and stdout/stderr provenance are retained. The desktop Diagnostics button navigates to matching lines in the current saved source, not arbitrary paths from compiler messages. Batch diagnostics from temporary staged paths may not resolve to the original editor file.

OpenMW Lua scripts can be parsed without executing them using a separately installed Lua 5.1 luac compiler:
    
    python -m chimster lua-check /path/to/luac Script.lua --execute

This is a Lua syntax check only, not a simulation of OpenMW's LuaJIT extensions, engine APIs or runtime.

### Legacy editor compilation handoff
Morrowind, classic Oblivion, Fallout 3 and Fallout: New Vegas now have advisory source block checks and standalone SCPT inspection, source draft preparation and donor attachment commands. Example for New Vegas:

    python -m chimster legacy-script-inspect newvegas original/Example.esp
    python -m chimster legacy-script-prepare newvegas original/Example.esp draft/Example.esp 0x800 Example.txt
    python -m chimster legacy-script-attach newvegas draft/Example.esp compiled/Example.esp final/Example.esp

For Morrowind, use the script name instead of a disk FormID. Preparation changes an existing standalone script, converts UTF-8 source to the supported CP1252 encoding and clears old bytecode and variable metadata. **The draft is not playable.** Compile it in the appropriate native Construction Set or GECK and save a same-name donor copy. Attachment checks script identity, matching source, compiled sizes/counts, record headers and unrelated payloads, preserves the draft's other records and adjusts group lengths. It intentionally rejects broader editor rewrites. It does not establish opcode correctness or genuine compiler provenance. Embedded FNV quest scripts retain the separate quest-attach-scripts workflow. No standalone legacy bytecode compiler, editor automation, generalized remapping, arbitrary encodings or engine verification is claimed.

Regression fixtures cover diagnostic parsing, backend switches, legacy draft/attachment and Lua version checks. Execution remains deferred. Actual installed compiler and editor compatibility must be verified before use.

### Compiler recovery and unchanged-build reuse
Use the Recover PEX desktop action or the staged CLI, with a trusted locally installed Champollion and scripts you have permission to inspect:

    python -m chimster pex-decompile skyrimse /path/to/Champollion Example.pex recovered --execute

The input PEX header and digest are checked, source recovery takes place in a private directory, and a matching PSC declaration and output hash are checked before publishing the PSC and decompile.json. A recovered script is not guaranteed to be original source or to recompile equivalently; namespaces and multiple-file decompiler output remain unsupported.

Project builds now accept the same backend-dependent options as single-file builds, and --reuse path/to/previous-build (also available in the desktop Build project action). All selected source and import entries, roots, compiler binary digest, flags digest, and options must match the previous build key; every PEX is header-checked and hash-checked again. Any changed source invalidates the entire reuse attempt, intentionally avoiding unsafe partial dependency inference. Only explicitly selected trusted local build manifests should be reused. Compiler DLLs and toolchain environment are not fingerprinted; use a fresh build after changes to those. No per-script incremental caching or signed cache provenance claimed.

Batch diagnostics now map recognized staged source paths and unique basenames back to inventoried original paths with source hashes. The editor refuses navigation for stale saved content. Unknown paths are retained in the log without opening them automatically.

Legacy backend scope remains unchanged: xNVSE CompileScript is a runtime UDF mechanism, not a general offline SCPT compiler; OpenMW's script-all is an engine validation path, not a replacement for native TES3 bytecode export. Original editors remain required for standalone legacy SCPT compilation. References: https://github.com/Orvid/Champollion/blob/main/README.md ; https://github.com/Orvid/Caprica/blob/master/Caprica/main_options.cpp ; https://geckwiki.com/index.php?title=CompileScript ; https://github.com/OpenMW/openmw .

New regression fixtures use mocked tool execution. Execution remains deferred, including real compiler/decompiler, editor and engine verification.

## Voice
The formats module packs and unpacks supported FUZ containers. A FUZ is not a speech synthesizer: it contains separate lip-sync and audio payloads. XWM encoding, actual lip-sync generation and Wwise conversion remain unimplemented. Do not republish extracted game voice assets.

## Localization
The formats module handles supported STRINGS, DLSTRINGS and ILSTRINGS containers. Keep the game and language-specific encoding and original string IDs. The SQLite translation memory stores context-sensitive source/target pairs. The audit command compares JSON dictionaries keyed by string ID:
    python -m chimster localization-audit source.json target.json
It flags missing or extra IDs and mismatches in common placeholders and markup. This is advisory; it does not automatically translate or fix strings.

## Interface assets
FFDec bridge commands create or optionally execute external SWF resource extraction and script reimport plans. Use new output paths; Scaleform/GFx compatibility and actual engine UI testing remain necessary.
    python -m chimster ffdec export /path/to/ffdec input.swf export-folder
    python -m chimster ffdec import /path/to/ffdec input.swf output.swf --scripts export-folder/scripts
