import unittest

from npcjason_app.tray_controller import (
    TrayPetOption,
    TrayQuotePackOption,
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
            skin_key="wizard",
            sound_enabled=False,
            auto_start_enabled=True,
            rare_events_enabled=False,
            chaos_mode=True,
            active_toy_label="Rubber Duck",
            skin_options=[
                TraySkinOption(key="jason", label="Classic Jason"),
                TraySkinOption(key="wizard", label="Wizard Jason"),
            ],
            toy_options=[TrayToyOption(key="rubber-duck", label="Rubber Duck", cooldown_ms=0, active=True)],
            quote_packs=[TrayQuotePackOption(key="jason-quotes", label="Jason Quote Pack", enabled=True)],
            pets=[TrayPetOption(pet_id="friend-1", label="Buddy | Wizard | happy")],
            tray_colors={"hair": "#123456"},
        )

        snapshot = build_tray_snapshot(state)

        self.assertEqual("Desk Jason | Happy | Rubber Duck", snapshot["title"])
        self.assertEqual(["Classic Jason", "Wizard Jason"], snapshot["skin_labels"])
        self.assertEqual("wizard", snapshot["selected_skin"])
        self.assertEqual(["Buddy | Wizard | happy"], snapshot["pets"])
        self.assertFalse(snapshot["sound_enabled"])
        self.assertTrue(snapshot["auto_start_enabled"])
        self.assertEqual(["Rubber Duck"], snapshot["toy_labels"])
        self.assertEqual(["Jason Quote Pack"], snapshot["quote_packs"])
        self.assertFalse(snapshot["rare_events_enabled"])
        self.assertTrue(snapshot["chaos_mode"])


if __name__ == "__main__":
    unittest.main()
