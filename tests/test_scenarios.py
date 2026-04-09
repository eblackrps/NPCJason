import unittest

from npcjason_app.scenarios import ScenarioManager
from npcjason_app.unlocks import UnlockManager


class FixedRng:
    def __init__(self, uniform_value):
        self.uniform_value = uniform_value

    def uniform(self, _minimum, _maximum):
        return self.uniform_value


class ScenarioTests(unittest.TestCase):
    def setUp(self):
        self.now = [1000.0]
        self.manager = ScenarioManager(clock=lambda: self.now[0])
        self.unlocks = UnlockManager()
        self.unlocks.load()

    def test_pick_scenario_prefers_favorites_and_matching_context(self):
        scenario = self.manager.pick_scenario(
            context={
                "favorite_scenarios": ["office-chaos"],
                "skin_tags": ["office", "responsible"],
                "preferred_categories": ["office"],
                "personality_state": "annoyed",
                "seasonal_modes": ["patch-day-panic"],
                "chaos_mode": True,
            },
            unlock_manager=self.unlocks,
            rng=FixedRng(30),
        )

        self.assertIsNotNone(scenario)
        self.assertEqual("office-chaos", scenario.key)

    def test_tick_runs_steps_and_applies_cooldown(self):
        self.assertTrue(self.manager.start("busy-it-morning", unlock_manager=self.unlocks))

        seen_actions = []
        completed = None
        for _index in range(12):
            result = self.manager.tick()
            if result.command:
                seen_actions.append(result.command.action)
            if result.completed_scenario:
                completed = result.completed_scenario
                break
            self.now[0] += 1.0

        self.assertEqual("busy-it-morning", completed)
        self.assertIn("set_state", seen_actions)
        self.assertIn("movement", seen_actions)
        self.assertIn("toy", seen_actions)
        self.assertIn("quote", seen_actions)
        self.assertGreater(self.manager.remaining_cooldown_ms("busy-it-morning"), 0)


if __name__ == "__main__":
    unittest.main()
