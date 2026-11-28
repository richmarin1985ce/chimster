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
