import unittest
from chimster.render_effects import Effects,LocalLight,preset

class EffectsTests(unittest.TestCase):
    def test_presets(self):
        self.assertEqual(preset("Off").shadow_size,0)
        self.assertEqual(preset("High").validate().shadow_size,1024)
        self.assertGreater(preset("High").ao_strength,preset("Low").ao_strength)
    def test_limits(self):
        for fx in (Effects(shadow_size=4096),Effects(ao_radius=0),Effects(lights=(LocalLight(),)*5),Effects(water_level=float("nan")),Effects(fog_density=-1)):
            with self.assertRaises(ValueError):fx.validate()
        with self.assertRaises(ValueError):LocalLight(radius=0).validate()

    def test_reflection_math(self):
        from chimster.panda_reflection import mirror_point,mirror_vector
        self.assertEqual(mirror_point((2,3,8),2),(2,3,-4))
        self.assertEqual(mirror_vector((0,1,2)),(0,1,-2))
        with self.assertRaises(ValueError):Effects(refraction=True).validate()

    def test_shadow_snap(self):
        from chimster.shadow_math import snap_center
        p=snap_center((.01,.01,2),(0,0,1),16,512)
        for a,b in zip(p,(0,0,2)):self.assertAlmostEqual(a,b)
        self.assertEqual(snap_center((1,2,3),(0,0,1),16,0),(1,2,3))
    def test_spot_limits(self):
        with self.assertRaises(ValueError):LocalLight(direction=(0,0,0)).validate()
        with self.assertRaises(ValueError):LocalLight(shadows=True).validate()
        self.assertEqual(LocalLight(direction=(0,0,-1),shadows=True).validate().cone,45)

    def test_nested_shadow_frames(self):
        from chimster.gpu_shadows import frames
        from chimster.shadow_math import dot
        r,u,n,views=frames((0,0,0),(1,2,3),48,512,2)
        self.assertAlmostEqual(dot(r,u),0)
        self.assertAlmostEqual(dot(u,n),0)
        self.assertAlmostEqual(views[0][1],16.8)
        self.assertEqual(views[1][1],48)
        with self.assertRaises(ValueError):Effects(shadow_cascades=3).validate()
