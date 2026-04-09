import json
from pathlib import Path
import tempfile
import unittest

from npcjason_app.data.defaults import default_settings
from npcjason_app.settings_service import GlobalSettings, InstanceSettings, SettingsService
from npcjason_app.store import JsonStore


class StartupStub:
    def __init__(self, enabled=False):
        self.enabled = enabled

    def is_enabled(self):
        return self.enabled


class SettingsServiceTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.settings_path = Path(self.temp_dir.name) / "settings.json"
        self.store = JsonStore(self.settings_path, default_settings)
        self.startup = StartupStub(enabled=True)
        self.service = SettingsService(self.store, self.startup)

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_save_and_load_round_trip(self):
        global_settings = GlobalSettings(
            sound_enabled=False,
            sound_volume=12,
            auto_update_enabled=False,
            event_reactions_enabled=False,
            quiet_hours_enabled=True,
            quiet_start_hour=21,
            quiet_end_hour=7,
            quiet_when_fullscreen=True,
            auto_antics_enabled=False,
            auto_antics_min_minutes=5,
            auto_antics_max_minutes=8,
            auto_antics_dance_chance=35,
            rare_events_enabled=False,
            chaos_mode=True,
            reaction_toggles={"usb": False, "updates": False},
            quote_pack_states={"jason-quotes": False},
            favorite_templates=["One", "Two"],
            recent_sayings=[{"template": "One", "text": "Rendered one", "source": "test", "timestamp": 1.0}],
        )
        instance_settings = InstanceSettings(x=25, y=35, skin="wizard", mood="tired", name="Desk Jason")

        self.service.save("main", global_settings, instance_settings)
        loaded = self.service.load("main")

        self.assertFalse(loaded.global_settings.sound_enabled)
        self.assertEqual(12, loaded.global_settings.sound_volume)
        self.assertFalse(loaded.global_settings.auto_update_enabled)
        self.assertFalse(loaded.global_settings.reaction_toggles["usb"])
        self.assertFalse(loaded.global_settings.rare_events_enabled)
        self.assertTrue(loaded.global_settings.chaos_mode)
        self.assertEqual({"jason-quotes": False}, loaded.global_settings.quote_pack_states)
        self.assertEqual("wizard", loaded.instance_settings.skin)
        self.assertEqual("Desk Jason", loaded.instance_settings.name)

    def test_import_validation_rejects_invalid_shapes(self):
        broken_path = Path(self.temp_dir.name) / "broken.json"
        broken_path.write_text('{"global": []}', encoding="utf-8")

        with self.assertRaises(ValueError):
            self.service.import_from_file(broken_path)

    def test_reset_restores_default_shape(self):
        self.service.reset()
        loaded = self.service.load("main")

        self.assertTrue(loaded.global_settings.sound_enabled)
        self.assertEqual("jason", loaded.instance_settings.skin)

    def test_load_repairs_invalid_saved_payload(self):
        self.store.write({"global": {"sound_volume": "loud"}, "instances": {"main": {"mood": "???", "name": "Desk"}}})

        loaded = self.service.load("main")

        self.assertEqual(70, loaded.global_settings.sound_volume)
        self.assertEqual("happy", loaded.instance_settings.mood)

    def test_export_writes_sanitized_payload(self):
        export_path = Path(self.temp_dir.name) / "export.json"
        self.store.write({"schema_version": 0, "global": {"sound_volume": "loud"}, "instances": []})

        self.service.export_to_file(export_path)
        exported = json.loads(export_path.read_text(encoding="utf-8"))

        self.assertEqual(4, exported["schema_version"])
        self.assertEqual(70, exported["global"]["sound_volume"])
        self.assertEqual({}, exported["instances"])


if __name__ == "__main__":
    unittest.main()
