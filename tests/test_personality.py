import unittest

from npcjason_app.personality import PersonalityController


class FixedRng:
    def __init__(self, uniform_value):
        self.uniform_value = uniform_value

    def uniform(self, _minimum, _maximum):
        return self.uniform_value


class PersonalityTests(unittest.TestCase):
    def setUp(self):
        self.now = [1000.0]
        self.controller = PersonalityController(clock=lambda: self.now[0])

    def test_transition_snapshot_and_locking(self):
        self.controller.transition_to("busy", duration_ms=5000, lock_ms=2000)

        snapshot = self.controller.snapshot()

        self.assertEqual("busy", snapshot["key"])
        self.assertTrue(snapshot["locked"])
        self.assertEqual("pace", snapshot["movement_style"])
        self.assertIn("office", snapshot["preferred_categories"])

    def test_tick_respects_lock_window(self):
        self.controller.transition_to("curious", duration_ms=1000, lock_ms=3000)
        self.controller.state_until_ms = 0

        changed = self.controller.tick(context={}, rng=FixedRng(0))

        self.assertIsNone(changed)
        self.assertEqual("curious", self.controller.current_state())

    def test_tick_biases_busy_during_patch_day(self):
        self.controller.load("idle")
        self.controller.state_until_ms = 0
        self.controller.locked_until_ms = 0

        changed = self.controller.tick(
            context={"mood": "caffeinated", "seasonal_contexts": ["patch-day"]},
            rng=FixedRng(10),
        )

        self.assertEqual("busy", changed)
        self.assertEqual("busy", self.controller.current_state())


if __name__ == "__main__":
    unittest.main()
