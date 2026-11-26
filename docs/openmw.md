# OpenMW bridge — phase 1
MIT code calls separately installed GPLv3 applications. No upstream source or game assets are included.

## Profile example (JSON)
    {"root":"./test-workspace","data":["/path/to/Morrowind/Data Files"],"content":["Morrowind.esm","Tribunal.esm","Bloodmoon.esm"],"archives":["Morrowind.bsa","Tribunal.bsa","Bloodmoon.bsa"]}

Paths are resolved relative to the JSON file. List only actual installed files. Explicit command-line overrides prevent inherited content/data/archive lists from silently changing test order. Engine resources and settings may still come from installed defaults; this is not a security sandbox. Use a disposable workspace. OpenMW-CS launch currently uses its normal configured profile; configure its data-local path before editing. Never edit the original masters.

CLI: python -m chimster openmw discover
CLI: python -m chimster openmw preview profile.json
CLI: python -m chimster openmw launch profile.json
CLI: python -m chimster openmw editor
CLI: python -m chimster openmw reload-plan scripts/example.lua

Lua source changes can be reloaded manually via reloadlua; changed registrations, assets and record changes conservatively require restarting. No simulated console injection.

## Native editor research
Investigate upstream apps/opencs model/world, view/render, document, terrain and shared components/esm3, resource and scene utilities. These are candidate source areas, not verified stable standalone APIs. Audit dependency graph and file-level licenses at pinned revision. A separately distributed GPL-compatible editor component is preferred if direct reuse is practical. Preserve upstream notices and corresponding source; do not import upstream code under MIT. Test native rendering first with redistributable synthetic assets, then user-provided local game files. Next deliverable: cell/land/object inventory with stable identities, TES3 round-trip validation, then a terrain viewport. No CK parity claims before integration tests.

References:
- https://github.com/OpenMW/openmw
- https://openmw.readthedocs.io/en/stable/reference/modding/paths.html
- https://openmw.readthedocs.io/en/stable/reference/lua-scripting/overview.html
- https://openmw.readthedocs.io/en/latest/manuals/openmw-cs/index.html
