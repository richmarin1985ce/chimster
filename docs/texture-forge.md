# Texture Forge
Native deterministic generators from explicit author-supplied inputs:
- Height-to-normal map, DirectX/OpenGL green channel, tile wrapping or clamped edges, strength control.
- Specular mask remapping with configurable low/high reflectivity, gamma and inversion at the library level. Not inferred physical material properties.
- Optional specular packing into normal-map alpha for target shaders that use it. Do not assume universal Bethesda channel conventions; preserve a separate map.
- Equirectangular 2:1 LDR panorama to six oriented cube faces and a legacy uncompressed DDS cubemap. Face order +X,-X,+Y,-Y,+Z,-Z, with DDS complex and cube face flags.
- PNG and uncompressed DDS output with complete material-map mip chains (normal vectors renormalized); cube DDS remains single-level. Optional Pillow for input image decoding; no dependency for pure byte-buffer transforms.
- Native generators do not yet produce BC-compressed DDS, alpha-coverage-preserving mipmaps, roughness-prefiltered/HDR cube maps, worldspace reflection probes, or automatically assign texture slots in NIF materials.
- Texconv integration is a separately installed tool bridge; validate actual compressed assets before game use.
CLI:
    python -m pip install Pillow
    python -m chimster textures material height.png specular-mask.png material-out --strength 4 --wrap
    python -m chimster textures material height.png specular-mask.png material-out --pack-alpha
    python -m chimster textures cube panorama.png cube-out --size 128
References: https://learn.microsoft.com/en-us/windows/win32/direct3ddds/dds-file-layout-for-cubic-environment-maps
