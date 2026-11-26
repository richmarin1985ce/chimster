# Integration quick wins
## Implemented
- Texture Forge native height-to-normal, mask-to-specular, optional normal alpha packing, PNG/DDS, renormalized normal mipmaps, LDR panorama-to-six-face DDS. Independent Pillow decode tests run in preview jobs. Cubemap has no mipmaps or HDR prefilter; no game-specific binding yet.
- Desktop Texture Forge, load-order scan, installed-tool discovery tabs. UI source only; interactive smoke test still needed.
- Isolated loose-file profile staging by ordered source precedence; never modifies the live installation, no VFS or archive precedence.
- Typed command plans for DirectXTex texconv, BSArch, Caprica, Champollion and Spriggit. Explicit execution, no arbitrary shell commands. Actual external utilities not run in CI; version-specific options and output formats need independent verification. Spriggit supports explicit version pinning and may download code packages; use trusted dependencies and disposable workspace.
- Local SQLite FTS5 documentation index with source path snippets. No wiki crawler or embedded upstream content.
- Optional loopback Ollama advisory planning with JSON schema and allowlisted action labels. No execution, no remote model credentials or file upload. User must configure a truly local/offline model; localhost alone cannot guarantee the service's inference location. Mocked API test only.
## Commands
    python -m pip install ".[textures]"
    python -m chimster textures material height.png mask.png material-out --pack-alpha
    python -m chimster textures cube panorama.png cube-out
    python -m chimster stage-overlay staged-data base-data mod-a mod-b
    python -m chimster knowledge notes.sqlite --rebuild docs --query "terrain lod"
    python -m chimster local-ai local-model newvegas "Plan terrain LOD"
    python -m chimster external-tool texconv config.json
Add --execute only after reviewing the tool plan. Config supplies named adapter arguments. Example texconv config: {"exe":"C:/Tools/texconv.exe","source":"height.png","out":"dds-out","fmt":"BC3_UNORM","mips":0}. See typed functions for other inputs.
## References
- https://github.com/microsoft/DirectXTex/wiki/texconv
- https://github.com/Orvid/Caprica
- https://github.com/Orvid/Champollion
- https://github.com/Mutagen-Modding/Spriggit
- https://github.com/TES5Edit/TES5Edit/blob/dev-4.1.6/BSArch.dpr
- https://docs.ollama.com/capabilities/structured-outputs
