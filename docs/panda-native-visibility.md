# Native visibility and Panda3D

Panda3D is the preferred viewport; retain CPU/ModernGL fallback. Use engine-native culling where possible instead of duplicating per-frame Python work. Preserve native records independently from preview representation.

## References
- https://geckwiki.com/index.php/Room_Bounds_and_Portal_Basics
- https://geckwiki.com/index.php/Occlusion_Culling (Fallout 3 development document; retail debug functionality may be absent)
- https://geckwiki.com/index.php/Editing_MultiBounds
- https://ck.uesp.net/wiki/Bethesda_Tutorial_Optimization (Skyrim source access returned 403; review pending)
- https://docs.panda3d.org/1.10/python/programming/render-attributes/occlusion-culling/portal-culling
- https://docs.panda3d.org/1.10/python/programming/render-attributes/occlusion-culling/polygon-occluder-culling
- https://docs.panda3d.org/1.10/python/programming/scene-graph/level-of-detail

## Architecture
Map native room membership to scene nodes, paired directed portals to Panda portal nodes, occlusion quads to OccluderNode, exterior groups to hierarchical bounding volumes. Keep unassigned references visible conservatively and support outside-room views. Validate portal winding, links, world transforms, pivot membership and bounds overlap. Existing axis-aligned portable layouts are insufficient for arbitrary rotated native volumes. Do not infer identical formats across games. Preview modes: unculled, room/portal, occlusion, combined, debug overlays. Never write native records from preview state. Retain portal_clip.py as a reference and budgeted fallback. Panda3D portal behavior, mask semantics and runtime performance require independent tests. Prefer LODNode and measured geometry instancing for forests and rock clusters; avoid flattening across culling boundaries. Native LOD serialization remains separate. Prioritize integration over new procedural generators.
