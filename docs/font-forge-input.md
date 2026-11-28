# Font Forge input requirements

Support Wacom and other OS-compatible pen tablets, including Windows Ink, Linux tablet input and macOS tablet events where available. Mouse and touch fallback required. Capture position, optional pressure, tilt, eraser and stroke boundaries through a platform-neutral adapter. Never assume pressure support from pointer events alone. Provide freehand glyph drawing, adjustable smoothing, stroke-to-closed-outline conversion, editable quadratic Bezier contours, baseline and em grid, undo, Unicode mapping and TTF export through fontTools. Pressure affects stroke width before outline conversion; retain editable outlines. No proprietary tablet SDK or separate application required for baseline input. Test real hardware separately; synthetic events do not certify tablet compatibility. Preserve native game font registration as a separate export step. No placeholder fonts required. Implementation and hardware verification pending.

## Deferred subsection
Include ordinary phone and tablet touch input, finger drawing and optional mobile stylus pressure. Pause all new Font Forge development until the remaining Section 16 book and note functionality is complete. Existing native font reference preservation remains active.

## Font Forge desktop implementation

The Assets > Font Forge tab imports multiple local TTF/OTF files via native TkDND file drops or a file picker. The persistent library stores content-addressed copies under ~/.chimster/fonts and does not install system fonts or alter game files. Preview uses Pillow and shows family, style, character count, outline format, license metadata and embedding flags. The Create TTF tab authors basic polygon contours with mouse input, Unicode mapping, undo, and export via fontTools. This supersedes the earlier pause for this scope. Pressure, touch, editable Bezier curves, project-level packaging and game-specific font registration remain unverified or pending. Imported fonts are not automatically redistributed; verify their license separately.

### Editable curves and projects
Font Forge now supports explicit on-curve and quadratic control points, TrueType implied midpoints, moving existing points, editing and deleting saved glyphs, and local versioned JSON projects. Save the active glyph before exporting or saving the project. Project files contain authored outlines only, not imported fonts. Existing polygon outlines remain supported. Mouse editing does not certify pen pressure or native touch support. Game registration is still separate.
