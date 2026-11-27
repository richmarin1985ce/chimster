# Wiki and localization workflow
The local wiki renders headings, bold text, inline and fenced code, simple lists, and clickable local page/anchor links. Raw HTML is escaped, remote links are displayed as plain text, and no external resources are loaded. Export a self-contained local HTML manual and audit broken internal links:
    python -m chimster wiki-export manual-html
    python -m chimster wiki-audit
This is a limited Markdown renderer, not a full CommonMark implementation. Links to files outside the indexed manual are reported unresolved, not opened.
Localization catalogs support portable books/quests, native FNV quest JSON and record project JSON, and existing string dictionaries. Explicit native response IDs are required. Native quest multi-line entries are indexed within a response, so insertion may change line identities; stale source checks prevent blindly reapplying old translations. Non-text records, script sources, flags and references remain unchanged. Use the Localization desktop tab or:
    python -m chimster localization-project catalog native-quest quest.json catalog.json
    python -m chimster localization-project suggest catalog.json memory.sqlite en fr suggested.json --reuse-unambiguous
    python -m chimster localization-project review approved.json --encoding cp1252
    python -m chimster localization-project remember approved.json memory.sqlite
    python -m chimster localization-project apply approved.json quest.json translated.json --encoding cp1252
    python -m chimster localization-project pack numeric-strings.json translated.strings STRINGS --encoding utf-8
Catalog entries have stable ID, source, context, target and status. Suggestions require explicit approval. By default, exact context/source match only; optional cross-context reuse suggests a previously approved translation only if a unique target exists for the phrase and language pair. Review enforces placeholder preservation and encoding compatibility. Native tables round-trip through codecs; no automatic plugin localization flags or language filename inference. No remote translation provider or local model is assumed. Terminology glossary and full native localization publish workflow remain pending. New CI pending; real editor interaction and game rendering unverified.
