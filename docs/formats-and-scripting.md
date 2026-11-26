# Scripting, audio and localization
## Papyrus and legacy scripts
The fragment inventory tracks script bindings but does not yet generate engine-specific wrappers or edit VMAD. Keep PSC source alongside compiled PEX and preserve generated fragment names/properties. Caprica and Champollion adapters construct external compilation and decompilation commands; they require separately installed versions and appropriate game script libraries. Native compilation has not been tested in actual games. TES3 and GECK script languages are distinct from Papyrus and OpenMW Lua.

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
