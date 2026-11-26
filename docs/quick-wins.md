# Quick-win implementation pass
Status: experimental source, not a release. The cross-platform CI workflow builds portable PyInstaller directories and Python packages; installers, signed binaries, and successful runs are not yet established.
- Tool discovery: PATH or explicit override, no automatic downloads.
- SDK: versioned declarative manifests; does not run extension code.
- Mod manager: isolated ZIP extraction and saved profiles, not game activation, VFS, uninstall, 7z or FOMOD execution.
- TES3: inventory and narrow STAT model override writer for a self-contained base plugin. Writes a new ESP and checks its own parser; no runtime verification. Does not consolidate arbitrary patches.
- Atlas: RGBA rectangle packing, gutters, PNG writing and non-tiling UV transform. No automatic image decoding, DDS, mipmap coverage or game-native atlas integration.
- Asset validation: loose-file overlay index and reference audit. BSA/BA2 references not resolved.
- Git: branch creation, text diffs and path history. No semantic record diff.
- FFDec: external CLI export/import plans for SWF scripts/resources; GFx and visual editing unverified.
- FOMOD: minimal metadata and required files, not a conditional installer. Requires MO2/Vortex smoke test.
## Upstream sources
- https://github.com/loot/libloot (current bindings are in the main repository; old libloot-python is archived)
- https://loot-api.readthedocs.io/en/latest/api/sorting.html
- https://github.com/jindrapetrik/jpexs-decompiler/wiki/Commandline-arguments
- https://github.com/BadDogSkyrim/PyNifly
- https://github.com/ousnius/nifly
- https://geckwiki.com/index.php/BSA_Files
