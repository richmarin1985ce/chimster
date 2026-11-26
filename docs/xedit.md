# xEdit backend — Phase 1
Original Chimster code MIT. Upstream xEdit repository is MPL-2.0; check pinned files and dependencies before redistribution. No xEdit executable or source bundled. This bridge uses separately installed Windows executables.

## Staging
Create a dedicated test directory with copied Data files and a game-appropriate plugins.txt. Never point the workspace at your live installation. Profile JSON: {"root":"./test-workspace","game":"newvegas"}. Preview first. The bridge supplies explicit Data, plugin list, cache, backup and temporary directories. It is not an OS sandbox and does not enforce read-only access inside the external application. Mod manager virtual filesystem support and game INI paths require validation on actual installations.
CLI: python -m chimster xedit preview profile.json path/to/xEdit.exe
CLI: python -m chimster xedit launch profile.json path/to/xEdit.exe --operation conflicts
CLI: python -m chimster xedit launch profile.json path/to/xLODGen.exe --operation lod
Use xLODGen executable for the LOD operation, select LOD settings interactively. Output is staged under LODOutput.
CLI: python -m chimster xedit report copied-log.txt

## Asset audit
The bundled original Pascal script, Chimster Asset Audit.pas, reads selected STAT/TREE/FLOR/GRAS/ACTI/MSTT records and emits marker-prefixed lines with plugin, editor ID, load-order FormID, model and winner. It does not change records. Select records and run Apply Script (the bridge sets the script directory); copy audit lines from Messages into a text file. Do not treat load-order FormIDs as durable identifiers. Script and paths need actual xEdit smoke tests; model path fields differ by game. Report ingestion does not validate on-disk assets or detect all conflicts.

## Next milestones
1. Verified game-specific record schemas, stable origin/master identity including light plugins, and semantic diffs.
2. Typed write proposals with explicit target patch, expected old value, required masters and review; no unrestricted script execution from AI.
3. Flora/NIF asset manifest -> verified model paths and game-specific records -> patch -> validate references -> xLODGen or TexGen/DynDOLOD. Keep tree/object/terrain LOD distinct. Do not assign native TREE/SPEEDTREE records to arbitrary static NIFs.
4. Round-trip tests, error reporting and benchmark suites with user-owned game installations. No auto-cleaning or live master edits by default.
5. Static building/rock/clutter LOD reduction, material-compatible atlas packing, UV remapping, game-specific mesh and texture validation.
6. Evaluate xEdit's Delphi record definitions and scripting APIs for reusable MPL-covered modules; retain upstream file licenses and source obligations. Direct source integration is not implemented.

References:
- https://github.com/TES5Edit/TES5Edit
- https://tes5edit.github.io/docs/2-overview.html
- https://tes5edit.github.io/docs/13-Scripting-Functions.html
- https://github.com/sheson/xLODGen
- https://dyndolod.info/Help/xLODGen
- https://dyndolod.info/DynDOLOD-Reference
