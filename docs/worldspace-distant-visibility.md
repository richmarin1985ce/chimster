# Worldspace distant visibility
TVDT exterior CELL occlusion tracks 4/8/16/32-cell LOD tile visibility, not elevation extrema. Regenerate after terrain changes; a changed occluder may invalidate source cells far beyond its own tile. Dirty tile planning is not sufficient for TVDT invalidation. Use whole-world regeneration until a proven dependency model exists. Preserve original bytes until native encoding and independent verification. Standard coverage approximately 256x256 cells. Investigate MHDT and game-specific terrain min/max fields separately from WRLD NAM0/NAM9 horizontal bounds and DNAM default elevations.
 
Skyrim cloud feature: distinguish world-map cloud bank mesh from in-world persistent full-LOD cloud references. Support original/custom NIF import, shader/alpha validation, placement, map coverage and recentering. Never redistribute stock assets. Skyrim neverfade references use Persistent and Is Full LOD; ordinary baked object LOD and dynamic enable-parent controlled LOD are separate. Do not promise unlimited draw distance. Fallout 4 Prydwen-style landmark: inspect actual native record and asset configuration before choosing flags; support quest enable state, distant proxy, near mesh handoff without duplication. Fallout 4 cloud support unverified. Preview with Panda3D LOD nodes and explicit distance ranges; native exports require game-specific verification.
 
References: https://dyndolod.info/Help/Occlusion-Data
https://dyndolod.info/How-LOD-Works
https://dyndolod.info/Help/Mesh-Mask-Reference-Rules
https://dyndolod.info/Messages/Worldspace-Bounds
https://tes5edit.github.io/fopdoc/FalloutNV/Records/WRLD.html
