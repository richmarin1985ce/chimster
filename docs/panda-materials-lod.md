# Panda viewport: materials and LOD

The optional Panda3D scene adapter accepts the existing viewport Material dictionary and Settings object. Diffuse RGBA maps, tint and alpha-cutout state are mapped to the Panda scene graph; normal/specular maps, picking and shadow rendering are not implemented here. Texture rows match the ModernGL convention. Missing LOD tiers retain the closest available finer mesh. LOD distances use unscaled instance anchors, with shared geometry templates and Panda LODNodes. These are scene-graph instances, not measured GPU hardware instancing.

Preview.render(scene, camera, w, h, materials=None, settings=None) remains backward compatible. Callers must pass material maps explicitly. Existing CPU/ModernGL fallbacks are unchanged. Scene graph tests run separately from Foundation tests; physical GPU performance and framebuffer output remain to be verified.
