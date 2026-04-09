from datetime import datetime
import unittest

from npcjason_app.seasonal import SeasonalModeManager


class SeasonalModeTests(unittest.TestCase):
    def test_monday_morning_mode_activates_from_calendar(self):
        manager = SeasonalModeManager()

        context = manager.context(now=datetime(2026, 4, 13, 9, 0, 0))

        self.assertIn("monday-morning-survival", context["active_keys"])
        self.assertIn("office", context["preferred_skin_tags"])

    def test_override_forces_specific_mode(self):
        manager = SeasonalModeManager()
        self.assertTrue(manager.set_override("homelab-weekend"))

        context = manager.context(now=datetime(2026, 4, 8, 10, 0, 0))

        self.assertEqual(["homelab-weekend"], context["active_keys"])
        self.assertIn("what-do", context["preferred_quote_packs"])


if __name__ == "__main__":
    unittest.main()
