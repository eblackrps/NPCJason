import json
from pathlib import Path
import unittest

from npcjason_app.data.defaults import default_settings
from npcjason_app.settings_service import GlobalSettings, InstanceSettings, SettingsService
from npcjason_app.store import JsonStore
from tests.helpers import workspace_tempdir


class StartupStub:
    def __init__(self, enabled=False):
        self.enabled = enabled

    def is_enabled(self):
        return self.enabled


class SettingsServiceTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = workspace_tempdir()
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
            sound_categories={"speech": True, "toy": False, "state": True, "scenario": False},
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
            movement_enabled=False,
            companion_enabled=False,
            selected_companion="mouse",
            activity_level="high",
            quote_frequency="chatty",
            companion_frequency="low",
            unlocks_enabled=False,
            seasonal_mode_override="office-chaos",
            last_active_season="monday-morning-survival",
            reaction_toggles={"usb": False, "updates": False},
            quote_pack_states={"jason-quotes": False},
            favorite_skins=["office"],
            favorite_toys=["tricycle"],
            favorite_scenarios=["office-chaos"],
            favorite_quote_packs=["what-do"],
            unlocked_skins=["astronaut"],
            unlocked_toys=["stress-ball"],
            unlocked_scenarios=["office-chaos"],
            unlocked_quote_packs=["what-do"],
            discovery_stats={"launches": 3, "discoveries": 1},
            recent_scenarios=["office-chaos"],
            favorite_templates=["One", "Two"],
            recent_sayings=[{"template": "One", "text": "Rendered one", "source": "test", "timestamp": 1.0}],
            companion_presence={"familiarity": 14, "days_used": 4, "today_mode_key": "patch-goblin"},
        )
        instance_settings = InstanceSettings(
            x=25,
            y=35,
            skin="wizard",
            mood="tired",
            name="Desk Jason",
            personality_state="busy",
            last_scenario="office-chaos",
        )

        self.service.save("main", global_settings, instance_settings)
        loaded = self.service.load("main")

        self.assertFalse(loaded.global_settings.sound_enabled)
        self.assertEqual(12, loaded.global_settings.sound_volume)
        self.assertFalse(loaded.global_settings.auto_update_enabled)
        self.assertFalse(loaded.global_settings.sound_categories["toy"])
        self.assertFalse(loaded.global_settings.reaction_toggles["usb"])
        self.assertFalse(loaded.global_settings.rare_events_enabled)
        self.assertTrue(loaded.global_settings.chaos_mode)
        self.assertFalse(loaded.global_settings.movement_enabled)
        self.assertFalse(loaded.global_settings.companion_enabled)
        self.assertEqual("mouse", loaded.global_settings.selected_companion)
        self.assertEqual("high", loaded.global_settings.activity_level)
        self.assertEqual("chatty", loaded.global_settings.quote_frequency)
        self.assertEqual("low", loaded.global_settings.companion_frequency)
        self.assertFalse(loaded.global_settings.unlocks_enabled)
        self.assertEqual("office-chaos", loaded.global_settings.seasonal_mode_override)
        self.assertEqual(["office"], loaded.global_settings.favorite_skins)
        self.assertEqual(["tricycle"], loaded.global_settings.favorite_toys)
        self.assertEqual(["office-chaos"], loaded.global_settings.favorite_scenarios)
        self.assertEqual(["what-do"], loaded.global_settings.favorite_quote_packs)
        self.assertEqual(["astronaut"], loaded.global_settings.unlocked_skins)
        self.assertEqual(3, loaded.global_settings.discovery_stats["launches"])
        self.assertEqual({"jason-quotes": False}, loaded.global_settings.quote_pack_states)
        self.assertEqual(14, loaded.global_settings.companion_presence["familiarity"])
        self.assertEqual(4, loaded.global_settings.companion_presence["days_used"])
        self.assertEqual("wizard", loaded.instance_settings.skin)
        self.assertEqual("Desk Jason", loaded.instance_settings.name)
        self.assertEqual("busy", loaded.instance_settings.personality_state)
        self.assertEqual("office-chaos", loaded.instance_settings.last_scenario)

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

        self.assertEqual(8, exported["schema_version"])
        self.assertEqual(70, exported["global"]["sound_volume"])
        self.assertEqual({}, exported["instances"])


if __name__ == "__main__":
    unittest.main()
