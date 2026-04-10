import unittest

from npcjason_app.persistence import sanitize_settings_payload, sanitize_shared_state_payload


class PersistenceTests(unittest.TestCase):
    def test_sanitize_settings_payload_repairs_invalid_shapes(self):
        payload = {
            "global": {
                "sound_enabled": "yes",
                "sound_volume": "loud",
                "sound_categories": {"toy": "no", "state": "yes"},
                "quiet_start_hour": 99,
                "rare_events_enabled": "no",
                "chaos_mode": "yes",
                "movement_enabled": "off",
                "companion_enabled": "false",
                "selected_companion": " mouse ",
                "unlocks_enabled": "on",
                "seasonal_mode_override": " monday-morning-survival ",
                "reactions": {"usb": "false", "updates": "true"},
                "disabled_quote_packs": [" jason-quotes ", "", "jason-quotes"],
                "favorite_skins": [" office ", "", "office", "astronaut"],
                "favorite_toys": ["tricycle", "rubber-duck", "tricycle"],
                "favorite_scenarios": ["office-chaos", None],
                "favorite_quote_packs": ["what-do", " jason-quotes "],
                "unlocked_scenarios": ["network-victory-lap", "", "network-victory-lap"],
                "discovery_stats": {"launches": "4", "runtime_minutes": "-5", "discoveries": "2"},
                "recent_scenarios": ["busy-it-morning", " office-chaos ", ""],
                "favorite_sayings": [" keep ", "", None],
                "recent_sayings": ["line", {"text": "two", "timestamp": "3"}],
            },
            "instances": {
                "main": {
                    "x": "12",
                    "y": None,
                    "mood": "mystery",
                    "name": "  Jason  ",
                    "personality_state": " smug ",
                    "last_scenario": " office-chaos ",
                },
                "bad": "oops",
            },
        }

        sanitized, warnings = sanitize_settings_payload(payload)

        self.assertTrue(sanitized["global"]["sound_enabled"])
        self.assertEqual(70, sanitized["global"]["sound_volume"])
        self.assertFalse(sanitized["global"]["sound_categories"]["toy"])
        self.assertTrue(sanitized["global"]["sound_categories"]["state"])
        self.assertEqual(23, sanitized["global"]["quiet_start_hour"])
        self.assertFalse(sanitized["global"]["rare_events_enabled"])
        self.assertTrue(sanitized["global"]["chaos_mode"])
        self.assertFalse(sanitized["global"]["movement_enabled"])
        self.assertFalse(sanitized["global"]["companion_enabled"])
        self.assertEqual("mouse", sanitized["global"]["selected_companion"])
        self.assertTrue(sanitized["global"]["unlocks_enabled"])
        self.assertEqual("monday-morning-survival", sanitized["global"]["seasonal_mode_override"])
        self.assertFalse(sanitized["global"]["reactions"]["usb"])
        self.assertTrue(sanitized["global"]["reactions"]["updates"])
        self.assertEqual({"jason-quotes": False}, sanitized["global"]["quote_pack_states"])
        self.assertEqual(["office", "astronaut"], sanitized["global"]["favorite_skins"])
        self.assertEqual(["tricycle", "rubber-duck"], sanitized["global"]["favorite_toys"])
        self.assertEqual(["office-chaos"], sanitized["global"]["favorite_scenarios"])
        self.assertEqual(["what-do", "jason-quotes"], sanitized["global"]["favorite_quote_packs"])
        self.assertEqual(["network-victory-lap"], sanitized["global"]["unlocked_scenarios"])
        self.assertEqual(4, sanitized["global"]["discovery_stats"]["launches"])
        self.assertEqual(0, sanitized["global"]["discovery_stats"]["runtime_minutes"])
        self.assertEqual(["busy-it-morning", "office-chaos"], sanitized["global"]["recent_scenarios"])
        self.assertEqual(["keep"], sanitized["global"]["favorite_sayings"])
        self.assertEqual(2, len(sanitized["global"]["recent_sayings"]))
        self.assertEqual("happy", sanitized["instances"]["main"]["mood"])
        self.assertEqual("smug", sanitized["instances"]["main"]["personality_state"])
        self.assertEqual("office-chaos", sanitized["instances"]["main"]["last_scenario"])
        self.assertNotIn("bad", sanitized["instances"])
        self.assertTrue(warnings)

    def test_sanitize_shared_state_payload_discards_invalid_entries(self):
        payload = {
            "instances": {"main": {"x": "1", "y": "2", "updated_at": "4", "name": "Desk"}},
            "conversations": [{"id": "a", "participants": ["main"], "lines": {"main": "hi"}, "created_at": "3"}],
            "commands": [
                {"id": "cmd", "target": "main", "action": "quit", "created_at": "5"},
                {"id": "", "target": "main", "action": "quit"},
            ],
        }

        sanitized, warnings = sanitize_shared_state_payload(payload)

        self.assertEqual(1, len(sanitized["instances"]))
        self.assertEqual(1, len(sanitized["conversations"]))
        self.assertEqual(1, len(sanitized["commands"]))
        self.assertEqual([], warnings)

    def test_sanitize_payloads_warn_on_schema_mismatch(self):
        settings, settings_warnings = sanitize_settings_payload({"schema_version": 1})
        shared_state, shared_warnings = sanitize_shared_state_payload({"schema_version": 99})

        self.assertEqual(7, settings["schema_version"])
        self.assertEqual(1, shared_state["schema_version"])
        self.assertTrue(any("schema upgraded" in warning for warning in settings_warnings))
        self.assertTrue(any("newer than supported" in warning for warning in shared_warnings))


if __name__ == "__main__":
    unittest.main()
