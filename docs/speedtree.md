# Legacy SpeedTree compatibility

Chimster's original internal SPT reader targets the documented legacy token stream used by Oblivion, Fallout 3 and New Vegas. It is not the proprietary SpeedTree runtime. Unknown token layouts terminate parsing at the exact byte offset. Editing is restricted to uniquely identified seed, size, size variance and near/far LOD distance fields in completely walked streams; original files are never overwritten.

## CLI

- `python -m chimster lod spt-inspect Tree.spt`
- `python -m chimster lod spt-edit Tree.spt '{"seed":42}' Edited.spt`
- `python -m chimster lod spt-billboard new-vegas Trees/Oak.spt output --width 128 --height 256 --data /path/to/Data`

The classic world object LOD builder reads TREE BNAM dimensions, resolves the original whole-tree DDS from the selected loose files or BSA archives, and generates cutout crossed cards. It preserves the original DDS and generates a neutral normal map. Leaf textures are not whole-tree billboards and are not substituted. Separate TREE records with the same SPT can retain different billboard dimensions. The standalone conversion creates a static native NIF candidate, not a new SPT.

Format facts: https://github.com/anahuj/spttools/blob/master/FORMAT ; TREE subrecords: https://github.com/TES5Edit/TES5Edit ; billboard naming: https://cs.uesp.net/wiki/SpeedTree/Paintshop_Pro:_Billboards_for_Oblivion_SpeedTree_trees

Outstanding: complete variant coverage against legally acquired real assets, procedural branch/frond/leaf reconstruction, native wind/collision behavior, missing billboard generation and game-specific native tree LOD layouts. No SpeedTree SDK, DLL, external application, or third-party parser implementation is bundled. Regression fixtures are synthetic; native runtime compatibility is unverified.
