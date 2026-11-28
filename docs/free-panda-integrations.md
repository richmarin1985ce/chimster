# Free Panda rendering integrations

Pinned optional dependencies: panda3d-simplepbr 0.13.1 (BSD-3-Clause), panda3d-gltf 1.3.0 (BSD-3-Clause). Panda3D 1.10.16 already includes CommonFilters (Panda BSD). No paid services, keys, or proprietary add-on purchases. Distribution must preserve upstream license notices; wheel metadata is included in installer collection.

Panda3D PBR and Panda3D Filters are selectable desktop preview modes. The PBR adapter supplies an explicit camera, graphics output, scene root and manually stepped task rather than constructing a second ShowBase. CommonFilters enables upstream SSAO when the preset requests it. Cg availability varies by platform; errors fall back to native rendering. Only one filter graph may own an output. Water deliberately uses the native path pending combined tests. No PBR material parity claim for existing NIF/OBJ tangents; glTF package is installed and collected; the sidebar can preview self-contained GLB assets using the upstream loader. Preview is transient and is not saved into the portable scene or native plugin. External and data URI resources are rejected.

RenderPipeline is MIT-licensed at its root but has third-party resources and a larger OpenGL 4.3 pipeline/setup footprint; not bundled. PSSMCameraRig is existing Panda native camera infrastructure, not a complete shader implementation. Neither is activated in this pass. CC0 sample code is a reference; no sample assets copied. ComplexPBR excluded due to nonstandard license terms.

Sources: https://github.com/Moguri/panda3d-simplepbr ; https://github.com/Moguri/panda3d-gltf ; https://docs.panda3d.org/1.10/python/reference/direct.filter.CommonFilters ; https://github.com/tobspr/RenderPipeline .
