import unittest

from npcjason_app.tray_controller import (
    TrayCompanionInteractionOption,
    TrayCompanionOption,
    TrayDeskItemOption,
    TrayPetOption,
    TrayQuotePackOption,
    TrayScenarioOption,
    TraySeasonOption,
    TraySkinOption,
    TrayState,
    TrayToyOption,
    build_tray_snapshot,
)


class TrayControllerTests(unittest.TestCase):
    def test_build_tray_snapshot_exposes_menu_state(self):
        state = TrayState(
            pet_name="Desk Jason",
            mood_label="Happy",
            personality_label="Busy",
            skin_key="wizard",
            sound_enabled=False,
            auto_start_enabled=True,
            rare_events_enabled=False,
            chaos_mode=True,
            movement_enabled=False,
            companion_enabled=True,
            companion_label="Mouse Sidekick",
            companion_state_label="Waiting",
            unlocks_enabled=False,
            active_toy_label="Rubber Duck",
            active_desk_item_label="Coffee Mug",
            activity_level="high",
            quote_frequency="chatty",
            companion_frequency="low",
            skin_options=[
                TraySkinOption(key="jason", label="Classic Jason"),
                TraySkinOption(key="wizard", label="Wizard Jason"),
            ],
            companion_options=[
                TrayCompanionOption(key="mouse", label="Mouse Sidekick", enabled=True, selected=True, state_label="Waiting"),
            ],
            companion_interactions=[
                TrayCompanionInteractionOption(key="feed-cheese", label="Feed Cheese", cooldown_ms=0, active=False),
            ],
            toy_options=[TrayToyOption(key="rubber-duck", label="Rubber Duck", cooldown_ms=0, active=True)],
            desk_item_options=[TrayDeskItemOption(key="coffee-mug", label="Coffee Mug", cooldown_ms=0, active=False)],
            quote_packs=[TrayQuotePackOption(key="jason-quotes", label="Jason Quote Pack", enabled=True)],
            scenario_options=[TrayScenarioOption(key="office-chaos", label="Office Chaos", cooldown_ms=0, active=False)],
            seasonal_options=[TraySeasonOption(key="monday-morning-survival", label="Monday Morning Survival", active=True)],
            seasonal_mode_label="Monday Morning Survival",
            pets=[TrayPetOption(pet_id="friend-1", label="Buddy | Wizard | happy")],
            tray_colors={"hair": "#123456"},
        )

        snapshot = build_tray_snapshot(state)

        self.assertEqual("Desk Jason | Happy | Busy | Rubber Duck", snapshot["title"])
        self.assertEqual(["Classic Jason", "Wizard Jason"], snapshot["skin_labels"])
        self.assertEqual("wizard", snapshot["selected_skin"])
        self.assertEqual(["Buddy | Wizard | happy"], snapshot["pets"])
        self.assertFalse(snapshot["sound_enabled"])
        self.assertTrue(snapshot["auto_start_enabled"])
        self.assertEqual(["Rubber Duck"], snapshot["toy_labels"])
        self.assertEqual(["Coffee Mug"], snapshot["desk_item_labels"])
        self.assertEqual(["Jason Quote Pack"], snapshot["quote_packs"])
        self.assertEqual(["Office Chaos"], snapshot["scenario_labels"])
        self.assertTrue(snapshot["companion_enabled"])
        self.assertEqual("Mouse Sidekick", snapshot["companion_label"])
        self.assertEqual("Waiting", snapshot["companion_state"])
        self.assertEqual(["Mouse Sidekick"], snapshot["companion_labels"])
        self.assertEqual(["Feed Cheese"], snapshot["companion_interactions"])
        self.assertEqual("Monday Morning Survival", snapshot["seasonal_mode"])
        self.assertFalse(snapshot["rare_events_enabled"])
        self.assertTrue(snapshot["chaos_mode"])
        self.assertFalse(snapshot["movement_enabled"])
        self.assertFalse(snapshot["unlocks_enabled"])
        self.assertEqual("high", snapshot["activity_level"])
        self.assertEqual("chatty", snapshot["quote_frequency"])
        self.assertEqual("low", snapshot["companion_frequency"])


if __name__ == "__main__":
    unittest.main()
