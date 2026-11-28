# Legacy SpeedTree compatibility

Chimster's original internal SPT reader targets the documented legacy token stream used by Oblivion, Fallout 3 and New Vegas. It is not the proprietary SpeedTree runtime. Unknown token layouts terminate parsing at the exact byte offset. Editing is restricted to uniquely identified seed, size, size variance and near/far LOD distance fields in completely walked streams; original files are never overwritten.

## Native round-trip projects

Use `lod spt-import Tree.spt project-folder`, edit `edits.json`, then use `lod spt-export project-folder NewTree.spt`. The project preserves the immutable original SPT and validates its SHA-256 before export. With no edits, export is byte-identical, even for an opaque variant with a recognizable header. Unsupported variants cannot be edited. The manifest lists stable texture indices (including empty texture slots). Example edits:

```json
{"scalars":{"seed":42,"size":200},"textures":{"0":"Trees/Bark.dds"}}
```

The exporter verifies unchanged token bytes after variable-length texture relinks. It does not synthesize missing procedural blocks, copy referenced texture files, or guarantee game acceptance. Use an existing compatible source as a template for variants. The Worldspace Browser includes SPT import/export controls. Flora Forge remains an independent original authoring system.

## CLI

- `python -m chimster lod spt-inspect Tree.spt`
- `python -m chimster lod spt-edit Tree.spt '{"seed":42}' Edited.spt`
- `python -m chimster lod spt-billboard new-vegas Trees/Oak.spt output --width 128 --height 256 --data /path/to/Data`

The classic world object LOD builder reads TREE BNAM dimensions, resolves the original whole-tree DDS from the selected loose files or BSA archives, and generates cutout crossed cards. It preserves the original DDS and generates a neutral normal map. Leaf textures are not whole-tree billboards and are not substituted. Separate TREE records with the same SPT can retain different billboard dimensions. The standalone conversion creates a static native NIF candidate, not a new SPT.

Format facts: https://github.com/anahuj/spttools/blob/master/FORMAT ; TREE subrecords: https://github.com/TES5Edit/TES5Edit ; billboard naming: https://cs.uesp.net/wiki/SpeedTree/Paintshop_Pro:_Billboards_for_Oblivion_SpeedTree_trees

Outstanding: real-asset and game-runtime validation, broader legacy SPT version coverage, native authoring beyond source-template edits, and other SpeedTree container families. Exact proprietary procedural reproduction is not a project goal. No SpeedTree SDK, DLL, external application, or third-party parser implementation is bundled. Regression fixtures are synthetic; native runtime compatibility is unverified.
