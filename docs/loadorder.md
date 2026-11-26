# Load order and AutoPatch foundation
MIT core. No libloot source or binary bundled. libloot is GPL-3.0-or-later; use an independently installed helper with an audited interface or comply with GPL for combined distributions.
## Implemented
- Explicit active list, overlay data directories, master graph, deterministic topological order, missing masters/cycles/case collisions.
- SQLite content-addressed header cache scoped by game and parser schema. Every scan hashes the input; unchanged content avoids structural parsing. No persistent normalized record cache yet.
- Review-only patch consolidation planner using externally normalized complete snapshots. Provider, origin plugin/local object ID, signature and semantic hash; never use raw load-order FormID as durable identity. Requires explicit attestation of review and absence of side effects. Does not disable plugins.
## Runtime policy
Build before launching the game; never replace a loaded plugin. Freeze mod list and hashes, sort with libloot, obtain full normalized records and references with xEdit (or TES3 adapter), resolve policy rules, write to an isolated temporary patch, reopen and validate, compare effective winners and dependencies before and after, approve and atomically publish a profile-local patch with a stable name. Keep original plugins installed and restore prior profile/patch together. Existing saves may depend on plugin identities even for override-only patches; never promise safe mid-playthrough removal. Restart after changes.
## Incremental architecture
Index normalized fields and references by game + backend version + plugin content hash + resolved master identities, invalidate changes and dependent records, include rules/metadata/assets/localization and order in build key. Persist reverse references and field-level provenance; use backend-native schemas, not generic last-wins field merging. Select affected records; compare against full rebuild in CI. xEdit cache must remain stable per game/profile. Fast debug report includes provider chain, winner, source paths, validation errors, changed dependencies and timing. Merge leveled lists, keywords, NPC packages and other arrays only with record-specific rules and explicit handling of deletions, ordering, intentional overrides, conditions, navmesh, scripts, VMAD, worldspace and persistent refs.
## Not yet implemented
libloot helper, full record export, actual ESP/ESL/OMW patch writer, field merges, post-build equivalence validation, load order application, save-aware migration and UI. Header graph is not a substitute for LOOT/engine ordering. No real-world speedup measured.
## References
- https://github.com/loot/libloot
- https://loot-api.readthedocs.io/en/latest/api/sorting.html
- https://tes5edit.github.io/whatsnew
- https://github.com/TES5Edit/TES5Edit
- https://tes5edit.github.io/docs/7-mod-cleaning-and-error-checking.html
- https://wrye-bash.github.io/docs/Wrye%20Bash%20Advanced%20Readme.html
- https://mutagen-modding.github.io/Synthesis/LoadOrder/
