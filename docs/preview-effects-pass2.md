# Advanced preview effects, second pass

- Panda: experimental planar scene reflection and refraction buffers (Medium/High, water enabled); reflected camera and opposing clip planes; analytic sky fallback for unavailable buffers, underwater views or camera-specific room culling. Refraction is tinted, not optical depth or shoreline foam.
- Panda: spotlight cones, one optional local shadow map, editable preview light position and water elevation. Directional shadow anchor snaps to light-space texels (single map, not cascaded).
- ModernGL: reconstruct view-space normals and reject distant AO samples. Analytic homogeneous single scattering uses a Henyey-Greenstein phase term with distance extinction. No shadowed volumetric raymarch, local fog volumes or temporal denoising.
- Off remains default. No native records written. GPU regression covers shader compilation, resize, image change and unchanged object picking if EGL is available. Panda reflection/refraction shader and render targets still need runtime verification.
