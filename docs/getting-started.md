# Getting started
Chimster is an experimental local-first modding workbench. Use copied game files and disposable profiles. No original retail game assets or proprietary tools are included.

## Installation
Python 3.10 or later is required for the source version. From the repository root:
    python -m pip install ".[textures]"
    python -m chimster ui
    python -m chimster --help
    python -m chimster wiki list

Portable previews are built by GitHub Actions for Windows, Linux and macOS. They are not signed installers. The desktop interface depends on Tk; on some Linux distributions you may need the operating system's Tk package. The optional image decoder is bundled in preview builds. PyFFI and geospatial dependencies are optional and must be installed separately in source environments.

## Typical workflows
- Inspect a plugin: python -m chimster inspect newvegas Example.esp
- Inspect tools: python -m chimster tools --game newvegas
- Detect installed utilities: python -m chimster discover-tools
- Search help: python -m chimster wiki search "texture atlas"
- Build a procedural tree: python -m chimster lod tree tree-output
- Generate normal and specular maps: python -m chimster textures material height.png mask.png material-output
- Stage copied loose files: python -m chimster stage-overlay staged-data base-data mod-a mod-b

Use new output folders for generation. Check generated assets in the target engine before distributing a mod. Do not replace an active plugin while the game runs. Most modern record writing, native modern NIF export, archive generation and integrated 3D editing remain under development. See roadmap.md and the relevant module notes for current limits.
