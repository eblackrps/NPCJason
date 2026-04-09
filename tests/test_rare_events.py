import random
import unittest

from npcjason_app.rare_events import RareEventManager


class RareEventTests(unittest.TestCase):
    def test_pick_event_biases_matching_skin_tags(self):
        manager = RareEventManager(clock=lambda: 1.0)

        event = manager.pick_event(
            {
                "skin_tags": ["homelab"],
                "preferred_categories": ["homelab"],
                "chaos_mode": False,
            },
            rng=random.Random(5),
        )

        self.assertIsNotNone(event)
        self.assertEqual("homelab-delivery", event.key)

    def test_mark_triggered_applies_cooldown(self):
        manager = RareEventManager(clock=lambda: 1.0)

        self.assertTrue(manager.mark_triggered("duck-debug"))
        self.assertGreater(manager.remaining_cooldown_ms("duck-debug"), 0)


if __name__ == "__main__":
    unittest.main()
