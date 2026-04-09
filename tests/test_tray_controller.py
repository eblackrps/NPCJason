import unittest

from npcjason_app.tray_controller import (
    TrayPetOption,
    TraySkinOption,
    TrayState,
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
            skin_options=[
                TraySkinOption(key="jason", label="Classic Jason"),
                TraySkinOption(key="wizard", label="Wizard Jason"),
            ],
            pets=[TrayPetOption(pet_id="friend-1", label="Buddy | Wizard | happy")],
            tray_colors={"hair": "#123456"},
        )

        snapshot = build_tray_snapshot(state)

        self.assertEqual("Desk Jason | Happy", snapshot["title"])
        self.assertEqual(["Classic Jason", "Wizard Jason"], snapshot["skin_labels"])
        self.assertEqual("wizard", snapshot["selected_skin"])
        self.assertEqual(["Buddy | Wizard | happy"], snapshot["pets"])
        self.assertFalse(snapshot["sound_enabled"])
        self.assertTrue(snapshot["auto_start_enabled"])


if __name__ == "__main__":
    unittest.main()
