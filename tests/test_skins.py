import unittest

from npcjason_app.skins import EMPTY_OVERLAY, build_skin_assets, default_skin_definition


class SkinTests(unittest.TestCase):
    def test_default_skin_definition_has_full_overlay(self):
        definition = default_skin_definition()
        self.assertEqual(20, len(definition["overlay"]))
        self.assertTrue(all(len(row) == 16 for row in definition["overlay"]))

    def test_build_skin_assets_applies_char_map(self):
        definition = default_skin_definition()
        definition["char_map"] = {"T": "Z"}
        definition["palette"] = {"Z": "#123456"}
        definition["overlay"] = EMPTY_OVERLAY

        assets = build_skin_assets(definition)

        body_rows = "\n".join(assets["frames"]["idle_open"])
        self.assertIn("Z", body_rows)
        self.assertEqual("#123456", assets["palette"]["Z"])


if __name__ == "__main__":
    unittest.main()
