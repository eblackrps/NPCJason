import unittest

from npcjason_app.toys import TOY_DEFINITIONS, ToyManager


class ToyDefinitionTests(unittest.TestCase):
    def test_expected_toys_exist(self):
        self.assertIn("tricycle", TOY_DEFINITIONS)
        self.assertIn("rubber-duck", TOY_DEFINITIONS)
        self.assertIn("homelab-cart", TOY_DEFINITIONS)
        self.assertIn("stress-ball", TOY_DEFINITIONS)

    def test_available_toys_expose_metadata_without_active_root(self):
        manager = ToyManager(root=None, clock=lambda: 1.0)
        toys = {toy["key"]: toy for toy in manager.available_toys()}

        self.assertEqual("Tricycle Ride", toys["tricycle"]["label"])
        self.assertIn("homelab", toys["homelab-cart"]["tags"])
        self.assertEqual(0, toys["stress-ball"]["cooldown_ms"])


if __name__ == "__main__":
    unittest.main()
