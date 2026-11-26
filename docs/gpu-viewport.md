# OpenGL viewport
Original MIT viewport code, using optional ModernGL (MIT) and glcontext (MIT) packages. No OpenMW or game code reused. Install from source with python -m pip install ".[viewport]". The desktop 3D viewport has an opt-in OpenGL preview checkbox. CPU preview remains available if context initialization or rendering fails; error and renderer name are shown. The normal preview build does not bundle ModernGL yet. Requires an OpenGL 3.3 driver; Windows/macOS hardware context creation is not independently tested.

## Architecture
- Perspective orbit camera, near/far clipping, true depth renderbuffer, per-object bounding sphere frustum rejection before mesh upload.
- Per-mesh vertex buffers and per-material index buffers cached across edits; transforms are uniforms. Stale resources released when assets or material maps are replaced.
- Directional lighting, ambient term, diffuse/normal/specular textures, derivative tangent frame, DirectX or OpenGL normal green channel, adjustable normal strength and gloss, alpha-cutout support.
- GPU object-ID attachment shares the depth and alpha test of the color pass. Mouse picks the visible surface, not approximate screen bounds.
- LOD 0 uses the base asset; optional variants named base@lod1, base@lod2, base@lod3 are selected by camera distance in scene units. Missing tiers fall back toward higher detail. Three increasing thresholds can be changed in the desktop interface. Demo includes actual generated tree variants and atlas billboards.
- CPU fallback uses the prior approximate painter preview; it does not perform shader lighting or GPU LOD. OpenGL readback is copied to Tk via Pillow at a capped 1280x720 render resolution. This is not zero-copy native GL window embedding.

## Commands
    python -m chimster render-preview preview.png --backend egl --width 960 --height 540
    python -m chimster render-preview preview.png --scene scene.json --materials materials.json --lod 20 40 80

Render output is PNG and CLI JSON reports visible/culled objects, triangles, draw calls, LOD counts, elapsed frame milliseconds including readback and GL renderer. CI uses Mesa software rendering, not a physical GPU benchmark.

## Material manifest
JSON mapping from mesh material name to properties, e.g. {"bark__opaque":{"diffuse":"bark.dds","normal":"bark_n.dds","specular":"bark_s.dds","directx":true,"normal_strength":1.0,"spec_strength":0.18,"gloss":24},"leaves__cutout":{"diffuse":"leaves.dds","cutout":0.5}}. Paths must be relative and contained within the manifest folder. Load explicitly from the viewport or CLI. Material data is not embedded in scene JSON; reload the manifest after reopening a custom scene. No game shader or BGSM parsing. Preview colors are approximate.

## Next
Native desktop GL surface, batched/instanced draws, hierarchical world chunks, texture mip/anisotropic filtering, GPU timing, occlusion culling, terrain tile stitching, cubemap capture, shadows, and actual game-specific record synchronization. Do not claim Creation Kit parity or hardware speedups from Mesa tests.
