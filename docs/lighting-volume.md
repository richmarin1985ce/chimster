# Lighting and volumetric rendering pass

ModernGL: colored sun and four point/spot lights, bounded attenuation, two nested orthographic directional depth maps, 3x3 PCF, alpha-cutout casters, texel snapping and coverage blend. The maps are camera-target-centered nested regions rather than frustum-split cascades. Shadowed world-space volumetric ray integration samples these maps, includes local light scattering, height fog and up to four smooth spherical fog volumes. Step counts and distance are bounded; the default remains off. Object picking is not post-processed.

Panda remains on its native single directional and optional spotlight shadow maps; shared sun color is supported. ModernGL local lights do not cast shadows yet. Panda volumetric integration is not implemented. No native game light-record writeback or production validation. EGL regression workflow now runs on matching pushes; benchmark and real GPU validation remain separate.
