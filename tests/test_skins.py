import unittest

from npcjason_app.skins import (
    EMPTY_OVERLAY,
    build_skin_assets,
    default_skin_definition,
    validate_skin_definition,
)


class SkinTests(unittest.TestCase):
    def test_default_skin_definition_has_full_overlay(self):
        definition = default_skin_definition()
        self.assertEqual(20, len(definition["overlay"]))
        self.assertTrue(all(len(row) == 16 for row in definition["overlay"]))
        self.assertIn("tags", definition)
        self.assertIn("animations", definition)
        self.assertEqual("default", definition["capabilities"]["idle_animation"])

    def test_build_skin_assets_applies_char_map(self):
        definition = default_skin_definition()
        definition["char_map"] = {"T": "Z"}
        definition["palette"] = {"Z": "#123456"}
        definition["overlay"] = EMPTY_OVERLAY

        assets = build_skin_assets(definition)

        body_rows = "\n".join(assets["frames"]["idle_open"])
        self.assertIn("Z", body_rows)
        self.assertEqual("#123456", assets["palette"]["Z"])
        self.assertTrue(assets["idle_sequence"])
        self.assertIn("quote_affinity", assets)

    def test_validate_skin_definition_adds_defaults_and_reports_invalid_tray(self):
        normalized, errors = validate_skin_definition(
            {"key": " ranger ", "tray": "invalid"},
            "ranger.json",
        )

        self.assertEqual("ranger", normalized["key"])
        self.assertEqual("NPCJason", normalized["author"])
        self.assertEqual("The default blue-shirt desktop gremlin.", normalized["description"])
        self.assertEqual("2.0", normalized["version"])
        self.assertTrue(any("'tray' must be an object" in error for error in errors))

    def test_validate_skin_definition_rejects_invalid_colors(self):
        normalized, errors = validate_skin_definition(
            {
                "key": "mage",
                "palette": {"T": "blue"},
                "tray": {"hair": "#123456", "body": "bad", "legs": "#654321"},
            },
            "mage.json",
        )

        self.assertNotIn("T", normalized["palette"])
        self.assertEqual("#3a86c8", normalized["tray"]["body"])
        self.assertTrue(any("invalid palette color" in error for error in errors))
        self.assertTrue(any("invalid tray color" in error for error in errors))

    def test_validate_skin_definition_supports_custom_sequences_and_frame_overlays(self):
        normalized, errors = validate_skin_definition(
            {
                "key": "operator",
                "tags": ["network", "focus"],
                "frame_overlays": {"dance1": ["A" * 16] * 20},
                "animations": {
                    "idle": [{"frame": "idle_open", "offset_y": 0, "delay_ms": 300}],
                    "interaction": [{"frame": "dance1", "offset_y": 1, "delay_ms": 140}],
                },
            },
            "operator.json",
        )

        self.assertEqual(["network", "focus"], normalized["tags"])
        self.assertEqual("custom", normalized["capabilities"]["interaction_animation"])
        self.assertEqual(300, normalized["animations"]["idle"][0]["delay_ms"])
        self.assertFalse(errors)


if __name__ == "__main__":
    unittest.main()
