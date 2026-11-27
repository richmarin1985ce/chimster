# Completion pass: documentation, localization, books, textures and landscape
Section 1 PR21 merged at a9f8ca760a2a6b416372e6d81bfb13d4079490b2 after 8 green workflows (188 of 200 foundation tests passed, 12 optional skips; Windows/Linux/macOS installer smoke tests green).
## 24 offline wiki
Safe Markdown subset, headings, code, bold/italic, local document links, desktop back navigation, standalone offline HTML and internal-link audit. External links are not fetched or activated; raw HTML is escaped, fragments resolve to the page rather than a heading. Full Markdown tables/images and broader licensed technical references remain pending.
    python -m chimster wiki-export manual-html
    python -m chimster wiki-check-links
## 20 localization
Versioned catalogs for books, portable and native quest/dialogue, and selected record projects. Stable IDs, exact source hash, exact context translation memory, validation of placeholders/encoding and advisory glossary. Desktop workbench. Apply only fully translated valid catalogs; no automatic translation model or paid service. Native FNV uses cp1252; choose utf-8 for portable documents. Native quest responses must have explicit stable IDs. Native localized string-table packaging and native plugin extraction across games remain pending.
    python -m chimster localize catalog book book.json en es catalog.json
    python -m chimster localize check book.json catalog.json --encoding cp1252
    python -m chimster localize apply book.json catalog.json translated.json --encoding cp1252
    python -m chimster localize remember book.json catalog.json memory.sqlite
    python -m chimster localize reuse book.json fresh-catalog.json filled.json memory.sqlite
## 16 books
Portable book cover and page illustration preview, three font families and three alignments, local image processing and safe HTML. Layout schema 1, optional font/ alignment/ cover relative image, illustrations list of page/image/caption. Images do not become native in-game textures or book markup. Native FNV plain-text export remains separate. Large native subrecords, additional game formats, fonts and actual in-game illustrated books remain pending.
    python -m chimster book-layout book.json layout.json images illustrated-output
## 11 textures
Deterministic CPU BC1, BC1 with binary alpha, and BC3 DDS export, mip chains, approximate alpha-test coverage preservation and authored height-in-alpha packing. Simple endpoint compression is not high-quality optimization and is not a complete BCn suite; use an external compressor for production quality. HDR, BC5/BC7, native material libraries and engine-specific parallax shader configuration remain pending.
    python -m chimster texture-compress source.png output.dds --format BC3 --alpha-coverage
    python -m chimster texture-height-alpha normal.png height.png packed.png
## 6 landscape
Interactive blend and erase modes in existing terrain editor, sparse 17x17 vertex alpha layers, shared sample positions, conservative four-overlay plus base budget checked before committing stroke, undo/redo, project save/reopen and simple color-blend preview. Erasing retains allocated slots; explicit removal helper frees a slot. Mean vertex opacity is not rendered texture coverage. Brush changes adjacent shared vertices consistently from equal inputs, but varying base textures/layer order and previously mismatched edges can still produce seams. Native landscape writer still has four-overlay implementation limit, not the actual game limit. Saved alpha_layers.json matches FNV content alpha_layers format; merge with author-supplied texture definitions and paint grid for export. No silent allocation eviction. Interactive slot removal/optimization, verified native texture budget expansion and texture-aware LOD compositing remain pending.
All additions on this branch require fresh CI and, where applicable, independent game/desktop tests. No public release.
