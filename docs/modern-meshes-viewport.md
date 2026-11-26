# Modern meshes and world viewport
## Native NIF bridge
The optional C++ helper uses nifly pinned at 47993ec6540a09453f6d53fded6c1eec91dcf3eb. Its source is GPL-3.0-only and the independent Python client remains MIT. See native/nifbridge/README.md for the build. No compiled helper is bundled in normal previews. CI builds from the pinned public source and exercises all seven supported game profiles.
    python -m chimster modern-nif newvegas tree.obj tree.nif /path/to/chimster-nifbridge --materials materials.json --scale 1
Example materials.json: {"bark__opaque":{"diffuse":"textures/chimster/bark.dds","normal":"textures/chimster/bark_n.dds"},"leaves__cutout":{"diffuse":"textures/chimster/leaves.dds","cutout":true}}
Input is triangulated OBJ with positive indices; material IDs must be ASCII identifiers. Each shape is limited to 65,535 vertices and triangles. The exporter assigns normals, tangents, default shaders and supplied texture paths, then reopens and verifies versions, triangle counts and texture references. Native format verification is not game compatibility certification. Game scale must be selected by author; collision, material variants, wind, skinning, native LOD tiles and Starfield are not supported. Fallout 4 BGSM assignments require further testing.
## Integrated 3D viewport
Open the 3D viewport tab in Chimster. The generated demo contains terrain and trees. Orbit with right mouse drag; zoom with wheel; Fit centers the scene. Click an object or select it in the object list; edit XYZ, yaw and scale, then Apply transform. Add tree, delete, undo and redo operate on the portable scene, not game records. Import triangulated OBJ; no external MTL execution. Save a new JSON scene and reopen it. Existing files are not overwritten.
    python -m chimster scene-demo example-scene.json
This is a CPU painter-sorted shaded triangle preview, not OpenMW rendering or a full z-buffered textured GPU engine. Triangle stride reduction keeps display complexity bounded but can create holes for large scenes. The object transforms and scene files are independent of rendering so a GPU backend can be substituted later. No game collision, real-time game asset loading, terrain sculpting or engine export is implemented in the viewport.
## Next acceptance tests
- Compile native helper and pass generated meshes for every target.
- Independent NifSkope/xEdit/game smoke tests on authorized installations; validate material and collision.
- Add spatial chunks, indexed GPU meshes, true depth, texture sampling and picking.
- Map portable instances to stable plugin records and per-game worldspace coordinates.
- Use OpenMW's public template to test real game rendering; evaluate separate GPL renderer integration.

## Native vegetation package
    python -m chimster native-flora newvegas flora-output /path/to/chimster-nifbridge --seed 42
Builds four native NIF candidates, original bark/leaf DDS textures, normal maps, a two-view billboard atlas and manifest in standard meshes/textures folders. Leaf faces are duplicated with opposite normals for two-sided geometry. This does not generate SPT or native worldspace LOD records/tiles. The atlas uses flat-color baking, not sampled leaf textures; foliage texture mipmaps/coverage and engine validation are pending. No retail assets included.
