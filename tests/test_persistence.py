import unittest

from npcjason_app.persistence import sanitize_settings_payload, sanitize_shared_state_payload


class PersistenceTests(unittest.TestCase):
    def test_sanitize_settings_payload_repairs_invalid_shapes(self):
        payload = {
            "global": {
                "sound_enabled": "yes",
                "sound_volume": "loud",
                "quiet_start_hour": 99,
                "reactions": {"usb": "false", "updates": "true"},
                "favorite_sayings": [" keep ", "", None],
                "recent_sayings": ["line", {"text": "two", "timestamp": "3"}],
            },
            "instances": {
                "main": {"x": "12", "y": None, "mood": "mystery", "name": "  Jason  "},
                "bad": "oops",
            },
        }

        sanitized, warnings = sanitize_settings_payload(payload)

        self.assertTrue(sanitized["global"]["sound_enabled"])
        self.assertEqual(70, sanitized["global"]["sound_volume"])
        self.assertEqual(23, sanitized["global"]["quiet_start_hour"])
        self.assertFalse(sanitized["global"]["reactions"]["usb"])
        self.assertTrue(sanitized["global"]["reactions"]["updates"])
        self.assertEqual(["keep"], sanitized["global"]["favorite_sayings"])
        self.assertEqual(2, len(sanitized["global"]["recent_sayings"]))
        self.assertEqual("happy", sanitized["instances"]["main"]["mood"])
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

        self.assertEqual(2, settings["schema_version"])
        self.assertEqual(1, shared_state["schema_version"])
        self.assertTrue(any("schema upgraded" in warning for warning in settings_warnings))
        self.assertTrue(any("newer than supported" in warning for warning in shared_warnings))


if __name__ == "__main__":
    unittest.main()
