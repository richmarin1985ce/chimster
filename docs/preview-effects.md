# Preview effects, initial integration

Panda3D: optional directional shadow map, ambient intensity, up to four bounded point lights, exponential distance fog and an animated translucent water card with wave normals, Fresnel and analytic sky/sun reflection. Water is a preview overlay, never a native record. Fog is homogeneous approximation, not volumetric shafts. No planar or screen-space scene reflection yet.

ModernGL: optional 16-tap depth-neighborhood screen-space occlusion, applied to the color target only. Picking is preserved. This is a first-pass depth-only approximation; normal-aware sampling, denoising and temporal stability remain. No shadow or water parity in ModernGL yet. Panda has no AO pass yet.

Desktop offers Off/Low/Medium/High presets, point light and preview water toggles. Off is default. Water preview refreshes at roughly 6.7 Hz while enabled. Native lighting metadata, shadow cascades, performance profiling, framebuffer validation and per-game water materials are follow-ups.
