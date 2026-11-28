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
